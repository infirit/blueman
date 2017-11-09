# coding=utf-8
from gettext import gettext as _
import os.path
import logging
import gettext
from typing import Dict, Tuple, Optional

from blueman.Functions import *
from blueman.bluez.Manager import Manager
from blueman.bluez.Adapter import Adapter

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk
from gi.repository import Pango


class AdapterGrid(Gtk.Grid):
    def __init__(self, adapter, **kwargs):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            row_spacing=2,
            margin=12,
            visible=True,
            **kwargs
        )

        # Maps names to position in grid, used in self.get_child_widget
        self.widget_map: Dict[str, Tuple[int, int]] = {}

        self.adapter = adapter

        visibility_label = Gtk.Label(label=_("<b>Visibility Setting</b>"), use_markup=True, visible=True,
                                     halign=Gtk.Align.START)
        self.add(visibility_label)
        self.widget_map["visibility_label"] = (0, 0)

        radio_hidden = Gtk.RadioButton(label=_("Hidden"), draw_indicator=True, visible=True, halign=Gtk.Align.START,
                                       can_focus=True)
        self.add(radio_hidden)
        self.widget_map["radio_hidden"] = (1, 0)
        radio_always = Gtk.RadioButton(label=_("Always visible"), group=radio_hidden, draw_indicator=True, visible=True,
                                       halign=Gtk.Align.START, can_focus=True)
        self.add(radio_always)
        self.widget_map["radio_always"] = (2, 0)
        radio_temporary = Gtk.RadioButton(label=_("Temporary visible"), group=radio_hidden, draw_indicator=True,
                                          visible=True, halign=Gtk.Align.START, can_focus=True)
        self.add(radio_temporary)
        self.widget_map["radio_temporary"] = (3, 0)

        hscale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, value_pos=Gtk.PositionType.BOTTOM, digits=0,
                           sensitive=False, visible=True)
        hscale.set_range(0, 30)
        hscale.set_increments(1, 1)
        self.add(hscale)
        self.widget_map["hscale"] = (4, 0)

        friendly_label = Gtk.Label(label=_("<b>Friendly Name</b>"), use_markup=True, visible=True,
                                   halign=Gtk.Align.START)
        self.add(friendly_label)
        self.widget_map["friendly_label"] = (5, 0)

        name_entry = Gtk.Entry(max_length=248, can_focus=True, visible=True, width_request=280)
        self.add(name_entry)
        self.widget_map["name_entry"] = (6, 0)

        if adapter['Discoverable'] and adapter['DiscoverableTimeout'] > 0:
            radio_temporary.set_active(True)
            hscale.set_value(adapter['DiscoverableTimeout'])
            hscale.set_sensitive(True)
        elif adapter['Discoverable'] and adapter['DiscoverableTimeout'] == 0:
            radio_always.set_active(True)
        else:
            radio_hidden.set_active(True)

        name_entry.set_text(adapter.get_name())

        hscale.connect("format-value", self._on_scale_format_value)
        hscale.connect("value-changed", self._on_scale_value_changed)
        radio_hidden.connect("toggled", self._on_radio_toggle, "hidden")
        radio_always.connect("toggled", self._on_radio_toggle, "always")
        radio_temporary.connect("toggled", self._on_radio_toggle, "temporary")
        name_entry.connect("changed", self._on_name_changed)

    def get_child_widget(self, name):
        top, left = self.widget_map[name]
        return self.get_child_at(left, top)

    def set_visibility(self, state):
        if state == "hidden":
            hidden = self.get_child_widget("radio_hidden")
            hidden.set_active(True)
        elif state == "always":
            always = self.get_child_widget("radio_always")
            always.set_active(True)
        elif state == "temporary":
            temporary = self.get_child_widget("radio_temporary")
            temporary.set_active(True)

    def set_alias_entry(self, text):
        friendly = self.get_child_widget("friendly_label")
        friendly.set_text(text)

        entry = self.get_child_widget("name_entry")
        entry.set_text(text)

    def _on_radio_toggle(self, radio, name):
        if not radio.props.active:
            return

        hscale = self.get_child_widget("hscale")
        if name == "hidden":
            self.adapter['DiscoverableTimeout'] = 0
            self.adapter['Discoverable'] = False
            hscale.set_sensitive(False)
        elif name == "always":
            self.adapter['DiscoverableTimeout'] = 0
            self.adapter['Discoverable'] = True
            hscale.set_sensitive(False)
        elif name == "temporary":
            self.adapter['Discoverable'] = True
            hscale.set_sensitive(True)
            hscale.set_value(3)

    def _on_scale_format_value(self, scale, value):
        # FIXME inconsistant or not working at all
        if value == 0:
            if self.adapter['Discoverable']:
                return _("Always")
            else:
                return _("Hidden")
        else:
            return gettext.ngettext("%d Minute", "%d Minutes", value) % value

    def _on_scale_value_changed(self, scale):
        val = scale.get_value()
        logging.info('value: %s' % val)
        if val == 0 and self.adapter['Discoverable']:
            self.get_child_widget("radio_always").props.active = True
        timeout = int(val * 60)
        self.adapter['DiscoverableTimeout'] = timeout

    def _on_name_changed(self, entry):
        self.adapter['Alias'] = entry.get_text()


class BluemanAdaptersWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(
            application=app,
            title=_("Bluetooth Adapters"),
            border_width=5,
            resizable=False,
            icon_name="blueman-device",
            name="BluemanAdapters"
        )


class BluemanAdapters(Gtk.Application):
    def __init__(self, selected_hci_dev, socket_id):
        super().__init__(application_id="org.blueman.Adapters")

        self.socket_id = socket_id
        self.selected_hci_dev = selected_hci_dev

        self.notebook = Gtk.Notebook(visible=True)

        self.window = None

        self.tabs: Dict[str, Dict[str, AdapterGrid]] = {}
        self._adapters: Dict[str, Adapter] = {}

        setup_icon_path()
        Manager.watch_name_owner(self._on_dbus_name_appeared, self._on_dbus_name_vanished)
        self.manager: Optional[Manager] = Manager()

        check_bluetooth_status(_("Bluetooth needs to be turned on for the adapter manager to work"), lambda: exit())

        adapters = self.manager.get_adapters()
        if not adapters:
            logging.error('No adapter(s) found')
            exit(1)

        self.manager.connect_signal('adapter-added', self.on_adapter_added)
        self.manager.connect_signal('adapter-removed', self.on_adapter_removed)

        for adapter in adapters:
            path = adapter.get_object_path()
            self.on_adapter_added(self.manager, path)

        # activate a particular tab according to command line option
        if selected_hci_dev is not None:
            if selected_hci_dev in self.tabs:
                hci_dev_num = int(selected_hci_dev[3:])
                self.notebook.set_current_page(hci_dev_num)
            else:
                logging.error('Error: the selected adapter does not exist')

    def do_activate(self):
        def app_release(plug, event):
            self.release()

        if self.socket_id:
            self.hold()
            plug = Gtk.Plug.new(self.socket_id)
            plug.show()
            plug.connect('delete-event', app_release)
            plug.add(self.notebook)
        else:
            if not self.window:
                self.window = BluemanAdaptersWindow(app=self)
                self.window.add(self.notebook)
            self.window.present_with_time(Gtk.get_current_event_time())

    def on_property_changed(self, adapter, name, value, path):
        hci_dev = os.path.basename(path)
        if name == "Discoverable" and value:
            if adapter["DiscoverableTimeout"] == 0:
                self.tabs[hci_dev]["grid"].set_visibility("always")
            else:
                self.tabs[hci_dev]["grid"].set_visibility("temporary")
        elif name == "Discoverable" and not value:
            self.tabs[hci_dev]["grid"].set_visibility("hidden")
        elif name == "Alias":
            self.tabs[hci_dev]["grid"].set_alias_entry(value)

    def on_adapter_added(self, _manager, adapter_path):
        hci_dev = os.path.basename(adapter_path)
        if hci_dev not in self._adapters:
            self._adapters[hci_dev] = Adapter(adapter_path)

        self._adapters[hci_dev].connect_signal("property-changed", self.on_property_changed)
        self.add_to_notebook(self._adapters[hci_dev])

    def on_adapter_removed(self, _manager, adapter_path):
        hci_dev = os.path.basename(adapter_path)
        self.remove_from_notebook(self._adapters[hci_dev])

    def _on_dbus_name_appeared(self, _connection, name, owner):
        logging.info("%s %s" % (name, owner))

    def _on_dbus_name_vanished(self, _connection, name):
        logging.info(name)
        # FIXME: show error dialog and exit

    def add_to_notebook(self, adapter):
        hci_dev = os.path.basename(adapter.get_object_path())
        hci_dev_num = int(hci_dev[3:])

        if hci_dev not in self.tabs:
            self.tabs[hci_dev] = {"grid": AdapterGrid(adapter)}

        name = adapter.get_name()
        if name == '':
            name = _('Adapter') + ' %d' % (hci_dev_num + 1)
        label = Gtk.Label(label=name, max_width_chars=20, hexpand=True, ellipsize=Pango.EllipsizeMode.END)
        self.tabs[hci_dev]['label'] = label

        self.notebook.insert_page(self.tabs[hci_dev]['grid'], label, hci_dev_num)

    def remove_from_notebook(self, adapter):
        hci_dev = os.path.basename(adapter.get_object_path())
        hci_dev_num = int(hci_dev[3:])

        self.notebook.remove_page(hci_dev_num)
