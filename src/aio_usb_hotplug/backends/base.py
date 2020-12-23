"""Interface specification for USB bus scanner backends."""

from abc import abstractmethod, ABCMeta
from typing import Any, Dict, List

__all__ = ("Device", "USBBusScannerBackend")

Device = Any


class USBBusScannerBackend(metaclass=ABCMeta):
    """Interface specification for USB bus scanner backends."""

    def configure(self, configuration: Dict[str, Any]) -> None:
        """Configures the scanner backend and specifies which devices the
        backend should report.

        The format of the configuration dictionary depends on the backend.
        The default implementation does nothing.

        It is guaranteed that no one else holds a reference to the configuration
        dictionary so it is safe to just store it as-is (without making a
        copy first).
        """
        pass  # pragma: no cover

    def is_supported(self) -> bool:
        """Returns whether the backend is supported on the current platform."""
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def key_of(self, device: Device) -> str:
        """Returns a unique key for a USB device that can be used for identity
        comparisons. The keys should take into account at least the bus ID, the
        address, the vendor ID and the product ID of the device.

        The string does not have to be human-readable, but it must be unique
        for each connected USB device.
        """
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    async def scan(self) -> List[Device]:
        """Scans the system for USB devices and returns the list of devices
        found.

        This is an async function that will be executed in the main event loop.
        If the backend blocks while scanning, you must delegate to a worker
        thread from this method.
        """
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    async def wait_until_next_scan(self) -> None:
        """Async function that blocks until the next scan is due.

        It is up to the backend to decide whether it scans the bus regularly
        or whether it uses some underlying mechanism of the OS to detect
        hotplug events.
        """
        raise NotImplementedError  # pragma: no cover
