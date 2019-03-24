# coding=utf-8
import os
import subprocess
import signal
from blueman.Constants import RFCOMM_WATCHER_PATH
from blueman.plugins.MechanismPlugin import MechanismPlugin
from blueman.main.DbusService import *
from gi.repository import Gio


class MechanismRfcommService(DbusService):
    files = {}

    def __init__(self, plugin, **kwargs):
        super().__init__(bus_name='org.blueman.Mechanism', path='/org/blueman/Mechanism', **kwargs)
        self.plugin = plugin

    @dbus_method(interface='org.blueman.Mechanism.Rfcomm', in_signature="d")
    def open_rfcomm(self, port_id):
        subprocess.Popen([RFCOMM_WATCHER_PATH, '/dev/rfcomm%d' % port_id])

    @dbus_method(interface='org.blueman.Mechanism.Rfcomm', in_signature="d")
    def close_rfcomm(self, port_id):
        command = 'blueman-rfcomm-watcher /dev/rfcomm%d' % port_id

        out, err = subprocess.Popen(['ps', '-e', 'o', 'pid,args'], stdout=subprocess.PIPE).communicate()
        for line in out.decode("UTF-8").splitlines():
            pid, cmdline = line.split(maxsplit=1)
            if command in cmdline:
                os.kill(int(pid), signal.SIGTERM)


class Rfcomm(MechanismPlugin):
    dbus_service = None

    def on_load(self):
        connection = Gio.bus_get_sync(Gio.BusType.SYSTEM)
        self.dbus_service = MechanismRfcommService(self, connection=connection)
        self.dbus_service.connect_bus()
