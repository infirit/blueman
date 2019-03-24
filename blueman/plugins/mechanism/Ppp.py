# coding=utf-8
from blueman.plugins.MechanismPlugin import MechanismPlugin
from blueman.main.DbusService import *
from gi.repository import Gio


class MechanismPppService(DbusService):
    def __init__(self, plugin, **kwargs):
        super().__init__(bus_name='org.blueman.Mechanism', path='/org/blueman/Mechanism', **kwargs)
        self.plugin = plugin

    def ppp_connected(self, ppp, port, ok):
        ok(port)
        self.plugin.timer.resume()

    def ppp_error(self, ppp, message, err):
        err(message)
        self.plugin.timer.resume()

    @dbus_method(interface='org.blueman.Mechanism.Ppp', in_signature="sss", out_signature="s",
                 sender_keyword="caller", invocation_keyword='invocation')
    def PPPConnect(self, port, number, apn, caller, invocation):
        self.plugin.confirm_authorization(caller, "org.blueman.pppd.pppconnect")
        self.plugin.timer.stop()
        from blueman.main.PPPConnection import PPPConnection

        ppp = PPPConnection(port, number, apn)
        ppp.connect("error-occurred", self.ppp_error, invocation.return_error)
        ppp.connect("connected", self.ppp_connected, invocation.return_value)

        ppp.connect_rfcomm()


class Ppp(MechanismPlugin):
    dbus_service = None

    def on_load(self):
        connection = Gio.bus_get_sync(Gio.BusType.SYSTEM)
        self.dbus_service = MechanismPppService(self, connection=connection)
        self.dbus_service.connect_bus()
