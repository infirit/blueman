# coding=utf-8
from blueman.main.DbusService import *
from blueman.plugins.AppletPlugin import AppletPlugin
from operator import attrgetter
from gi.repository import GLib
from gi.repository import Gio


class MenuItem(object):
    def __init__(self, menu_plugin, owner, priority, text, markup, icon_name, tooltip, callback, submenu_function,
                 visible, sensitive):
        self._menu_plugin = menu_plugin
        self._owner = owner
        self._priority = priority
        self._text = text
        self._markup = markup
        self._icon_name = icon_name
        self._tooltip = tooltip
        self._callback = callback
        self._submenu_function = submenu_function
        self._visible = visible
        self._sensitive = sensitive

        assert text and icon_name and (callback or submenu_function) or \
            not any([text, icon_name, tooltip, callback, submenu_function])

    @property
    def owner(self):
        return self._owner

    @property
    def priority(self):
        return self._priority

    @property
    def callback(self):
        return self._callback

    @property
    def visible(self):
        return self._visible

    def __iter__(self):
        for key in ['text', 'markup', 'icon_name', 'tooltip', 'sensitive']:
            value = getattr(self, '_' + key)
            if value is not None:
                yield key, value
        submenu = list(self.submenu_items)
        if submenu:
            yield 'submenu', [dict(item) for item in submenu]

    @property
    def submenu_items(self):
        if not self._submenu_function:
            return
        submenu_items = self._submenu_function()
        if not submenu_items:
            return
        for item in submenu_items:
            assert not set(item.keys()) - {'text', 'markup', 'icon_name', 'tooltip', 'callback', 'sensitive'}
            yield MenuItem(self._menu_plugin, self._owner, 0, item.get('text'), item.get('markup'),
                           item.get('icon_name'), item.get('tooltip'), item.get('callback'), None, True,
                           item.get('sensitive', True))

    def set_text(self, text, markup=False):
        self._text = text
        self._markup = markup
        self._menu_plugin.on_menu_changed()

    def set_icon_name(self, icon_name):
        self._icon_name = icon_name
        self._menu_plugin.on_menu_changed()

    def set_tooltip(self, tooltip):
        self._tooltip = tooltip
        self._menu_plugin.on_menu_changed()

    def set_visible(self, visible):
        self._visible = visible
        self._menu_plugin.on_menu_changed()

    def set_sensitive(self, sensitive):
        self._sensitive = sensitive
        self._menu_plugin.on_menu_changed()


DBUS_INTERFACE = 'org.blueman.Applet.Menu'


class AppletMenuService(DbusService):
    def __init__(self, plugin, **kwargs):
        super().__init__(path='/org/blueman/Applet', **kwargs)
        self.plugin = plugin

    @dbus_signal(interface=DBUS_INTERFACE, signature='aa{sv}')
    def MenuChanged(self, menu):
        pass

    @dbus_method(interface=DBUS_INTERFACE, out_signature='aa{sv}')
    def GetMenu(self):
        def create_variant(value):
            if type(value) == bool:
                return GLib.Variant('b', value)
            elif type(value) == str:
                return GLib.Variant('s', value)
            elif type(value) == list:
                value_dict = {}
                for lkey, lval in value[0].items():
                    value_dict[lkey] = create_variant(lval)
                return GLib.Variant('a{sv}', value_dict)
            else:
                raise ValueError('Unhandled type: %s' % type(value))

        items = []
        for item in self.plugin.menuitems:
            if not item.visible:
                continue

            item_dict = {}
            for key, val in item:
                    item_dict[key] = create_variant(val)

            items.append(item_dict)
        return items

    @dbus_method(interface=DBUS_INTERFACE, in_signature='ai')
    def ActivateMenuItem(self, indexes):
        node = [item for item in self.plugin.menuitems if item.visible][indexes[0]]
        for index in list(indexes)[1:]:
            node = [item for item in node.submenu_items if item.visible][index]
        if node.callback:
            node.callback()


class Menu(AppletPlugin):
    __description__ = _("Provides a menu for the applet and an API for other plugins to manipulate it")
    __icon__ = "menu-editor"
    __author__ = "Walmis"
    __unloadable__ = False

    _connection = None
    _dbus_service = None

    menuitems = []

    def on_load(self):
        self.__plugins_loaded = False

        self._connection = Gio.bus_get_sync(Gio.BusType.SESSION)
        self._dbus_service = AppletMenuService(self, connection=self._connection)
        self._dbus_service.connect_bus()

    def on_unload(self):
        self._connection = None
        self._dbus_service.disconnec_bus()
        self._dbus_service = None

    def __sort(self):
        self.menuitems.sort(key=attrgetter('priority'))

    def add(self, owner, priority, text=None, markup=False, icon_name=None, tooltip=None, callback=None,
            submenu_function=None, visible=True, sensitive=True):
        item = MenuItem(self, owner, priority, text, markup, icon_name, tooltip, callback, submenu_function, visible,
                        sensitive)
        self.menuitems.append(item)
        if self.__plugins_loaded:
            self.__sort()
        self.on_menu_changed()
        return item

    def unregister(self, owner):
        for item in reversed(self.menuitems):
            if item.owner == owner:
                self.menuitems.remove(item)
        self.on_menu_changed()

    def on_plugins_loaded(self):
        self.__plugins_loaded = True
        self.__sort()

    def on_menu_changed(self):
        self._dbus_service.MenuChanged(self._dbus_service.GetMenu())
