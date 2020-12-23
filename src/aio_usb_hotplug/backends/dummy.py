"""PyUSB-based backend for aio_usb_hotplug."""

from anyio import sleep
from typing import List

from .base import Device, USBBusScannerBackend


class DummyUSBBusScannerBackend(USBBusScannerBackend):
    """Dummy USB bus scanner that never detects anything. Used as a fallback when
    no suitable backend exists for the current platform.
    """

    def is_supported(self) -> bool:
        """Returns whether the backend is supported on the current platform."""
        return True

    def key_of(self, device: Device) -> str:
        return str(id(device))

    async def scan(self) -> List[Device]:
        return []

    async def wait_until_next_scan(self) -> None:
        await sleep(100000)
