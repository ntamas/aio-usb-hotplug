"""PyUSB-based backend for aio_usb_hotplug."""

from anyio import sleep, to_thread
from typing import Any, Dict, List

from .base import Device, USBBusScannerBackend


class PyUSBBusScannerBackend(USBBusScannerBackend):
    """PyUSB-based USB bus scanner implementation."""

    def __init__(self):
        """Constructor."""
        self._params = {}

        try:
            import usb.core

            self._usb_core = usb.core
        except ImportError:
            self._usb_core = None

        try:
            import pyudev

            self._pyudev = pyudev
        except ImportError:
            self._pyudev = None

    def configure(self, configuration: Dict[str, Any]) -> None:
        self._params = configuration

    def is_supported(self) -> bool:
        """Returns whether the backend is supported on the current platform."""
        if self._usb_core is None:
            return False

        # _pyudev is optional so we don't check that

        # This section is copied from the find() function of pyusb
        import usb.backend.libusb1 as libusb1
        import usb.backend.libusb0 as libusb0
        import usb.backend.openusb as openusb

        for m in (libusb1, openusb, libusb0):
            backend = m.get_backend()
            if backend is not None:
                return True

        return False

    def key_of(self, device: Device) -> str:
        """Returns a unique key for a USB device that can be used for identity
        comparisons. The keys take into account the bus ID, the address, the
        vendor ID and the product ID of the device.

        Note that we don't use the serial number, and there's a reason for that.
        Apparently, some USB devices do not like it when we query the serial
        number once a second, and freeze randomly.
        """
        key = "{0.idVendor:04X}:{0.idProduct:04X}".format(device)

        if device.bus is not None and device.address is not None:
            key = "{0} at bus {1.bus}, address {1.address}".format(key, device)

        return key

    async def scan(self) -> List[Device]:
        return await to_thread.run_sync(self._find_devices, cancellable=True)

    async def wait_until_next_scan(self) -> None:
        if self._pyudev:
            await self._wait_for_next_pyudev_hotplug_event()
        else:
            await sleep(1)

    def _find_devices(self) -> List[Device]:
        """Scans the USB bus for all the devices that we are interested in.

        This function may block; make sure to call it on an appropriate worker
        thread only and not on the main event loop.
        """
        return list(self._usb_core.find(find_all=True, **self._params))

    async def _wait_for_next_pyudev_hotplug_event(self):
        """Coroutine that waits for the next hotplug event on the USB bus using
        pyudev.
        """
        pyudev = self._pyudev

        monitor = pyudev.Monitor.from_netlink(pyudev.Context())
        monitor.filter_by(subsystem="usb")

        def _wait_in_worker_thread():
            # Wait for the first event
            event = monitor.poll()

            # Wait for subsequent events arriving close to each other so we don't
            # trigger multiple scans until the USB bus settles down.
            while event:
                event = monitor.poll(timeout=0.5)

        await to_thread.run_sync(_wait_in_worker_thread, cancellable=True)
