from gettext import gettext as _
from typing import Union, TYPE_CHECKING, cast
from collections.abc import Callable
from blueman.bluemantyping import ObjectPath

from _blueman import RFCOMMError
from gi.repository import Gio, GLib

from blueman.Service import Service
from blueman.bluez.errors import BluezDBusException
if TYPE_CHECKING:
    from blueman.main.NetworkManager import NMConnectionError
from blueman.plugins.AppletPlugin import AppletPlugin
from blueman.bluez.Device import Device
from blueman.services.Functions import get_service

import logging

from blueman.services.meta import SerialService, NetworkService


class RFCOMMConnectedListener:
    def on_rfcomm_connected(self, service: SerialService, port: str) -> None:
        ...

    def on_rfcomm_disconnect(self, port: int) -> None:
        ...


class RFCOMMConnectHandler:
    def rfcomm_connect_handler(self, _service: SerialService, _reply: Callable[[str], None],
                               _err: Callable[[RFCOMMError | GLib.Error], None]) -> bool:
        return False


class ServiceConnectHandler:
    def service_connect_handler(self, _service: Service, _ok: Callable[[], None],
                                _err: Callable[[Union["NMConnectionError", GLib.Error]], None]) -> bool:
        return False

    def service_disconnect_handler(self, _service: Service, _ok: Callable[[], None],
                                   _err: Callable[[Union["NMConnectionError", GLib.Error]], None]) -> bool:
        return False


class DBusService(AppletPlugin):
    __unloadable__ = False
    __description__ = _("Provides DBus API for other Blueman components")
    __author__ = "Walmis"
    __dbus_iface_name__ = "org.blueman.Applet"

    def on_load(self) -> None:
        self._add_dbus_method("QueryPlugins", (), "as", self.parent.Plugins.get_loaded)
        self._add_dbus_method("QueryAvailablePlugins", (), "as", lambda: list(self.parent.Plugins.get_classes()))
        self._add_dbus_method("SetPluginConfig", ("s", "b"), "", self.parent.Plugins.set_config)
        self._add_dbus_method("ConnectService", ("o", "s"), "", self.connect_service, is_async=True)
        self._add_dbus_method("DisconnectService", ("o", "s", "d"), "", self._disconnect_service, is_async=True)
        self._add_dbus_method("OpenPluginDialog", (), "", self._open_plugin_dialog)

        self._add_dbus_signal("PluginsChanged")
        self._add_dbus_signal("BluezObjectAdded", ("o", "s"))
        self._add_dbus_signal("BluezObjectRemoved", ("o", "s"))
        self._add_dbus_signal("BluezInterfaceAdded", ("o", "s"))
        self._add_dbus_signal("BluezInterfaceRemoved", ("o", "s"))

        self.parent.Plugins.connect("plugin-loaded", lambda *args: self._plugins_changed())
        self.parent.Plugins.connect("plugin-unloaded", lambda *args: self._plugins_changed())

        self.__bluez_object_manager: Gio.DBusObjectManagerClient = Gio.DBusObjectManagerClient.new_for_bus_sync(
            Gio.BusType.SYSTEM, Gio.DBusObjectManagerClientFlags.DO_NOT_AUTO_START,
            "org.bluez", '/', None, None, None)
        self.__bluez_object_manager.connect("object-added", self.__on_bluez_obj_signal, "BluezObjectAdded")
        self.__bluez_object_manager.connect("object-removed", self.__on_bluez_obj_signal, "BluezObjectRemoved")
        self.__bluez_object_manager.connect("interface-added", self.__on_bluez_iface_signal, "BluezInterfaceAdded")
        self.__bluez_object_manager.connect("interface-removed", self.__on_bluez_iface_signal, "BluezInterfaceRemoved")

    def __on_bluez_obj_signal(
            self,
            _object_manager: Gio.DBusObjectManager,
            dbus_object: Gio.DBusObject,
            signal: str
    ) -> None:
        adapter1 = "org.bluez.Adapter1"
        device1 = "org.bluez.Device1"

        adapter_interface = dbus_object.get_interface(adapter1)
        device_interface = dbus_object.get_interface(device1)

        object_path = cast(ObjectPath, dbus_object.get_object_path())

        if adapter_interface is not None:
            logging.debug(f"{signal} - {adapter1}: {object_path}")
            self._emit_dbus_signal(signal, object_path, adapter1)
        if device_interface is not None:
            logging.debug(f"{signal} - {device1}: {object_path}")
            self._emit_dbus_signal(signal, object_path, device1)

    def __on_bluez_iface_signal(
            self,
            _object_manager: Gio.DBusObjectManagerClient,
            _dbus_object: Gio.DBusObject,
            interface: Gio.DBusInterface,
            signal: str
    ) -> None:
        assert isinstance(interface, Gio.DBusProxy)
        battery1 = "org.bluez.Battery1"
        battery_interface_name = interface.get_interface_name()
        object_path = cast(ObjectPath, interface.get_object_path())

        if battery_interface_name == battery1:
            logging.debug(f"{signal} - {battery1}: {object_path}")
            self._emit_dbus_signal(signal, object_path, battery1)

    def _plugins_changed(self) -> None:
        self._emit_dbus_signal("PluginsChanged")

    def connect_service(self, object_path: ObjectPath, uuid: str, ok: Callable[[], None],
                        err: Callable[[Union[BluezDBusException, "NMConnectionError",
                                             RFCOMMError, GLib.Error, str]], None]) -> None:
        try:
            self.parent.Plugins.RecentConns
        except KeyError:
            logging.warning("RecentConns plugin is unavailable")
        else:
            self.parent.Plugins.RecentConns.notify(object_path, uuid)

        if uuid == '00000000-0000-0000-0000-000000000000':
            device = Device(obj_path=object_path)
            device.connect(reply_handler=ok, error_handler=err)
        else:
            service = get_service(Device(obj_path=object_path), uuid)
            assert service is not None

            if any(plugin.service_connect_handler(service, ok, err)
                   for plugin in self.parent.Plugins.get_loaded_plugins(ServiceConnectHandler)):
                pass
            elif isinstance(service, SerialService):
                def reply(rfcomm: str) -> None:
                    assert isinstance(service, SerialService)  # https://github.com/python/mypy/issues/2608
                    for plugin in self.parent.Plugins.get_loaded_plugins(RFCOMMConnectedListener):
                        plugin.on_rfcomm_connected(service, rfcomm)
                    ok()

                if not any(plugin.rfcomm_connect_handler(service, reply, err)
                           for plugin in self.parent.Plugins.get_loaded_plugins(RFCOMMConnectHandler)):
                    service.connect(reply_handler=lambda port: ok(), error_handler=err)
            elif isinstance(service, NetworkService):
                service.connect(reply_handler=lambda interface: ok(), error_handler=err)
            else:
                logging.info("No handler registered")
                err("Service not supported\nPossibly the plugin that handles this service is not loaded")

    def _disconnect_service(self, object_path: ObjectPath, uuid: str, port: int, ok: Callable[[], None],
                            err: Callable[[Union[BluezDBusException, "NMConnectionError",
                                                 GLib.Error, str]], None]) -> None:
        if uuid == '00000000-0000-0000-0000-000000000000':
            device = Device(obj_path=object_path)
            device.disconnect(reply_handler=ok, error_handler=err)
        else:
            service = get_service(Device(obj_path=object_path), uuid)
            assert service is not None

            if any(plugin.service_disconnect_handler(service, ok, err)
                   for plugin in self.parent.Plugins.get_loaded_plugins(ServiceConnectHandler)):
                pass
            elif isinstance(service, SerialService):
                service.disconnect(port, reply_handler=ok, error_handler=err)

                for plugin in self.parent.Plugins.get_loaded_plugins(RFCOMMConnectedListener):
                    plugin.on_rfcomm_disconnect(port)

                logging.info("Disconnecting rfcomm device")
            elif isinstance(service, NetworkService):
                service.disconnect(reply_handler=ok, error_handler=err)

    def _open_plugin_dialog(self) -> None:
        self.parent.Plugins.StandardItems.on_plugins()
