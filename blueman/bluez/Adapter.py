from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

from gi.repository import GObject, Gio, GLib
from blueman.Functions import dprint
from blueman.bluez.PropertiesBase import PropertiesBase
from blueman.bluez.Device import Device


class Adapter(PropertiesBase):
    def __init__(self, obj_path=None):
        super(Adapter, self).__init__('org.bluez.Adapter1', obj_path)
        self._object_manager = Gio.DBusObjectManagerClient.new_for_bus_sync(Gio.BusType.SYSTEM,
                                                                            Gio.DBusObjectManagerClientFlags.NONE,
                                                                            'org.bluez', '/', None, None, None)

    def find_device(self, address):
        devices = self.list_devices()
        for device in devices:
            if device.get_properties()['Address'] == address:
                return device

    def list_devices(self):
        objects = self._object_manager.get_objects()
        devices = []
        for object in objects:
            for interface in object.get_interfaces():
                if interface.get_interface_name() == 'org.bluez.Device1':
                    devices.append(object.get_object_path())
        return [Device(device) for device in devices]

    def start_discovery(self):
        self._call('StartDiscovery')

    def stop_discovery(self):
        self._call('StopDiscovery')

    def remove_device(self, device):
        self._call('RemoveDevice', 'o', device.get_object_path())

    def get_name(self):
        props = self.get_properties()
        try:
            return props['Alias']
        except KeyError:
            return props['Name']

    def set_name(self, name):
        try:
            return self.set('Alias', name)
        # TODO: Test
        except GLib.Error:
            return self.set('Name', name)
