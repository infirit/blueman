from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

from gi.repository import Gio
from blueman.bluez.Base import Base as BlueZBase


class Base(BlueZBase):
    __bus = Gio.bus_get_sync(Gio.BusType.SESSION)
    __bus_name = 'org.bluez.obex'
