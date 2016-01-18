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

        self._object_manager = Gio.ObjectManagerClient.new_for_bus_sync(
            Gio.BusType.SYSTEM, Gio.DBusObjectManagerClientFlags.NONE,
            self.__bus_name, '/', None, None, None)

    def find_device(self, address):
        for device in self.list_devices():
            if device['Address'] == address:
                return device

    def list_devices(self):
        paths = []
        for obj_proxy in self._object_manager.get_objects():
            proxy = obj_proxy.get_interface('org.bluez.Device1')

            if proxy: paths.append(proxy.get_object_path())

        return [Device(path) for path in paths]

    def start_discovery(self):
        self._call('StartDiscovery')

    def stop_discovery(self):
        self._call('StopDiscovery')

    def remove_device(self, device):
        self._call('RemoveDevice', 'o', device.get_object_path())

    def get_name(self):
        if 'Alias' in self:
            return self['Alias']
        else:
            return self['Name']

    def set_name(self, name):
        try:
            return self.set('Alias', name)
        # TODO: Test
        except GLib.Error:
            return self.set('Name', name)
