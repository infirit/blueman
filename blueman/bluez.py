# coding=utf-8
from typing import List, Callable, Optional, Any, Union, Dict

from gi.repository import Gio, GLib, GObject
from gi.types import GObjectMeta
from blueman.gobject import SingletonGObjectMeta
import logging

from blueman.typing import GSignals


class BluezDBusException(Exception):
    def __init__(self, reason: str):
        self.reason = reason

    def __str__(self) -> str:
        return self.reason


class DBusFailedError(BluezDBusException):
    pass


class DBusInvalidArgumentsError(BluezDBusException):
    pass


class DBusNotAuthorizedError(BluezDBusException):
    pass


class DBusOutOfMemoryError(BluezDBusException):
    pass


class DBusNoSuchAdapterError(BluezDBusException):
    pass


class DBusNotReadyError(BluezDBusException):
    pass


class DBusNotAvailableError(BluezDBusException):
    pass


class DBusNotConnectedError(BluezDBusException):
    pass


class DBusConnectionAttemptFailedError(BluezDBusException):
    pass


class DBusAlreadyExistsError(BluezDBusException):
    pass


class DBusDoesNotExistError(BluezDBusException):
    pass


class DBusNoReplyError(BluezDBusException):
    pass


class DBusInProgressError(BluezDBusException):
    pass


class DBusNotSupportedError(BluezDBusException):
    pass


class DBusAuthenticationFailedError(BluezDBusException):
    pass


class DBusAuthenticationTimeoutError(BluezDBusException):
    pass


class DBusAuthenticationRejectedError(BluezDBusException):
    pass


class DBusAuthenticationCanceledError(BluezDBusException):
    pass


class DBusUnsupportedMajorClassError(BluezDBusException):
    pass


class DBusServiceUnknownError(BluezDBusException):
    pass


class DBusMainLoopNotSupportedError(BluezDBusException):
    pass


class DBusMainLoopModuleNotFoundError(BluezDBusException):
    pass


class BluezUnavailableAgentMethodError(BluezDBusException):
    pass


__DICT_ERROR__ = {'org.bluez.Error.Failed': DBusFailedError,
                  'org.bluez.Error.InvalidArguments': DBusInvalidArgumentsError,
                  'org.bluez.Error.NotAuthorized': DBusNotAuthorizedError,
                  'org.bluez.Error.OutOfMemory': DBusOutOfMemoryError,
                  'org.bluez.Error.NoSuchAdapter': DBusNoSuchAdapterError,
                  'org.bluez.Error.NotReady': DBusNotReadyError,
                  'org.bluez.Error.NotAvailable': DBusNotAvailableError,
                  'org.bluez.Error.NotConnected': DBusNotConnectedError,
                  'org.bluez.serial.Error.ConnectionAttemptFailed': DBusConnectionAttemptFailedError,
                  'org.bluez.Error.AlreadyExists': DBusAlreadyExistsError,
                  'org.bluez.Error.DoesNotExist': DBusDoesNotExistError,
                  'org.bluez.Error.InProgress': DBusInProgressError,
                  'org.bluez.Error.NoReply': DBusNoReplyError,
                  'org.bluez.Error.NotSupported': DBusNotSupportedError,
                  'org.bluez.Error.AuthenticationFailed': DBusAuthenticationFailedError,
                  'org.bluez.Error.AuthenticationTimeout': DBusAuthenticationTimeoutError,
                  'org.bluez.Error.AuthenticationRejected': DBusAuthenticationRejectedError,
                  'org.bluez.Error.AuthenticationCanceled': DBusAuthenticationCanceledError,
                  'org.bluez.serial.Error.NotSupported': DBusNotSupportedError,
                  'org.bluez.Error.UnsupportedMajorClass': DBusUnsupportedMajorClassError,
                  'org.freedesktop.DBus.Error.ServiceUnknown': DBusServiceUnknownError}


def parse_dbus_error(exception: GLib.Error) -> BluezDBusException:
    global __DICT_ERROR__

    gerror, dbus_error, message = exception.message.split(':', 2)
    try:
        return __DICT_ERROR__[dbus_error](message)
    except KeyError:
        return BluezDBusException(dbus_error + message)


class BaseMeta(GObjectMeta):
    def __call__(cls, **kwargs: str) -> "Base":
        if not hasattr(cls, "__instances__"):
            cls.__instances__: Dict[str, "Base"] = {}

        path = kwargs.get('obj_path')
        if path is None:
            path = cls._obj_path

        if path in cls.__instances__:
            return cls.__instances__[path]

        instance: "Base" = super().__call__(**kwargs)
        cls.__instances__[path] = instance

        return instance


class Base(Gio.DBusProxy, metaclass=BaseMeta):
    connect_signal = GObject.GObject.connect
    disconnect_signal = GObject.GObject.disconnect

    __name = 'org.bluez'
    __bus_type = Gio.BusType.SYSTEM

    __gsignals__: GSignals = {
        'property-changed': (GObject.SignalFlags.NO_HOOKS, None, (str, object, str))
    }
    __instances__: Dict[str, "Base"]

    def __init__(self, obj_path: str):
        super().__init__(
            g_name=self.__name,
            g_interface_name=self._interface_name,
            g_object_path=obj_path,
            g_bus_type=self.__bus_type,
            # FIXME See issue 620
            g_flags=Gio.DBusProxyFlags.GET_INVALIDATED_PROPERTIES)

        self.init()
        self.__fallback = {'Icon': 'blueman', 'Class': 0, 'Appearance': 0}

        self.__variant_map = {str: 's', int: 'u', bool: 'b'}

    def do_g_properties_changed(self, changed_properties: GLib.Variant, _invalidated_properties: List[str]) -> None:
        changed = changed_properties.unpack()
        object_path = self.get_object_path()
        logging.debug("%s %s" % (object_path, changed))
        for key, value in changed.items():
            self.emit("property-changed", key, value, object_path)

    def _call(
        self,
        method: str,
        param: GLib.Variant = None,
        reply_handler: Optional[Callable[..., None]] = None,
        error_handler: Optional[Callable[[BluezDBusException], None]] = None,
    ) -> None:
        def callback(
            proxy: Base,
            result: Gio.Task,
            reply: Optional[Callable[..., None]],
            error: Optional[Callable[[BluezDBusException], None]],
        ) -> None:
            try:
                value = proxy.call_finish(result).unpack()
                if reply:
                    reply(*value)
            except GLib.Error as e:
                if error:
                    error(parse_dbus_error(e))
                else:
                    raise parse_dbus_error(e)

        self.call(method, param, Gio.DBusCallFlags.NONE, GLib.MAXINT, None,
                  callback, reply_handler, error_handler)

    def get(self, name: str, interface_name: Optional[str] = None) -> Any:
        if interface_name is None:
            interface_name = self._interface_name

        try:
            prop = self.call_sync(
                'org.freedesktop.DBus.Properties.Get',
                GLib.Variant('(ss)', (interface_name, name)),
                Gio.DBusCallFlags.NONE,
                GLib.MAXINT,
                None)
            return prop.unpack()[0]
        except GLib.Error as e:
            if name in self.get_cached_property_names():
                return self.get_cached_property(name).unpack()
            elif name in self.__fallback:
                return self.__fallback[name]
            else:
                raise parse_dbus_error(e)

    def set(self, name: str, value: Union[str, int, bool]) -> None:
        v = GLib.Variant(self.__variant_map[type(value)], value)
        param = GLib.Variant('(ssv)', (self._interface_name, name, v))
        self.call('org.freedesktop.DBus.Properties.Set',
                  param,
                  Gio.DBusCallFlags.NONE,
                  GLib.MAXINT,
                  None)

    def get_properties(self) -> Dict[str, Any]:
        param = GLib.Variant('(s)', (self._interface_name,))
        res = self.call_sync('org.freedesktop.DBus.Properties.GetAll',
                             param,
                             Gio.DBusCallFlags.NONE,
                             GLib.MAXINT,
                             None)

        props: Dict[str, Any] = res.unpack()[0]
        for k, v in self.__fallback.items():
            if k in props:
                continue
            else:
                props[k] = v

        return props

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __setitem__(self, key: str, value: Union[str, int, bool]) -> None:
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        return key in self.get_properties()


class Device(Base):
    _interface_name = 'org.bluez.Device1'

    def __init__(self, obj_path: str):
        super().__init__(obj_path=obj_path)

    def pair(
        self,
        reply_handler: Optional[Callable[[], None]] = None,
        error_handler: Optional[Callable[[BluezDBusException], None]] = None,
    ) -> None:
        self._call('Pair', reply_handler=reply_handler, error_handler=error_handler)

    def connect(
        self,
        reply_handler: Optional[Callable[[], None]] = None,
        error_handler: Optional[Callable[[BluezDBusException], None]] = None,
    ) -> None:
        self._call('Connect', reply_handler=reply_handler, error_handler=error_handler)

    def disconnect(
        self,
        reply_handler: Optional[Callable[[], None]] = None,
        error_handler: Optional[Callable[[BluezDBusException], None]] = None,
    ) -> None:
        self._call('Disconnect', reply_handler=reply_handler, error_handler=error_handler)

    def connect_network(
        self,
        uuid: str,
        reply_handler: Optional[Callable[[str], None]] = None,
        error_handler: Optional[Callable[[BluezDBusException], None]] = None,
    ) -> None:
        param = GLib.Variant('(s)', (uuid,))
        self._call('org.bluez.Network1.Connect', param, reply_handler=reply_handler, error_handler=error_handler)

    def disconnect_network(
        self,
        reply_handler: Optional[Callable[[], None]] = None,
        error_handler: Optional[Callable[[BluezDBusException], None]] = None,
    ) -> None:
        self._call('org.bluez.Network1.Disconnect', reply_handler=reply_handler, error_handler=error_handler)

    @property
    def network_connected(self) -> bool:
        connected: bool = self.get("Connected", "org.bluez.Network1")
        return connected

    @property
    def network_interface(self) -> str:
        interface_name: str = self.get("Interface")
        return interface_name


class Adapter(Base):
    _interface_name = 'org.bluez.Adapter1'

    def __init__(self, obj_path: str):
        super().__init__(obj_path=obj_path)

    def start_discovery(self) -> None:
        self._call('StartDiscovery')

    def stop_discovery(self) -> None:
        self._call('StopDiscovery')

    def remove_device(self, device: Device) -> None:
        param = GLib.Variant('(o)', (device.get_object_path(),))
        self._call('RemoveDevice', param)

    def get_name(self) -> str:
        name: str = self['Alias']
        return name

    def set_name(self, name: str) -> None:
        self.set('Alias', name)

    def register_network(self, uuid: str, bridge: str) -> None:
        param = GLib.Variant('(ss)', (uuid, bridge))
        self._call('org.bluez.NetworkServer1.Register', param)

    def unregister_network(self, uuid: str) -> None:
        param = GLib.Variant('(s)', (uuid,))
        self._call('org.bluez.NetworkServer1.Unregister', param)


class Manager(GObject.GObject, metaclass=SingletonGObjectMeta):
    __gsignals__: GSignals = {
        'adapter-added': (GObject.SignalFlags.NO_HOOKS, None, (str,)),
        'adapter-removed': (GObject.SignalFlags.NO_HOOKS, None, (str,)),
        'device-created': (GObject.SignalFlags.NO_HOOKS, None, (str,)),
        'device-removed': (GObject.SignalFlags.NO_HOOKS, None, (str,)),
    }

    connect_signal = GObject.GObject.connect
    disconnect_signal = GObject.GObject.disconnect

    __bus_name = 'org.bluez'

    def __init__(self) -> None:
        super().__init__()
        self._object_manager = Gio.DBusObjectManagerClient.new_for_bus_sync(
            Gio.BusType.SYSTEM, Gio.DBusObjectManagerClientFlags.DO_NOT_AUTO_START,
            self.__bus_name, '/', None, None, None)

        self._object_manager.connect("object-added", self._on_object_added)
        self._object_manager.connect("object-removed", self._on_object_removed)

    def _on_object_added(self, _object_manager: Gio.DBusObjectManager, dbus_object: Gio.DBusObject) -> None:
        device_proxy = dbus_object.get_interface('org.bluez.Device1')
        adapter_proxy = dbus_object.get_interface('org.bluez.Adapter1')

        if adapter_proxy:
            object_path = adapter_proxy.get_object_path()
            logging.debug(object_path)
            self.emit('adapter-added', object_path)
        elif device_proxy:
            object_path = device_proxy.get_object_path()
            logging.debug(object_path)
            self.emit('device-created', object_path)

    def _on_object_removed(self, _object_manager: Gio.DBusObjectManager, dbus_object: Gio.DBusObject) -> None:
        device_proxy = dbus_object.get_interface('org.bluez.Device1')
        adapter_proxy = dbus_object.get_interface('org.bluez.Adapter1')

        if adapter_proxy:
            object_path = adapter_proxy.get_object_path()
            logging.debug(object_path)
            self.emit('adapter-removed', object_path)
        elif device_proxy:
            object_path = device_proxy.get_object_path()
            logging.debug(object_path)
            self.emit('device-removed', object_path)

    def get_adapters(self) -> List[Adapter]:
        paths = []
        for obj_proxy in self._object_manager.get_objects():
            proxy = obj_proxy.get_interface('org.bluez.Adapter1')

            if proxy:
                paths.append(proxy.get_object_path())

        return [Adapter(obj_path=path) for path in paths]

    def get_adapter(self, pattern: Optional[str] = None) -> Adapter:
        adapters = self.get_adapters()
        if pattern is None:
            if len(adapters):
                return adapters[0]
            else:
                raise DBusNoSuchAdapterError("No adapter(s) found")
        else:
            for adapter in adapters:
                path = adapter.get_object_path()
                if path.endswith(pattern) or adapter['Address'] == pattern:
                    return adapter
            raise DBusNoSuchAdapterError("No adapters found with pattern: %s" % pattern)

    def get_devices(self, adapter_path: str = "/") -> List[Device]:
        paths = []
        for obj_proxy in self._object_manager.get_objects():
            proxy = obj_proxy.get_interface('org.bluez.Device1')

            if proxy:
                object_path = proxy.get_object_path()
                if object_path.startswith(adapter_path):
                    paths.append(object_path)

        return [Device(obj_path=path) for path in paths]

    def find_device(self, address: str, adapter_path: str = "/") -> Optional[Device]:
        for device in self.get_devices(adapter_path):
            if device['Address'] == address:
                return device
        return None

    @classmethod
    def watch_name_owner(
        cls,
        appeared_handler: Callable[[Gio.DBusConnection, str, str], None],
        vanished_handler: Callable[[Gio.DBusConnection, str], None],
    ) -> None:
        Gio.bus_watch_name(Gio.BusType.SYSTEM, cls.__bus_name, Gio.BusNameWatcherFlags.AUTO_START,
                           appeared_handler, vanished_handler)


class AgentManager(Base):
    _interface_name = 'org.bluez.AgentManager1'
    _obj_path = '/org/bluez'

    def __init__(self) -> None:
        super().__init__(obj_path=self._obj_path)

    def register_agent(self, agent_path: str, capability: str = "", default: bool = False) -> None:
        param = GLib.Variant('(os)', (agent_path, capability))
        self._call('RegisterAgent', param)
        if default:
            default_param = GLib.Variant('(o)', (agent_path,))
            self._call('RequestDefaultAgent', default_param)

    def unregister_agent(self, agent_path: str) -> None:
        param = GLib.Variant('(o)', (agent_path,))
        self._call('UnregisterAgent', param)


class AnyBase(GObject.GObject):
    __gsignals__: GSignals = {
        'property-changed': (GObject.SignalFlags.NO_HOOKS, None, (str, object, str))
    }

    connect_signal = GObject.GObject.connect
    disconnect_signal = GObject.GObject.disconnect

    __bus = Gio.bus_get_sync(Gio.BusType.SYSTEM)
    __bus_name = 'org.bluez'
    __bus_interface_name = 'org.freedesktop.DBus.Properties'

    def __init__(self, interface_name: str):
        super().__init__()

        self.__interface_name = interface_name
        self.__signal = None

        def on_signal(
            _connection: Gio.DBusConnection,
            _sender_name: str,
            object_path: str,
            _interface_name: str,
            _signal_name: str,
            param: GLib.Variant,
        ) -> None:
            iface_name, changed, invalidated = param.unpack()
            if iface_name == self.__interface_name:
                self._on_properties_changed(object_path, changed, invalidated)

        self.__signal = self.__bus.signal_subscribe(
            self.__bus_name, self.__bus_interface_name, 'PropertiesChanged', None, None,
            Gio.DBusSignalFlags.NONE, on_signal)

    def _on_properties_changed(
        self, object_path: str, changed_properties: Dict[str, object], _invalidated: List[str]
    ) -> None:
        for name, value in changed_properties.items():
            self.emit('property-changed', name, value, object_path)

    def close(self) -> None:
        if self.__signal:
            self.__bus.signal_unsubscribe(self.__signal)
            self.__signal = None
        self.__bus = None


class AnyDevice(AnyBase):
    def __init__(self) -> None:
        super().__init__('org.bluez.Device1')


class AnyNetwork(AnyBase):
    def __init__(self) -> None:
        super().__init__('org.bluez.Network1')


class AnyAdapter(AnyBase):
    def __init__(self) -> None:
        super().__init__('org.bluez.Adapter1')
