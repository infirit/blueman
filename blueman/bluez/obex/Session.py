# coding=utf-8
from blueman.bluez.obex.Base import Base
from gi.repository import GLib


class Session(Base):
    _interface_name = 'org.bluez.obex.Session1'

    def _init(self, session_path):
        super(Session, self)._init(interface_name=self._interface_name, obj_path=session_path)

    @property
    def address(self):
        return self.get('Destination')

    @property
    def root(self):
        return self.get('Root')
