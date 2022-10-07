from gettext import gettext as _
import logging
from typing import Dict, Tuple, TYPE_CHECKING, Any, Optional, Sequence

from blueman.bluez.Adapter import Adapter
from blueman.bluez.Device import Device
from blueman.bluez.Manager import Manager
from blueman.gui.manager.ManagerDeviceList import ManagerDeviceList
from blueman.gui.manager.ManagerDeviceMenu import ManagerDeviceMenu
from blueman.gui.CommonUi import show_about_dialog
from blueman.Constants import WEBSITE
from blueman.Functions import launch, adapter_path_to_name

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Gio

if TYPE_CHECKING:
    from blueman.main.Manager import Blueman


class ManagerMenu:
    def __init__(self, blueman: "Blueman"):
        self.blueman = blueman
        self.Config = Gio.Settings(schema_id="org.blueman.general")

        self.adapter_items: Dict[str, Tuple[Gtk.RadioMenuItem, Adapter]] = {}
        self._adapters_group: Sequence[Gtk.RadioMenuItem] = []
        self._insert_adapter_item_pos = 2

        self.item_adapter = self.blueman.builder.get_widget("item_adapter", Gtk.MenuItem)
        self.item_device = self.blueman.builder.get_widget("item_device", Gtk.MenuItem)

        self.item_view = self.blueman.builder.get_widget("item_view", Gtk.MenuItem)
        self.item_help = self.blueman.builder.get_widget("item_help", Gtk.MenuItem)

        report_item = self.blueman.builder.get_widget("report_problem", Gtk.ImageMenuItem)
        report_item.connect("activate", lambda x: launch(f"xdg-open {WEBSITE}/issues"))

        help_item = self.blueman.builder.get_widget("help", Gtk.ImageMenuItem)
        assert self.blueman.window is not None
        widget = self.blueman.window.get_toplevel()
        assert isinstance(widget, Gtk.Window)
        window = widget
        help_item.connect("activate", lambda x: show_about_dialog('Blueman ' + _('Device Manager'), parent=window))

        item_toolbar = self.blueman.builder.get_widget("show_toolbar", Gtk.CheckMenuItem)
        self.blueman.Config.bind("show-toolbar", item_toolbar, "active", Gio.SettingsBindFlags.DEFAULT)

        item_statusbar = self.blueman.builder.get_widget("show_statusbar", Gtk.CheckMenuItem)
        self.blueman.Config.bind("show-statusbar", item_statusbar, "active", Gio.SettingsBindFlags.DEFAULT)

        item_unnamed = self.blueman.builder.get_widget("hide_unnamed", Gtk.CheckMenuItem)
        self.blueman.Config.bind("hide-unnamed", item_unnamed, "active", Gio.SettingsBindFlags.DEFAULT)

        self._sort_alias_item = self.blueman.builder.get_widget("sort_by_name", Gtk.RadioMenuItem)
        self._sort_timestamp_item = self.blueman.builder.get_widget("sort_by_added", Gtk.RadioMenuItem)

        sort_config = self.Config['sort-by']
        if sort_config == "alias":
            self._sort_alias_item.props.active = True
        else:
            self._sort_timestamp_item.props.active = True

        self._sort_type_item = self.blueman.builder.get_widget("sort_descending", Gtk.CheckMenuItem)

        if self.Config['sort-order'] == "ascending":
            self._sort_type_item.props.active = False
        else:
            self._sort_type_item.props.active = True

        item_plugins = self.blueman.builder.get_widget("view_plugin_dialog", Gtk.ImageMenuItem)
        item_plugins.connect('activate', self._on_plugin_dialog_activate)

        item_services = self.blueman.builder.get_widget("view_services", Gtk.ImageMenuItem)
        item_services.connect('activate', lambda *args: launch("blueman-services", name=_("Service Preferences")))

        search_item = self.blueman.builder.get_widget("adapter_search", Gtk.ImageMenuItem)
        search_item.connect("activate", lambda x: self.blueman.inquiry())
        self.Search = search_item

        adapter_settings = self.blueman.builder.get_widget("adapter_prefs", Gtk.ImageMenuItem)
        adapter_settings.connect("activate", lambda x: self.blueman.adapter_properties())

        exit_item = self.blueman.builder.get_widget("adapter_exit", Gtk.ImageMenuItem)
        exit_item.connect("activate", lambda x: self.blueman.quit())

        self.item_adapter.show()
        self.item_view.show()
        self.item_help.show()
        self.item_device.show()
        self.item_device.props.sensitive = False

        self._manager = Manager()
        self._manager.connect_signal("adapter-added", self.on_adapter_added)
        self._manager.connect_signal("adapter-removed", self.on_adapter_removed)

        blueman.List.connect("device-selected", self.on_device_selected)

        for adapter in self._manager.get_adapters():
            self.on_adapter_added(None, adapter.get_object_path())

        self.device_menu: Optional[ManagerDeviceMenu] = None

        self.Config.connect("changed", self._on_settings_changed)
        self._sort_alias_item.connect("activate", self._on_sorting_changed, "alias")
        self._sort_timestamp_item.connect("activate", self._on_sorting_changed, "timestamp")
        self._sort_type_item.connect("activate", self._on_sorting_changed, "sort-type")

    def _on_sorting_changed(self, btn: Gtk.CheckMenuItem, sort_opt: str) -> None:
        if sort_opt == 'alias' and btn.props.active:
            self.Config['sort-by'] = "alias"
        elif sort_opt == "timestamp" and btn.props.active:
            self.Config['sort-by'] = "timestamp"
        elif sort_opt == 'sort-type':
            # FIXME bind widget to gsetting
            if btn.props.active:
                self.Config["sort-order"] = "descending"
            else:
                self.Config["sort-order"] = "ascending"

    def _on_settings_changed(self, settings: Gio.Settings, key: str) -> None:
        value = settings[key]
        if key == 'sort-by':
            if value == "alias":
                if not self._sort_alias_item.props.active:
                    self._sort_alias_item.props.active = True
            elif value == "timestamp":
                if not self._sort_timestamp_item.props.active:
                    self._sort_timestamp_item.props.active = True
        elif key == "sort-type":
            if value == "ascending":
                if not self._sort_type_item.props.active:
                    self._sort_type_item.props.active = True
            else:
                if not self._sort_type_item.props.active:
                    self._sort_type_item.props.active = False
        elif key == "hide-unnamed":
            logging.debug("refilter")
            self.blueman.List.filter.refilter()

    def on_device_selected(self, _lst: ManagerDeviceList, device: Device, tree_iter: Gtk.TreeIter) -> None:
        if tree_iter and device:
            self.item_device.props.sensitive = True

            if self.device_menu is None:
                self.device_menu = ManagerDeviceMenu(self.blueman)
                self.item_device.set_submenu(self.device_menu)
            else:
                def idle() -> bool:
                    assert self.device_menu is not None  # https://github.com/python/mypy/issues/2608
                    self.device_menu.generate()
                    return False
                GLib.idle_add(idle, priority=GLib.PRIORITY_LOW)

        else:
            self.item_device.props.sensitive = False

    def on_adapter_property_changed(self, _adapter: Adapter, name: str, value: Any, path: str) -> None:
        if name == "Name" or name == "Alias":
            item = self.adapter_items[path][0]
            item.set_label(value)
        elif name == "Discovering":
            if self.Search:
                if value:
                    self.Search.props.sensitive = False
                else:
                    self.Search.props.sensitive = True

    def on_adapter_selected(self, menuitem: Gtk.CheckMenuItem, adapter_path: str) -> None:
        if menuitem.props.active:
            assert self.blueman.List.Adapter is not None
            if adapter_path != self.blueman.List.Adapter.get_object_path():
                logging.info(f"selected {adapter_path}")
                self.blueman.Config["last-adapter"] = adapter_path_to_name(adapter_path)
                self.blueman.List.set_adapter(adapter_path)

    def on_adapter_added(self, _manager: Optional[Manager], adapter_path: str) -> None:
        adapter = Adapter(obj_path=adapter_path)
        menu = self.item_adapter.get_submenu()
        assert isinstance(menu, Gtk.Menu)

        item = Gtk.RadioMenuItem.new_with_label(self._adapters_group, adapter.get_name())
        item.show()
        self._adapters_group = item.get_group()

        self._itemhandler = item.connect("activate", self.on_adapter_selected, adapter_path)
        self._adapterhandler = adapter.connect_signal("property-changed", self.on_adapter_property_changed)

        menu.insert(item, self._insert_adapter_item_pos)
        self._insert_adapter_item_pos += 1

        self.adapter_items[adapter_path] = (item, adapter)

        assert self.blueman.List.Adapter is not None
        if adapter_path == self.blueman.List.Adapter.get_object_path():
            item.props.active = True

        if len(self.adapter_items) > 0:
            self.item_adapter.props.sensitive = True

    def on_adapter_removed(self, _manager: Manager, adapter_path: str) -> None:
        item, adapter = self.adapter_items.pop(adapter_path)
        menu = self.item_adapter.get_submenu()
        assert isinstance(menu, Gtk.Menu)

        item.disconnect(self._itemhandler)
        adapter.disconnect(self._adapterhandler)

        menu.remove(item)
        self._insert_adapter_item_pos -= 1

        if len(self.adapter_items) == 0:
            self.item_adapter.props.sensitive = False

    def _on_plugin_dialog_activate(self, _item: Gtk.MenuItem) -> None:
        def cb(_proxy: Gio.DBusProxy, _res: Any, _userdata: Any) -> None:
            pass
        self.blueman.Applet.OpenPluginDialog(result_handler=cb)
