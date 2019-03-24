# coding=utf-8
import logging
from blueman.bluez.Network import AnyNetwork
from blueman.gui.Notification import Notification
from blueman.main.DbusService import *
from blueman.plugins.AppletPlugin import AppletPlugin
from blueman.main.DBusProxies import Mechanism
from gi.repository import Gio


DBUS_INTERFACE = 'org.blueman.Applet.DhcpClient'


class AppletDhcpClientService(DbusService):
    def __init__(self, plugin, **kwargs):
        super().__init__(path='/org/blueman/Applet', **kwargs)
        self.plugin = plugin

    @dbus_method(interface=DBUS_INTERFACE, in_signature='s')
    def DhcpClient(self, interface):
        self.plugin.dhcp_acquire(interface)


class DhcpClient(AppletPlugin):
    __description__ = _("Provides a basic dhcp client for Bluetooth PAN connections.")
    __icon__ = "network-workgroup"
    __author__ = "Walmis"

    _any_network = None
    _connection = None
    _dbus_service = None

    def on_load(self):
        self._any_network = AnyNetwork()
        self._any_network.connect_signal('property-changed', self._on_network_prop_changed)

        self.quering = []

        self._connection = Gio.bus_get_sync(Gio.BusType.SESSION)
        self._dbus_service = AppletDhcpClientService(self, connection=self._connection)
        self._dbus_service.connect_bus()

    def on_unload(self):
        self._any_network.disconnect_by_func(self._on_network_prop_changed)
        self._any_network = None
        self._dbus_service.disconnect_bus()
        self._dbus_service = None

    def _on_network_prop_changed(self, _network, key, value, _path):
        if key == "Interface":
            if value != "":
                self.dhcp_acquire(value)

    def dhcp_acquire(self, device):
        if device not in self.quering:
            self.quering.append(device)
        else:
            return

        if device != "":
            def reply(_obj, result, _user_data):
                logging.info(result)
                Notification(_("Bluetooth Network"),
                             _("Interface %(0)s bound to IP address %(1)s") % {"0": device, "1": result},
                             icon_name="network-workgroup").show()

                self.quering.remove(device)

            def err(_obj, result, _user_data):
                logging.warning(result)
                Notification(_("Bluetooth Network"), _("Failed to obtain an IP address on %s") % device,
                             icon_name="network-workgroup").show()

                self.quering.remove(device)

            Notification(_("Bluetooth Network"), _("Trying to obtain an IP address on %s\nPlease wait…" % device),
                         icon_name="network-workgroup").show()

            m = Mechanism(interface_name='org.blueman.Mechanism.Network')
            m.DhcpClient('(s)', device, result_handler=reply, error_handler=err, timeout=120)
