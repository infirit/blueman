# coding=utf-8
from typing import Optional, Callable

from blueman.Service import Service
from blueman.bluez import Device, BluezDBusException


class NetworkService(Service):
    def __init__(self, device: Device, uuid: str):
        super().__init__(device, uuid)

    @property
    def available(self) -> bool:
        # This interface is only available after pairing
        paired: bool = self.device["Paired"]
        return paired

    @property
    def connected(self) -> bool:
        if not self.available:
            return False

        return self.device.network_connected

    def connect(
        self,
        reply_handler: Optional[Callable[[str], None]] = None,
        error_handler: Optional[Callable[[BluezDBusException], None]] = None,
    ) -> None:
        self.device.connect_server(self.uuid, reply_handler=reply_handler, error_handler=error_handler)

    def disconnect(
        self,
        reply_handler: Optional[Callable[[], None]] = None,
        error_handler: Optional[Callable[[BluezDBusException], None]] = None,
    ) -> None:
        self.device.disconnect_server(reply_handler=reply_handler, error_handler=error_handler)
