# coding=utf-8
from blueman.bluez.AnyBase import AnyBase


class AnyNetwork(AnyBase):
    def __init__(self) -> None:
        super().__init__('org.bluez.Network1')
