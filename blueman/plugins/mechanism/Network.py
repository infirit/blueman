# coding=utf-8
from blueman.plugins.MechanismPlugin import MechanismPlugin
from blueman.main.NetConf import NetConf, DnsMasqHandler, DhcpdHandler, UdhcpdHandler
from blueman.main.DbusService import *
from gi.repository import Gio

DHCPDHANDLERS = {"DnsMasqHandler": DnsMasqHandler,
                 "DhcpdHandler": DhcpdHandler,
                 "UdhcpdHandler": UdhcpdHandler}

DBUS_INTERFACE = 'org.blueman.Mechanism.Network'


class MechanismNetworkService(DbusService):
    def __init__(self, plugin, **kwargs):
        super().__init__(bus_name='org.blueman.Mechanism', path='/org/blueman/Mechanism', **kwargs)
        self.plugin = plugin

    @dbus_method(interface=DBUS_INTERFACE, in_signature="s", out_signature="s", sender_keyword="caller",
                 invocation_keyword='invocation')
    def DhcpClient(self, net_interface, caller, invocation):
        self.plugin.timer.stop()

        self.plugin.confirm_authorization(caller, "org.blueman.dhcp.client")

        from blueman.main.DhcpClient import DhcpClient

        def dh_error(dh, message):
            invocation.return_error(message)
            self.plugin.timer.resume()

        def dh_connected(dh, ip):
            invocation.return_value(ip)
            self.plugin.timer.resume()

        dh = DhcpClient(net_interface)
        dh.connect("error-occurred", dh_error)
        dh.connect("connected", dh_connected)
        try:
            dh.run()
        except Exception as e:
            invocation.return_error(e)

    @dbus_method(DBUS_INTERFACE, in_signature="sss", out_signature="", sender_keyword="caller")
    def EnableNetwork(self, ip_address, netmask, dhcp_handler, caller):
        self.plugin.confirm_authorization(caller, "org.blueman.network.setup")
        nc = NetConf.get_default()
        nc.set_ipv4(ip_address, netmask)
        nc.set_dhcp_handler(DHCPDHANDLERS[dhcp_handler])
        nc.apply_settings()

    @dbus_method(DBUS_INTERFACE, in_signature="", out_signature="", sender_keyword="caller")
    def ReloadNetwork(self, caller):
        nc = NetConf.get_default()
        if nc.ip4_address is None or nc.ip4_mask is None:
            nc.ip4_changed = False
            nc.store()
            return

        self.plugin.confirm_authorization(caller, "org.blueman.network.setup")
        nc.apply_settings()

    @dbus_method(DBUS_INTERFACE, in_signature="", out_signature="", sender_keyword="caller")
    def DisableNetwork(self, caller):
        self.plugin.confirm_authorization(caller, "org.blueman.network.setup")
        nc = NetConf.get_default()
        nc.remove_settings()
        nc.set_ipv4(None, None)
        nc.store()


class Network(MechanismPlugin):
    dbus_service = None

    def on_load(self):
        connection = Gio.bus_get_sync(Gio.BusType.SYSTEM)
        self.dbus_service = MechanismNetworkService(self, connection=connection)
        self.dbus_service.connect_bus()
