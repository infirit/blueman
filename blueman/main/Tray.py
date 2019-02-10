from importlib import import_module
import logging

from blueman.Functions import check_single_instance
from blueman.main.DBusProxies import AppletService

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio


class BluemanTray(object):
    def __init__(self):
        check_single_instance("blueman-tray")

        main_loop = GLib.MainLoop()

        Gio.bus_watch_name(Gio.BusType.SESSION, 'org.blueman.Applet',
                           Gio.BusNameWatcherFlags.NONE, None, lambda _connection, _name: main_loop.quit())

        statusicon = AppletService(interface_name='org.blueman.Applet.StatusIcon')
        menu = AppletService(interface_name='org.blueman.Applet.Menu')
        indicator_name = statusicon.GetStatusIconImplementation()
        logging.info('Using indicator "%s"' % indicator_name)
        indicator_class = getattr(import_module('blueman.main.indicators.' + indicator_name), indicator_name)
        self.indicator = indicator_class(statusicon.GetIconName(), self._activate_menu_item, self._activate_status_icon)

        statusicon.connect('g-signal', self.on_signal)
        menu.connect('g-signal', self.on_signal)

        self.indicator.set_text(statusicon.GetText())
        self.indicator.set_visibility(statusicon.GetVisibility())
        self.indicator.set_menu(menu.GetMenu())

        main_loop.run()

    def _activate_menu_item(self, *indexes):
        return AppletService(interface_name='org.blueman.Applet.Menu').ActivateMenuItem('(ai)', indexes)

    def _activate_status_icon(self):
        return AppletService(interface_name='org.blueman.Applet.StatusIcon').Activate()

    def on_signal(self, _applet, sender_name, signal_name, args):
        print('***', signal_name, args)
        if signal_name == 'IconNameChanged':
            self.indicator.set_icon(*args)
        elif signal_name == 'TextChanged':
            self.indicator.set_text(*args)
        elif signal_name == 'VisibilityChanged':
            self.indicator.set_visibility(*args)
        elif signal_name == 'MenuChanged':
            self.indicator.set_menu(*args)
