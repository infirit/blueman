# coding=utf-8
import os
import struct
from blueman.plugins.MechanismPlugin import MechanismPlugin
from blueman.plugins.applet.KillSwitch import RFKILL_TYPE_BLUETOOTH, RFKILL_OP_CHANGE_ALL
from blueman.main.DbusService import *
from gi.repository import Gio

if not os.path.exists('/dev/rfkill'):
    raise ImportError("Hardware kill switch not found")


class MechanismRfkillService(DbusService):
    def __init__(self, plugin, **kwargs):
        super().__init__(bus_name='org.blueman.Mechanism', path='/org/blueman/Mechanism', **kwargs)
        self.plugin = plugin

    @dbus_method(interface='org.blueman.Mechanism.RfKill', in_signature="b", out_signature="", sender_keyword="caller")
    def SetRfkillState(self, state, caller):
        self.plugin.confirm_authorization(caller, "org.blueman.rfkill.setstate")
        with open('/dev/rfkill', 'r+b', buffering=0) as f:
            f.write(struct.pack("IBBBB", 0, RFKILL_TYPE_BLUETOOTH, RFKILL_OP_CHANGE_ALL, (0 if state else 1), 0))


class RfKill(MechanismPlugin):
    dbus_service = None

    def on_load(self):
        connection = Gio.bus_get_sync(Gio.BusType.SYSTEM)
        self.dbus_service = MechanismRfkillService(self, connection=connection)
        self.dbus_service.connect_bus()
