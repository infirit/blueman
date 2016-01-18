from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals
from gi.repository import GObject
from blueman.Functions import dprint

from blueman.bluez.Adapter import Adapter
from blueman.bluez.PropertiesBase import PropertiesBase
from blueman.bluez.errors import DBusNoSuchAdapterError


class Manager(PropertiesBase):
    __gsignals__ = {
        str('adapter-added'): (GObject.SignalFlags.NO_HOOKS, None, (GObject.TYPE_PYOBJECT,)),
        str('adapter-removed'): (GObject.SignalFlags.NO_HOOKS, None, (GObject.TYPE_PYOBJECT,)),
        str('device-created'): (GObject.SignalFlags.NO_HOOKS, None, (GObject.TYPE_PYOBJECT,)),
        str('device-removed'): (GObject.SignalFlags.NO_HOOKS, None, (GObject.TYPE_PYOBJECT,)),
    }

    def __init__(self):
        super(Manager, self).__init__()
        self._object_manager = Gio.ObjectManagerClient.new_for_bus_sync(
            Gio.BusType.SYSTEM, Gio.DBusObjectManagerClientFlags.NONE,
            self.__bus_name, '/', None, None, None)

        self.object_manager.connect("object-added", self._on_object_added)
        self.object_manager.connect("object-removed", self._on_object_removed)

    def _on_object_added(self, object_manager, dbus_object):
        device_proxy = dbus_object.get_interface('org.bluez.Device1')
        adapter_proxy = dbus_object.get_interface('org.bluez.Adapter1')

        if adapter_proxy:
            object_path = adapter_proxy.get_object_path()
            dprint(object_path)
            self.emit('adapter-added', object_path)
        elif device_proxy:
            object_path = device_proxy.get_object_path()
            dprint(object_path)
            self.emit('device-created', object_path)

    def _on_object_removed(self, object_manager, dbus_object):
        device_proxy = dbus_object.get_interface('org.bluez.Device1')
        adapter_proxy = dbus_object.get_interface('org.bluez.Adapter1')

        if adapter_proxy:
            object_path = adapter_proxy.get_object_path()
            dprint(object_path)
            self.emit('adapter-removed', object_path)
        elif device_proxy:
            object_path = device_proxy.get_object_path()
            dprint(object_path)
            self.emit('device-removed', object_path)

    def list_devices(self):
        paths = []
        for obj_proxy in self._object_manager.get_objects():
            proxy = obj_proxy.get_interface('org.bluez.Device1')

            if proxy: paths.append(proxy.get_object_path())

        return [Device(path) for path in paths]

    def get_adapter(self, pattern=None):
        adapters = self.list_adapters()
        if pattern is None:
            if len(adapters):
                return adapters[0]
        else:
            for adapter in adapters:
                path = adapter.get_object_path()
                if path.endswith(pattern) or adapter.get_properties()['Address'] == pattern:
                    return adapter

        # If the given - or any - adapter does not exist, raise the NoSuchAdapter
        # error BlueZ 4's DefaultAdapter and FindAdapter methods trigger
        raise DBusNoSuchAdapterError('No such adapter')
