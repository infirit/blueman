from importlib import import_module

import logging

from blueman.Functions import check_single_instance
from blueman.main.AppletService import AppletService

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio


class BluemanTray(object):
    def __init__(self):
        check_single_instance("blueman-tray")

        logging.basicConfig(level=logging.INFO)

        applet = AppletService()

        Gio.bus_watch_name(Gio.BusType.SESSION, 'org.blueman.Applet', Gio.BusNameWatcherFlags.NONE, None, Gtk.main_quit)

        indicator_name = applet.GetStatusIconImplementation()
        indicator_name = 'GtkStatusIcon'
        logging.info('Using indicator "%s"' % indicator_name)
        indicator_class = getattr(import_module('blueman.main.indicators.' + indicator_name), indicator_name)
        self.indicator = indicator_class(applet.GetIconName())

        applet.connect('g-signal', self.on_signal)

        self.indicator.set_text(applet.GetText())
        self.indicator.set_visibility(applet.GetVisibility())
        self.indicator.set_menu(applet.GetMenu(), self._activate_menu_item)

        # TODO: Replace with GLib main loop
        Gtk.main()

    def _activate_menu_item(self, *indexes):
        return AppletService().ActivateMenuItem('(ai)', indexes)

    def on_signal(self, _applet, sender_name, signal_name, args):
        if signal_name == 'IconNameChanged':
            self.indicator.set_icon(*args)
        elif signal_name == 'TextChanged':
            self.indicator.set_text(*args)
        elif signal_name == 'VisibilityChanged':
            self.indicator.set_visibility(*args)
        elif signal_name == 'MenuChanged':
            self.indicator.set_menu(*args, self._activate_menu_item)
