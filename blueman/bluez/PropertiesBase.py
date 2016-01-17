from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

from gi.repository import GObject
from blueman.Functions import dprint
from blueman.bluez.Base import Base
import dbus


class PropertiesBase(Base):
    __gsignals__ = {
        str('property-changed'): (GObject.SignalFlags.NO_HOOKS, None,
                                  (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT))
    }

    def __init__(self, interface, obj_path):
        super(PropertiesBase, self).__init__(interface, obj_path)

        self._handler_wrappers = {}

        if obj_path:
            self.__properties_interface = dbus.Interface(self._dbus_proxy, 'org.freedesktop.DBus.Properties')

        self._handle_signal(self._on_properties_changed, 'PropertiesChanged', 'org.freedesktop.DBus.Properties',
                            path_keyword='path')

    def _on_property_changed(self, key, value, path):
        dprint(path, key, value)
        self.emit('property-changed', key, value, path)

    def _on_properties_changed(self, interface_name, changed_properties, _invalidated_properties, path):
        if interface_name == self._interface_name:
            for name, value in changed_properties.items():
                self._on_property_changed(name, value, path)

    @raise_dbus_error
    def get(self, name):
        return self.__properties_interface.Get(self._interface_name, name)

    def set(self, name, value):
        if type(value) is int:
            value = dbus.UInt32(value)
        return self._call('Set', self._interface_name, name, value, interface=self.__properties_interface)

    def get_properties(self):
        return self._call('GetAll', self._interface_name, interface=self.__properties_interface)

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self.set(key, value)

    def __contains__(self, key):
        return key in self.get_properties()
