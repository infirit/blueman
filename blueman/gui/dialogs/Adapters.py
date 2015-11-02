#!/usr/bin/env python

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

from locale import bind_textdomain_codeset
import dbus
from dbus.mainloop.glib import DBusGMainLoop
import os.path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import Pango

import blueman.bluez as Bluez
from blueman.Constants import *
from blueman.Functions import *

DBusGMainLoop(set_as_default=True)

class BluemanAdapters(Gtk.Dialog):
    def __init__(self, selected_hci_dev, parent=None):
        Gtk.Dialog.__init__(self, title=_("Bluetooth Adapters"), parent=parent)
        # Setup dialog
        self.set_border_width(5)
        self.set_resizable(False)
        self.props.icon_name = "blueman-device"
        self.props.window_position = Gtk.WindowPosition.CENTER
        self.set_name("BluemanAdapters")
        self.connect("response", self.on_dialog_response)

        close_button = self.add_button("_Close", Gtk.ResponseType.CLOSE)
        close_button.props.receives_default = True
        close_button.props.use_underline = True

        self.content_area = self.get_content_area()
        self.notebook = Gtk.Notebook()
        self.content_area.add(self.notebook)
        self.tabs = {}

        setup_icon_path()
        self.bus = dbus.SystemBus()
        self.bus.watch_name_owner('org.bluez', self.on_dbus_name_owner_change)

        check_single_instance("blueman-adapters", lambda time: self.present_with_time(time))

        check_bluetooth_status(_("Bluetooth needs to be turned on for the adapter manager to work"), lambda: exit())

        try:
            self.manager = Bluez.Manager()
            self.manager.connect_signal('adapter-added', self.on_adapter_added)
            self.manager.connect_signal('adapter-removed', self.on_adapter_removed)
            adapters = self.manager.list_adapters()
            for adapter in adapters:
                self.add_to_notebook(adapter)
        except Exception as e:
            print(e)
            self.manager = None
        #fixme: show error dialog and exit

        #activate a particular tab according to command line option
        if selected_hci_dev is not None:
            if selected_hci_dev in self.tabs:
                hci_dev_num = int(selected_hci_dev[3:])
                self.notebook.set_current_page(hci_dev_num)
            else:
                print('Error: the selected adapter does not exist')
        self.show_all()

    def on_dialog_response(self, dialog, response_id):
        for hci, settings in self.tabs.items():
            if settings['changed']:
                settings['adapter'].set_name(settings['name'])
        Gtk.main_quit()

    def on_property_changed(self, adapter, name, value, path):
        if name == "Discoverable" and value == 0:
            hci_dev = os.path.basename(path)
            self.tabs[hci_dev]["hidden_radio"].set_active(True)

    def on_adapter_added(self, _manager, adapter_path):
        adapter = Bluez.Adapter(adapter_path)
        self.add_to_notebook(adapter)

    def on_adapter_removed(self, _manager, adapter_path):
        hci_dev = os.path.basename(adapter_path)
        adapter = self.tabs[hci_dev]["adapter"]
        self.remove_from_notebook(adapter)

    def on_dbus_name_owner_change(self, owner):
        print('org.bluez owner changed to '+owner)
        if owner == '':
            self.manager = None
        #fixme: show error dialog and exit

    def build_adapter_tab(self, adapter):
        adapter_settings = {}

        def on_hidden_toggle(radio):
            if not radio.props.active:
                return
            adapter.set('DiscoverableTimeout', 0)
            adapter_settings['discoverable'] = False
            adapter.set('Discoverable', False)
            hscale.set_sensitive(False)

        def on_always_toggle(radio):
            if not radio.props.active:
                return
            adapter.set('DiscoverableTimeout', 0)
            adapter_settings['discoverable'] = True
            adapter.set('Discoverable', True)
            hscale.set_sensitive(False)

        def on_temporary_toggle(radio):
            if not radio.props.active:
                return
            adapter_settings['discoverable'] = True
            adapter.set('Discoverable', True)
            hscale.set_sensitive(True)
            hscale.set_value(3)

        def on_scale_format_value(scale, value):
            if value == 0:
                if adapter_settings['discoverable']:
                    return _("Always")
                else:
                    return _("Hidden")
            else:
                return gettext.ngettext("%d Minute", "%d Minutes", value) % (value)

        def on_scale_value_changed(scale):
            val = scale.get_value()
            print('value: '+str(val))
            if val == 0 and adapter_settings['discoverable']:
                always_radio.props.active = True
            timeout = int(val * 60)
            adapter.set('DiscoverableTimeout', timeout)

        def on_name_changed(entry):
            adapter_settings['name'] = entry.get_text()
            adapter_settings['changed'] = True

        props = adapter.get_properties()
        adapter_settings['adapter'] = adapter
        adapter_settings['adapter'].connect_signal('property-changed', self.on_property_changed)
        adapter_settings['address'] = props['Address']
        adapter_settings['name'] = adapter.get_name()
        adapter_settings['discoverable'] = props['Discoverable']
        #we use count timeout in minutes
        adapter_settings['discoverable_timeout'] = props['DiscoverableTimeout'] / 60
        adapter_settings['changed'] = False

        builder = Gtk.Builder()
        builder.set_translation_domain("blueman")
        builder.add_from_file(UI_PATH + "/adapters-tab.ui")
        adapter_settings['grid'] = builder.get_object("grid")

        hscale = builder.get_object("hscale")
        hscale.connect("format-value", on_scale_format_value)
        hscale.connect("value-changed", on_scale_value_changed)
        hscale.set_range(0, 30)
        hscale.set_increments(1, 1)

        hidden_radio = builder.get_object("hidden")
        always_radio = builder.get_object("always")
        temporary_radio = builder.get_object("temporary")

        if adapter_settings['discoverable'] and adapter_settings['discoverable_timeout'] > 0:
            temporary_radio.set_active(True)
            hscale.set_value(adapter_settings['discoverable_timeout'])
            hscale.set_sensitive(True)
        elif adapter_settings['discoverable'] and adapter_settings['discoverable_timeout'] == 0:
            always_radio.set_active(True)
        else:
            hidden_radio.set_active(True)

        name_entry = builder.get_object("name_entry")
        name_entry.set_text(adapter_settings['name'])

        hidden_radio.connect("toggled", on_hidden_toggle)
        always_radio.connect("toggled", on_always_toggle)
        temporary_radio.connect("toggled", on_temporary_toggle)
        name_entry.connect("changed", on_name_changed)

        adapter_settings["hidden_radio"] = hidden_radio
        adapter_settings["always_radio"] = always_radio
        adapter_settings["temparary_radio"] = temporary_radio
        return adapter_settings

    def add_to_notebook(self, adapter):
        hci_dev = os.path.basename(adapter.get_object_path())
        hci_dev_num = int(hci_dev[3:])

        if not hci_dev in self.tabs:
            self.tabs[hci_dev] = self.build_adapter_tab(adapter)
        else:
            if self.tabs[hci_dev]['visible']:
                return
            #might need to update settings at this point
        settings = self.tabs[hci_dev]
        settings['visible'] = True
        name = settings['name']
        if name == '':
            name = _('Adapter') + ' %d' % (hci_dev_num + 1)
        label = Gtk.Label(label=name)
        label.set_max_width_chars(20)
        label.props.hexpand = True
        label.set_ellipsize(Pango.EllipsizeMode.END)
        self.notebook.insert_page(settings['grid'], label, hci_dev_num)

    def remove_from_notebook(self, adapter):
        hci_dev = os.path.basename(adapter.get_object_path())
        hci_dev_num = int(hci_dev[3:])

        self.tabs[hci_dev]['visible'] = False
        self.notebook.remove_page(hci_dev_num)

    #leave actual tab contents intact in case adapter becomes present once again
