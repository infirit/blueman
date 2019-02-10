# coding=utf-8
from gi.repository import Gio, GLib
from gi.types import GObjectMeta


class DBusProxyFailed(Exception):
    pass


class ProxyBaseMeta(GObjectMeta):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        interface_name = kwargs.get('interface_name')
        if interface_name is None:
            raise ValueError('the keyword interface_name is required for proper operation')

        if interface_name not in cls._instances:
            cls._instances[interface_name] = super().__call__(*args, **kwargs)
        return cls._instances[interface_name]


class ProxyBase(Gio.DBusProxy, metaclass=ProxyBaseMeta):
    def __init__(self, name, interface_name, object_path, systembus=False, **kwargs):
        if systembus:
            bustype = Gio.BusType.SYSTEM
        else:
            bustype = Gio.BusType.SESSION

        super().__init__(
            g_name=name,
            g_interface_name=interface_name,
            g_object_path=object_path,
            g_bus_type=bustype,
            g_flags=Gio.DBusProxyFlags.NONE,
            **kwargs
        )

        try:
            self.init()
        except GLib.Error as e:
            raise DBusProxyFailed(e.message)

    def method_call(self, method, param=None):
        res = self.call_sync(method, param, Gio.DBusCallFlags.NONE, GLib.MAXINT, None)
        return res.unpack()


class Mechanism(ProxyBase):
    def __init__(self, interface_name, name='org.blueman.Mechanism',
                 object_path='/', **kwargs):
        super().__init__(name=name, interface_name=interface_name, object_path=object_path, systembus=True, **kwargs)


class AppletService(ProxyBase):
    def __init__(self, interface_name, name='org.blueman.Applet',
                 object_path='/org/blueman/Applet', **kwargs):
        super().__init__(name=name, interface_name=interface_name, object_path=object_path, **kwargs)
