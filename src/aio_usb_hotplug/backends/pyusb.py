"""PyUSB-based backend for aio_usb_hotplug."""

import usb.core

from anyio import (
    create_queue,
    move_on_after,
    run_async_from_thread,
    run_in_thread,
    sleep,
)
from typing import Any, Dict, List

from .base import Device, USBBusScannerBackend


class PyUSBBusScannerBackend(USBBusScannerBackend):
    """PyUSB-based USB bus scanner implementation."""

    def __init__(self):
        """Constructor."""
        self._params = {}

        try:
            import pyudev

            self._pyudev = pyudev
        except ImportError:
            self._pyudev = None

    def configure(self, configuration: Dict[str, Any]) -> None:
        self._params = configuration

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
        return await run_in_thread(self._find_devices)

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
        return list(usb.core.find(find_all=True, **self._params))

    async def _wait_for_next_pyudev_hotplug_event(self):
        """Coroutine that waits for the next hotplug event on the USB bus using
        pyudev.
        """
        pyudev = self._pyudev
        monitor = pyudev.Monitor.from_netlink(pyudev.Context())
        monitor.filter_by(subsystem="usb")

        queue = create_queue()

        def _on_event(device):
            run_async_from_thread(queue.put, "notify")

        observer = pyudev.MonitorObserver(monitor, callback=_on_event)
        observer.start()

        # Wait for the first event
        await queue.get()

        # Wait for subsequent events arriving close to each other so we don't
        # trigger multiple scans until the USB bus settles down.
        while True:
            async with move_on_after(0.5):
                await queue.get()
