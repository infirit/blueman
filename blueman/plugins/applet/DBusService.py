# coding=utf-8
from blueman.main.PluginManager import StopException
from blueman.plugins.AppletPlugin import AppletPlugin
from blueman.bluez.Device import Device
from blueman.services.Functions import get_service
from blueman.main.DbusService import *
from gi.repository import Gio
import logging


DBUS_INTERFACE = 'org.blueman.Applet'


class AppletBaseService(DbusService):
    def __init__(self, plugin, **kwargs):
        super().__init__(path='/org/blueman/Applet', **kwargs)
        self.parent = plugin.parent

    @dbus_method(interface=DBUS_INTERFACE, out_signature='as')
    def QueryPlugins(self):
        return self.parent.Plugins.get_loaded()

    def on_device_disconnect(self, device):
        pass

    @dbus_method(interface=DBUS_INTERFACE, out_signature='as')
    def QueryAvailablePlugins(self):
        return list(self.parent.Plugins.get_classes())

    @dbus_method(interface=DBUS_INTERFACE, in_signature='sb')
    def SetPluginConfig(self, plugin, value):
        self.parent.Plugins.set_config(plugin, value)

    @dbus_method(interface=DBUS_INTERFACE, in_signature='os', invocation_keyword='invocation')
    def connect_service(self, object_path, uuid, invocation):
        try:
            self.parent.Plugins.RecentConns
        except KeyError:
            logging.warning("RecentConns plugin is unavailable")
        else:
            self.parent.Plugins.RecentConns.notify(object_path, uuid)

        if uuid == '00000000-0000-0000-0000-000000000000':
            device = Device(object_path)
            device.connect(reply_handler=invocation.return_value, error_handler=invocation.return_error)
        else:
            def cb(_inst, ret):
                if ret:
                    raise StopException

            service = get_service(Device(object_path), uuid)

            if service.group == 'serial' and 'NMDUNSupport' in self.QueryPlugins():
                self.parent.Plugins.run_ex("service_connect_handler", cb, service, invocation.return_value,
                                           invocation.return_error)
            elif service.group == 'serial' and 'PPPSupport' in self.QueryPlugins():
                def reply(rfcomm):
                    self.parent.Plugins.run("on_rfcomm_connected", service, rfcomm)
                    invocation.return_value(rfcomm)

                rets = self.parent.Plugins.run("rfcomm_connect_handler", service, reply, invocation.return_error)
                if True in rets:
                    pass
                else:
                    logging.info("No handler registered")
                    invocation.return_error(
                        "Service not supported\nPossibly the plugin that handles this service is not loaded")
            else:
                if not self.parent.Plugins.run_ex("service_connect_handler", cb, service, invocation.return_value,
                                                  invocation.return_error):
                    service.connect(reply_handler=invocation.return_value, error_handler=invocation.return_error)

    @dbus_method(interface=DBUS_INTERFACE, in_signature='osd', invocation_keyword='invocation')
    def disconnect_service(self, object_path, uuid, port, invocation):
        if uuid == '00000000-0000-0000-0000-000000000000':
            device = Device(object_path)
            device.disconnect(reply_handler=invocation.return_value, error_handler=invocation.return_error)
        else:
            def cb(_inst, ret):
                if ret:
                    raise StopException

            service = get_service(Device(object_path), uuid)

            if service.group == 'serial' and 'NMDUNSupport' in self.QueryPlugins():
                self.parent.Plugins.run_ex("service_disconnect_handler", cb, service, invocation.return_value,
                                           invocation.return_error)
            elif service.group == 'serial' and 'PPPSupport' in self.QueryPlugins():
                service.disconnect(port, reply_handler=invocation.return_value, error_handler=invocation.return_error)

                self.parent.Plugins.run("on_rfcomm_disconnect", port)

                logging.info("Disconnecting rfcomm device")
            else:
                if not self.parent.Plugins.run_ex("service_disconnect_handler", cb, service, invocation.return_value,
                                                  invocation.return_error):
                    service.disconnect(reply_handler=invocation.return_value, error_handler=invocation.return_error)

    @dbus_method(interface=DBUS_INTERFACE)
    def open_plugin_dialog(self):
        self.parent.Plugins.StandardItems.on_plugins()


class DBusService(AppletPlugin):
    __depends__ = ["StatusIcon"]
    __unloadable__ = False
    __description__ = _("Provides DBus API for other Blueman components")
    __author__ = "Walmis"

    _connection = None
    _dbus_service = None

    def on_load(self):

        AppletPlugin.add_method(self.on_rfcomm_connected)
        AppletPlugin.add_method(self.on_rfcomm_disconnect)
        AppletPlugin.add_method(self.rfcomm_connect_handler)
        AppletPlugin.add_method(self.service_connect_handler)
        AppletPlugin.add_method(self.service_disconnect_handler)

        self._connection = Gio.bus_get_sync(Gio.BusType.SESSION)
        self._dbus_service = AppletBaseService(self, connection=self._connection)
        self._dbus_service.connect_bus()

    def on_unload(self):
        self._dbus_service.disconnect_bus()
        self._dbus_service = None

    def service_connect_handler(self, service, ok, err):
        pass

    def service_disconnect_handler(self, service, ok, err):
        pass

    def rfcomm_connect_handler(self, service, reply_handler, error_handler):
        return False

    def on_rfcomm_connected(self, service, port):
        pass

    def on_rfcomm_disconnect(self, port):
        pass
