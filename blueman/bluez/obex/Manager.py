from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

from blueman.Functions import dprint
from blueman.bluez.obex.Transfer import Transfer
from blueman.bluez.obex.Base import Base
from gi.repository import GObject


class Manager(Base):
    __gsignals__ = {
        str('session-removed'): (GObject.SignalFlags.NO_HOOKS, None, (GObject.TYPE_PYOBJECT,)),
        str('transfer-started'): (GObject.SignalFlags.NO_HOOKS, None, (GObject.TYPE_PYOBJECT,)),
        str('transfer-completed'): (GObject.SignalFlags.NO_HOOKS, None, (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT)),
    }

    def __init__(self):
        super(Manager, self).__init__()

        self._transfers = {}

        self._object_manager = Gio.ObjectManagerClient.new_sync(
            self.__bus, Gio.DBusObjectManagerClientFlags.None,
            self.bus_name, '/', None, None,None)

        self.object_manager.connect("object-added", self._on_object_added)
        self.object_manager.connect("object-removed", self._on_object_removed)

    def _on_object_added(self, object_manager, dbus_object):
        transfer_proxy = dbus_object.get_interface('org.bluez.obex.Transfer1')

        if transfer_proxy:
            object_path = transfer_proxy.get_object_path()
            bluez_transfer = Transfer(object_path)

            complete_sig = bluez_transfer.connect('completed', self._on_transfer_completed, True)
            error_sig = bluez_transfer.connect('error', self._on_tranfer_completed, False)

            self._transfers[object_path] = (bluez_transfer, (complete_sig, error_sig))
            self._on_transfer_started(object_path)

    def _on_object_removed(self, object_manager, dbus_object):
        session_proxy = dbus_object.get_interface('org.bluez.obex.Session1')

        if session_proxy:
            object_path = session_proxy.get_object_path()
            self._on_session_removed(object_path)

    def _on_session_removed(self, session_path):
        dprint(session_path)
        self.emit('session-removed', session_path)

    def _on_transfer_started(self, transfer_path):
        dprint(transfer_path)
        self.emit('transfer-started', transfer_path)

    def _on_transfer_completed(self, transfer_path, success):
        dprint(transfer_path, success)
        bluez_transfer, signals = self._transfers.pop(transfer_path)
        for sig in signals: bluez_transfer.disconnect(sig)
        self.emit('transfer-completed', transfer_path, success)
