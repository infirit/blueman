# coding=utf-8
from blueman.main.DBusServiceObject import *
from gi.repository import Gio
import logging


__all__ = ['dbus_method', 'DBusPropery', 'dbus_signal', 'DbusService']


class DbusService(DBusServiceObject):
    def __init__(self, bus_name='org.blueman.Applet', path='/', **kwargs):
        super().__init__(object_path=path, **kwargs)
        self.__bus_name = bus_name
        self._bus_id = None

    @staticmethod
    def _on_name_acquired(conn, name):
        logging.debug('Got bus name: %s' % name)

    def connect_bus(self):
        self._bus_id = Gio.bus_own_name_on_connection(self.connection, self.__bus_name, Gio.BusNameOwnerFlags.NONE,
                                                      self._on_name_acquired, None)

    def disconnect_bus(self):
        if self._bus_id:
            Gio.bus_unown_name(self._bus_id)
        self._bus_id = None
        self.set_property('connection', None)
