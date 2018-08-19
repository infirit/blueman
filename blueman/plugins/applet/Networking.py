# coding=utf-8
from blueman.main.Config import Config
from blueman.bluez.NetworkServer import NetworkServer
from blueman.main.DBusProxies import Mechanism

from blueman.plugins.AppletPlugin import AppletPlugin
from blueman.gui.CommonUi import ErrorDialog
from gi.repository import GLib
import logging


class Networking(AppletPlugin):
    __icon__ = "network"
    __description__ = _("Manages local network services, like NAP bridges")
    __author__ = "Walmis"

    Config = None
    _mechanism = None
    _registered = {}

    def on_load(self):
        self._registered = {}

        self.Config = Config("org.blueman.network")
        self.Config.connect("changed", self.on_config_changed)
        self._mechanism = Mechanism()

        self.load_nap_settings()

    def on_unload(self):
        for adapter_path in self._registered:
            s = NetworkServer(self._registered.pop(adapter_path))
            s.unregister("nap")

        self.Config.disconnect_by_func(self.on_config_changed)
        self.Config = None
        self._mechanism = None

    def on_manager_state_changed(self, state):
        if state:
            self.update_status()

    def reload_network(self):
        def reply(*_):
            pass

        def err(_obj, result, _user_data):
            self.show_error_dialog(result)

        self._mechanism.ReloadNetwork(result_handler=reply, error_handler=err)

    def enable_network(self):
        try:
            self._mechanism.EnableNetwork('(sss)', self.Config['ipaddress'], '255.255.255.0',
                                          self.Config['dhcphandler'])
        except GLib.Error as e:
            # It will error on applet startup anyway so lets make sure to disable
            self.disable_network()
            self.show_error_dialog(e)

    def disable_network(self):
        try:
            self._mechanism.DisableNetwork()
        except GLib.Error as e:
            self.show_error_dialog(e)

    def on_adapter_added(self, path):
        self.update_status()

    def update_status(self):
        self.set_nap(self.Config["nap-enable"])

    def load_nap_settings(self):
        logging.info("Loading NAP settings")

        self.reload_network()

    def on_config_changed(self, config, key):
        if key in ('nap-enable', 'ipaddress', 'dhcphandler'):
            self.set_nap(config['nap-enable'])

    def show_error_dialog(self, excp):
        def run_dialog(dialog):
            dialog.run()
            dialog.destroy()

        d = ErrorDialog('<b>Failed to apply network settings</b>',
                        'You might not be able to connect to the Bluetooth network via this machine',
                        excp, margin_left=9)
        GLib.idle_add(run_dialog, d)

    def set_nap(self, enable):
        logging.info("set nap %s" % enable)
        if self.parent.manager_state:
            adapters = self.parent.Manager.get_adapters()
            for adapter in adapters:
                object_path = adapter.get_object_path()

                registered = self._registered.setdefault(object_path, False)

                s = NetworkServer(object_path)
                if enable and not registered:
                    s.register("nap", "pan1")
                    self._registered[object_path] = True
                elif not enable and registered:
                    s.unregister("nap")
                    self._registered[object_path] = False

            if enable:
                self.enable_network()
            else:
                self.disable_network()
