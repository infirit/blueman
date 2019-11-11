# coding=utf-8
import logging
import weakref
from typing import Dict, Callable, Optional, List
from gi.repository import Gio, GObject, GLib

from blueman.bluez import Base as BlueZBase
from blueman.bluez import BluezDBusException
from blueman.gobject import SingletonGObjectMeta

from blueman.typing import GSignals


class Base(BlueZBase):
    __bus_type = Gio.BusType.SESSION
    __name = 'org.bluez.obex'


class Client(Base):
    __gsignals__: GSignals = {
        'session-failed': (GObject.SignalFlags.NO_HOOKS, None, (str,)),
    }

    _interface_name = 'org.bluez.obex.Client1'
    _obj_path = '/org/bluez/obex'

    def __init__(self) -> None:
        super().__init__(obj_path=self._obj_path)

    def create_session(self, dest_addr: str, source_addr: str = "00:00:00:00:00:00", pattern: str = "opp") -> None:
        def on_session_created(session_path: str) -> None:
            logging.info("%s %s %s %s" % (dest_addr, source_addr, pattern, session_path))

        def on_session_failed(error: BluezDBusException) -> None:
            logging.error("%s %s %s %s" % (dest_addr, source_addr, pattern, error))
            self.emit("session-failed", error)

        v_source_addr = GLib.Variant('s', source_addr)
        v_pattern = GLib.Variant('s', pattern)
        param = GLib.Variant('(sa{sv})', (dest_addr, {"Source": v_source_addr, "Target": v_pattern}))
        self._call('CreateSession', param, reply_handler=on_session_created, error_handler=on_session_failed)

    def remove_session(self, session_path: str) -> None:
        def on_session_removed() -> None:
            logging.info(session_path)

        def on_session_remove_failed(error: BluezDBusException) -> None:
            logging.error("%s %s" % (session_path, error))

        param = GLib.Variant('(o)', (session_path,))
        self._call('RemoveSession', param, reply_handler=on_session_removed,
                   error_handler=on_session_remove_failed)


class Manager(GObject.GObject, metaclass=SingletonGObjectMeta):
    __gsignals__: GSignals = {
        'session-added': (GObject.SignalFlags.NO_HOOKS, None, (str,)),
        'session-removed': (GObject.SignalFlags.NO_HOOKS, None, (str,)),
        'transfer-started': (GObject.SignalFlags.NO_HOOKS, None, (str,)),
        'transfer-completed': (GObject.SignalFlags.NO_HOOKS, None, (str, bool)),
    }

    connect_signal = GObject.GObject.connect
    disconnect_signal = GObject.GObject.disconnect

    __bus_name = 'org.bluez.obex'

    def __init__(self) -> None:
        super().__init__()
        self.__transfers: Dict[str, Transfer] = {}

        self._object_manager = Gio.DBusObjectManagerClient.new_for_bus_sync(
            Gio.BusType.SESSION, Gio.DBusObjectManagerClientFlags.NONE,
            self.__bus_name, '/', None, None, None)

        self._object_manager.connect('object-added', self._on_object_added)
        self._object_manager.connect('object-removed', self._on_object_removed)

        weakref.finalize(self, self._on_delete)

    def _on_delete(self) -> None:
        self._object_manager.disconnect_by_func(self._on_object_added)
        self._object_manager.disconnect_by_func(self._on_object_removed)

    def _on_object_added(self, _object_manager: Gio.DBusObjectManager, dbus_object: Gio.DBusObject) -> None:
        session_proxy = dbus_object.get_interface('org.bluez.obex.Session1')
        transfer_proxy = dbus_object.get_interface('org.bluez.obex.Transfer1')
        object_path = dbus_object.get_object_path()

        if transfer_proxy:
            logging.info(object_path)
            transfer = Transfer(obj_path=object_path)
            transfer.connect_signal('completed', self._on_transfer_completed, True)
            transfer.connect_signal('error', self._on_transfer_completed, False)
            self.__transfers[object_path] = transfer
            self.emit('transfer-started', object_path)

        if session_proxy:
            logging.info(object_path)
            self.emit('session-added', object_path)

    def _on_object_removed(self, _object_manager: Gio.DBusObjectManager, dbus_object: Gio.DBusObject) -> None:
        session_proxy = dbus_object.get_interface('org.bluez.obex.Session1')
        transfer_proxy = dbus_object.get_interface('org.bluez.obex.Transfer1')
        object_path = dbus_object.get_object_path()

        if transfer_proxy and object_path in self.__transfers:
            logging.info(object_path)
            transfer = self.__transfers.pop(object_path)

            # Disconnect as many times as we connect (pygobject bug #106)
            transfer.disconnect_by_func(self._on_transfer_completed)
            transfer.disconnect_by_func(self._on_transfer_completed)

        if session_proxy:
            logging.info(object_path)
            self.emit('session-removed', object_path)

    def _on_transfer_completed(self, transfer: "Transfer", success: bool) -> None:
        transfer_path = transfer.get_object_path()

        logging.info("%s %s" % (transfer_path, success))
        self.emit('transfer-completed', transfer_path, success)

    @classmethod
    def watch_name_owner(
        cls,
        appeared_handler: Callable[[Gio.DBusConnection, str, str], None],
        vanished_handler: Callable[[Gio.DBusConnection, str], None],
    ) -> None:
        Gio.bus_watch_name(Gio.BusType.SESSION, cls.__bus_name, Gio.BusNameWatcherFlags.AUTO_START,
                           appeared_handler, vanished_handler)


class AgentManager(Base):
    _interface_name = 'org.bluez.obex.AgentManager1'
    _obj_path = '/org/bluez/obex'

    def __init__(self) -> None:
        super().__init__(obj_path=self._obj_path)

    def register_agent(self, agent_path: str) -> None:
        def on_registered() -> None:
            logging.info(agent_path)

        def on_register_failed(error: BluezDBusException) -> None:
            logging.error("%s %s" % (agent_path, error))

        param = GLib.Variant('(o)', (agent_path,))
        self._call('RegisterAgent', param, reply_handler=on_registered, error_handler=on_register_failed)

    def unregister_agent(self, agent_path: str) -> None:
        def on_unregistered() -> None:
            logging.info(agent_path)

        def on_unregister_failed(error: BluezDBusException) -> None:
            logging.error("%s %s" % (agent_path, error))

        param = GLib.Variant('(o)', (agent_path,))
        self._call('UnregisterAgent', param, reply_handler=on_unregistered, error_handler=on_unregister_failed)


class ObjectPush(Base):
    __gsignals__: GSignals = {
        'transfer-started': (GObject.SignalFlags.NO_HOOKS, None, (str, str,)),
        'transfer-failed': (GObject.SignalFlags.NO_HOOKS, None, (str,)),
    }

    _interface_name = 'org.bluez.obex.ObjectPush1'

    def __init__(self, obj_path: str):
        super().__init__(obj_path=obj_path)

    def send_file(self, file_path: str) -> None:
        def on_transfer_started(transfer_path: str, props: Dict[str, str]) -> None:
            logging.info(" ".join((self.get_object_path(), file_path, transfer_path)))
            self.emit('transfer-started', transfer_path, props['Filename'])

        def on_transfer_error(error: BluezDBusException) -> None:
            logging.error("%s %s" % (file_path, error))
            self.emit('transfer-failed', error)

        param = GLib.Variant('(s)', (file_path,))
        self._call('SendFile', param, reply_handler=on_transfer_started, error_handler=on_transfer_error)

    def get_session_path(self) -> str:
        path: str = self.get_object_path()
        return path


class Session(Base):
    _interface_name = 'org.bluez.obex.Session1'

    def __init__(self, obj_path: str):
        super().__init__(obj_path=obj_path)

    @property
    def address(self) -> str:
        dest: str = self.get('Destination')
        return dest

    @property
    def root(self) -> str:
        root: str = self.get('Root')
        return root


class Transfer(Base):
    __gsignals__: GSignals = {
        'progress': (GObject.SignalFlags.NO_HOOKS, None, (int,)),
        'completed': (GObject.SignalFlags.NO_HOOKS, None, ()),
        'error': (GObject.SignalFlags.NO_HOOKS, None, ())
    }

    _interface_name = 'org.bluez.obex.Transfer1'

    def __init__(self, obj_path: str):
        super().__init__(obj_path=obj_path)

    @property
    def filename(self) -> Optional[str]:
        name: Optional[str] = self.get("Filename")
        return name

    @property
    def name(self) -> str:
        name: str = self.get("Name")
        return name

    @property
    def session(self) -> str:
        session: str = self.get("Session")
        return session

    @property
    def size(self) -> Optional[int]:
        size: Optional[int] = self.get("Size")
        return size

    def do_g_properties_changed(self, changed_properties: GLib.Variant, _invalidated_properties: List[str]) -> None:
        for name, value in changed_properties.unpack().items():
            logging.debug("%s %s %s" % (self.get_object_path(), name, value))
            if name == 'Transferred':
                self.emit('progress', value)
            elif name == 'Status':
                if value == 'complete':
                    self.emit('completed')
                elif value == 'error':
                    self.emit('error')
