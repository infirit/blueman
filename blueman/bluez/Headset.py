from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

from gi.repository import GObject
from blueman.bluez.PropertiesBase import PropertiesBase


class Headset(PropertiesBase):
    __gsignals__ = {str('answer-requested'): (GObject.SignalFlags.NO_HOOKS, None, ())}

    def __init__(self, obj_path=None):
        super(Headset, self).__init__('org.bluez.Headset1', obj_path)

        sig = self.__dbus_proxy.connect("g-signal", self._on_signal_recieved)
        self.__signals.append(sig)

    def _on_signal_recieved(self, proxy, sender_name, signal_name, param):
        if signal_name == 'AnswerRequested':
            self.emit('answer-requested')
