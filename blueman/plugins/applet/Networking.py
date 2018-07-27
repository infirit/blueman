# coding=utf-8
from blueman.main.Config import Config
from blueman.bluez.NetworkServer import NetworkServer
from blueman.main.DBusProxies import Mechanism

from blueman.plugins.AppletPlugin import AppletPlugin
from blueman.gui.CommonUi import ErrorDialog
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

    def load_nap_settings(self):
        logging.info("Loading NAP settings")

        def reply(*_):
            pass

        def err(_obj, result, _user_data):
            d = ErrorDialog("<b>Failed to apply network settings</b>",
                            "You might not be able to connect to the Bluetooth network via this machine",
                            result,
                            margin_left=9)

            d.run()
            d.destroy()

        self._mechanism.ReloadNetwork(result_handler=reply, error_handler=err)

    def on_adapter_added(self, path):
        self.update_status()

    def update_status(self):
        self.set_nap(self.Config["nap-enable"])

    def on_config_changed(self, config, key):
        if key == "nap-enable":
            self.set_nap(config[key])

    def set_nap(self, on):
        logging.info("set nap %s" % on)
        if self.parent.manager_state:
            adapters = self.parent.Manager.get_adapters()
            for adapter in adapters:
                object_path = adapter.get_object_path()

                registered = self._registered.setdefault(object_path, False)

                s = NetworkServer(object_path)
                if on and not registered:
                    s.register("nap", "pan1")
                    self._registered[object_path] = True
                elif not on and registered:
                    s.unregister("nap")
                    self._registered[object_path] = False
