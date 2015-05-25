from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

from blueman.bluez.PropertiesBase import PropertiesBase


class Device(PropertiesBase):
    def __init__(self, obj_path=None):
        super(Device, self).__init__('org.bluez.Device1', obj_path)

    def pair(self, reply_handler=None, error_handler=None):
        def ok():
            if callable(reply_handler):
                reply_handler()

        def err(e):
            if callable(error_handler):
                error_handler(e)
            else:
                raise e

        self._call('Pair', reply_handler=ok, error_handler=err)

    def connect(self, reply_handler=None, error_handler=None):
        def ok():
            if callable(reply_handler):
                reply_handler()

        def err(e):
            if callable(error_handler):
                error_handler(e)
            else:
                raise e

        self._call('Connect', reply_handler=ok, error_handler=err)

    def disconnect(self, reply_handler=None, error_handler=None):
        def ok():
            if callable(reply_handler):
                reply_handler()

        def err(e):
            if callable(error_handler):
                error_handler(e)
            else:
                raise e

        self._call('Disconnect', reply_handler=ok, error_handler=err)
