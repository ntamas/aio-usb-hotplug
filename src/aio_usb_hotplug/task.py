"""Hotplug detector for USB devices."""

from anyio import create_event
from async_generator import asynccontextmanager, async_generator, yield_
from collections import namedtuple
from enum import Enum
from typing import Callable, Dict, Iterator, Optional, Union

from .backends.base import USBBusScannerBackend
from .backends.autodetect import choose_backend


__all__ = ("HotplugDetector",)


def _to_int(value: Union[str, int]) -> int:
    """Converts a vendor or product ID, specified either in hexadecimal notation
    as a string, or in decimal notation as an integer, to its integer
    representation.

    Parameters:
        value: the value to convert

    Returns:
        the vendor or product ID as an integer
    """
    if isinstance(value, str):
        return int(value, 16)
    else:
        return int(value)


class HotplugEventType(Enum):
    """Enum representing the possible hotplug event types."""

    ADDED = "added"
    REMOVED = "removed"


HotplugEvent = namedtuple("HotplugEvent", "type device key")


class HotplugDetector:
    """Hotplug detector for USB devices.

    This class continuously scans the USB bus for devices that match a given
    set of USB attributes, and dispatches events when devices are discovered
    or removed.
    """

    @classmethod
    def for_device(cls, vid: Union[str, int], pid: Union[str, int], *args, **kwds):
        """Shortcut method to create a HotplugDetector_ for devices matching
        a single VID:PID combination.

        Parameters:
            vid: the vendor ID to match, in hexadecimal notation as a string,
                or as a single decimal number
            pid: the vendor ID to match, in hexadecimal notation as a string,
                or as a single decimal number

        Additional positional and keyword arguments are forwarded to the
        constructor.
        """
        vid, pid = _to_int(vid), _to_int(pid)
        return cls({"vid": vid, "pid": pid}, *args, **kwds)

    def __init__(
        self,
        params: Optional[Dict] = None,
        *,
        backend: Callable[[None], USBBusScannerBackend] = choose_backend
    ):
        """Constructor.

        Parameters:
            params: dictionary of keyword arguments to pass to the
                `configure()` method of the backend in order to specify what
                sort of devices we are interested in.
            backend: a callable that returns an instance of USBBusScannerBackend_
                when invoked with no arguments; defaults to autodetection
                depending on the current platform.
        """
        self._backend = backend

        self._params = self._preprocess_params(dict(params or {}))
        self._active = {}

        self._suspended = 0
        self._resume_event = None

    @async_generator
    async def events(self) -> Iterator[HotplugEvent]:
        """Runs the hotplug detection in an infinite loop, waiting between the
        given number of seconds between scans.

        Note that the actual detection is executed in a worker thread in order
        not to block the main event loop of the application. Signals are
        dispatched in the same thread that runs the event loop.

        Yields:
            HotplugEvent: event objects describing the devices that were added
                or removed
        """
        backend = self._backend() if callable(self._backend) else self._backend
        backend.configure(self._params)
        key_of = backend.key_of

        while True:
            if self._suspended:
                print("Waiting because we are suspended")
                await self._resume_event.wait()
                print("Released from suspend")

            devices = await backend.scan()

            added = {}
            seen = set()

            for index, device in enumerate(devices):
                key = key_of(device)
                if key in self._active:
                    seen.add(key)
                else:
                    added[key] = device

            to_remove = [key for key in self._active.keys() if key not in seen]
            removed = [self._active.pop(key) for key in to_remove]
            self._active.update(added)

            for device in removed:
                key = key_of(device)
                event = HotplugEvent(
                    type=HotplugEventType.REMOVED, device=device, key=key
                )
                await yield_(event)

            for device in added.values():
                key = key_of(device)
                event = HotplugEvent(
                    type=HotplugEventType.ADDED, device=device, key=key
                )
                await yield_(event)

            await backend.wait_until_next_scan()

    async def resume(self) -> None:
        """Resumes the hotplug detector task after a suspension."""
        self._suspended -= 1
        print("--- _suspended = ", self._suspended)
        if not self._suspended and self._resume_event:
            await self._resume_event.set()

    def suspend(self) -> None:
        """Temporarily suspends the hotplug detector."""
        self._suspended += 1
        print("+++ _suspended = ", self._suspended)
        if self._suspended and not self._resume_event:
            self._resume_event = create_event()

    @asynccontextmanager
    @async_generator
    async def suspended(self) -> None:
        """Async context manager that suspends the hotplug detector while the
        execution is in the context.
        """
        self.suspend()
        try:
            await yield_()
        finally:
            await self.resume()

    @staticmethod
    def _preprocess_params(params: Dict) -> Dict:
        """Preprocesses the parameters passed to the constructor, remapping
        the following commonly used aliases to identifiers used by `pyusb`:

        * `vid` is renamed to `idVendor`
        * `pid` is renamed to `idProduct`

        Parameters:
            params: the dictionary to process. It will be modified in-place.

        Returns:
            the same dictionary that was passed in
        """
        aliases = {"vid": ("idVendor", _to_int), "pid": ("idProduct", _to_int)}

        for old, (new, func) in aliases.items():
            if old in params and new not in params:
                value = params.pop(old)
                if func:
                    value = func(value)
                params[new] = value

        return params
