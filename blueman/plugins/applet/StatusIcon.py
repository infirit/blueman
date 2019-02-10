# coding=utf-8
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gio

from blueman.Functions import launch, kill, get_pid, get_lockfile
from blueman.main.DbusService import *
from blueman.main.PluginManager import StopException
from blueman.plugins.AppletPlugin import AppletPlugin


DBUS_INTERFACE = 'org.blueman.Applet.StatusIcon'


class AppletStatusIconService(DbusService):
    def __init__(self, plugin, **kwargs):
        super().__init__(path='/org/blueman/Applet', **kwargs)
        self.plugin = plugin

    @dbus_method(interface=DBUS_INTERFACE, out_signature='b')
    def GetVisibility(self):
        return self.plugin.visible

    @dbus_signal(interface=DBUS_INTERFACE, signature='b')
    def VisibilityChanged(self, visible):
        pass

    @dbus_signal(interface=DBUS_INTERFACE, signature='s')
    def TextChanged(self, text):
        pass

    @dbus_method(interface=DBUS_INTERFACE, out_signature='s')
    def GetText(self):
        return '\n'.join([self.plugin.lines[key] for key in sorted(self.plugin.lines)])

    @dbus_signal(interface=DBUS_INTERFACE, signature='s')
    def IconNameChanged(self, icon_name):
        pass

    @dbus_method(interface=DBUS_INTERFACE, out_signature="s")
    def GetStatusIconImplementation(self):
        implementations = self.plugin.parent.Plugins.run("on_query_status_icon_implementation")
        return next((implementation for implementation in implementations if implementation), 'GtkStatusIcon')

    @dbus_method(interface=DBUS_INTERFACE, out_signature='s')
    def GetIconName(self):
        icon = "blueman-tray"

        def callback(inst, ret):
            if ret is not None:
                for i in ret:
                    nonlocal icon
                    icon = i
                    raise StopException

        self.plugin.parent.Plugins.run_ex("on_status_icon_query_icon", callback)
        return icon

    @dbus_method(interface=DBUS_INTERFACE)
    def Activate(self):
        self.plugin.emit('activate')


class StatusIcon(AppletPlugin, GObject.GObject):
    __gsignals__ = {'activate': (GObject.SignalFlags.NO_HOOKS, None, ())}

    __unloadable__ = False
    __icon__ = "blueman-tray"
    __depends__ = ['Menu']

    FORCE_SHOW = 2
    SHOW = 1
    FORCE_HIDE = 0

    visible = None

    visibility_timeout = None

    _implementation = None

    _connection = None
    _dbus_service = None

    def on_load(self):
        GObject.GObject.__init__(self)
        self.lines = {0: _("Bluetooth Enabled")}

        AppletPlugin.add_method(self.on_query_status_icon_implementation)
        AppletPlugin.add_method(self.on_query_status_icon_visibility)
        AppletPlugin.add_method(self.on_status_icon_query_icon)

        self.query_visibility(emit=False)

        self.parent.Plugins.connect('plugin-loaded', self._on_plugins_changed)
        self.parent.Plugins.connect('plugin-unloaded', self._on_plugins_changed)

        self._connection = Gio.bus_get_sync(Gio.BusType.SESSION)
        self._dbus_service = AppletStatusIconService(self, connection=self._connection)
        self._dbus_service.connect_bus()

    def on_unload(self):
        self._dbus_service.disconnect_bus()
        self._dbus_service = None

    def on_power_state_changed(self, _manager, state):
        if state:
            self.set_text_line(0, _("Bluetooth Enabled"))
            self.query_visibility(delay_hiding=True)
        else:
            self.set_text_line(0, _("Bluetooth Disabled"))
            self.query_visibility()

    def query_visibility(self, delay_hiding=False, emit=True):
        rets = self.parent.Plugins.run("on_query_status_icon_visibility")
        if StatusIcon.FORCE_HIDE not in rets:
            if StatusIcon.FORCE_SHOW in rets:
                self.set_visible(True, emit)
            else:
                if not self.parent.Manager:
                    self.set_visible(False, emit)
                    return

                if self.parent.Manager.get_adapters():
                    self.set_visible(True, emit)
                elif not self.visibility_timeout:
                    if delay_hiding:
                        self.visibility_timeout = GLib.timeout_add(1000, self.on_visibility_timeout)
                    else:
                        self.set_visible(False, emit)
        else:
            self.set_visible(False, emit)

    def on_visibility_timeout(self):
        GLib.source_remove(self.visibility_timeout)
        self.visibility_timeout = None
        self.query_visibility()

    def set_visible(self, visible, emit):
        self.visible = visible
        if emit:
            self._dbus_service.VisibilityChanged(visible)

    def set_text_line(self, lineid, text):
        if text:
            self.lines[lineid] = text
        else:
            self.lines.pop(lineid, None)

        self._dbus_service.TextChanged(self._dbus_service.GetText())

    def icon_should_change(self):
        self._dbus_service.IconNameChanged(self._dbus_service.GetIconName())
        self.query_visibility()

    def on_adapter_added(self, path):
        self.query_visibility()

    def on_adapter_removed(self, path):
        self.query_visibility()

    def on_manager_state_changed(self, state):
        self.query_visibility()

    def _on_plugins_changed(self, _plugins, _name):
        implementation = self._dbus_service.GetStatusIconImplementation()
        if not self._implementation or self._implementation != implementation:
            self._implementation = implementation
            kill(get_pid(get_lockfile('blueman-tray')), 'blueman-tray')
            launch('blueman-tray', icon_name='blueman', sn=False)

    def on_query_status_icon_implementation(self):
        return None

    def on_query_status_icon_visibility(self):
        return StatusIcon.SHOW

    def on_status_icon_query_icon(self):
        return None
