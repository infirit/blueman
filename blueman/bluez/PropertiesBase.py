from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

import sys
from gi.repository import GObject, GLib
from blueman.Functions import dprint
from blueman.bluez.Base import Base


class PropertiesBase(Base):
    __gsignals__ = {
        str('property-changed'): (GObject.SignalFlags.NO_HOOKS, None,
                                  (GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT, GObject.TYPE_PYOBJECT))
    }

    if sys.version_info.major < 3:
        __variant_map = {str: 's', unicode: 's', int: 'i', bool: 'b'}
    else:
        __variant_map = {str: 's', int: 'i', bool: 'b'}

    def __init__(self, interface, obj_path):
        super(PropertiesBase, self).__init__(interface, obj_path)

        sig = self.__dbus_proxy.connect("g-properties-changed", self._on_properties_changed)
        self.__signals.append(sig)

    def _on_properties_changed(self, proxy, changed, invalidates):
        for key, val in changed.unpack().items():
            path = proxy.get_object_path()
            self.emit("property-changed", key, val, path)

    def get(self, name):
        return self.__dbus_proxy.get_cached_property(name)

    def set(self, name, value):
        variant = GLib.Variant(self.__variant_map[type(value)], value)
        self.dbus_proxy.set_cached_property(name, variant)

    def get_properties(self):
        return dict((name, self._dbus_proxy.get_cached_property(name).unpack()) for name in property_names

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self.set(key, value)

    def __contains__(self, key):
        return key in self.get_properties()
