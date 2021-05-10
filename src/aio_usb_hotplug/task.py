"""Hotplug detector for USB devices."""

from anyio import CancelScope, Event, create_task_group
from async_generator import async_generator, yield_
from collections import namedtuple
from contextlib import contextmanager
from enum import Enum
from typing import Callable, Coroutine, Dict, Iterator, Optional, Union

from .backends.base import Device, USBBusScannerBackend
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
    async def added_devices(self) -> Iterator[HotplugEvent]:
        """Runs the hotplug detection in an asynchronous task.

        Yields:
            Device: device objects, one for each device whose addition was
                detected. Removed devices are not reported.
        """
        async for event in self.events():
            if event.type == HotplugEventType.ADDED:
                await yield_(event.device)

    @async_generator
    async def events(self) -> Iterator[HotplugEvent]:
        """Runs the hotplug detection in an asynchronous task.

        Yields:
            HotplugEvent: event objects describing the devices that were added
                or removed
        """
        backend = self._backend() if callable(self._backend) else self._backend
        backend.configure(self._params)
        key_of = backend.key_of

        while True:
            if self._suspended:
                await self._resume_event.wait()

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

    @async_generator
    async def removed_devices(self) -> Iterator[HotplugEvent]:
        """Runs the hotplug detection in an asynchronous task.

        Yields:
            Device: device objects, one for each device whose removal was
                detected. Added devices are not reported.
        """
        async for event in self.events():
            if event.type == HotplugEventType.REMOVED:
                await yield_(event.device)

    def resume(self) -> None:
        """Resumes the hotplug detector task after a suspension."""
        self._suspended -= 1
        if not self._suspended and self._resume_event:
            self._resume_event.set()

    async def run_for_each_device(
        self,
        task: Callable[[Device], Coroutine],
        *,
        predicate: Optional[Callable[[Device], bool]] = None,
        cancellable: bool = True
    ) -> None:
        """Runs a background task that listens for hotplug events and runs an
        asynchronous task for each device that was added to the USB bus.

        Parameters:
            task: the task to run for each matched device
            predicate: an optional predicate to evaluate for each device. When
                the predicate returns `False`, no task will be spawned for the
                matched device.
            cancellable: whether to cancel tasks corresponding to devices that
                were removed
        """
        predicate = predicate or (lambda _: True)
        cancel_scopes_by_key = {}

        async with create_task_group() as tasks:
            if cancellable:

                async def _task_wrapper(event):
                    """Wrapper for the task object that clears its cancel scope from the
                    resulting dictionary when the task terminates.
                    """
                    with CancelScope() as scope:
                        cancel_scopes_by_key[event.key] = scope
                        try:
                            await task(event.device)
                        finally:
                            del cancel_scopes_by_key[event.key]

            else:

                async def _task_wrapper(event):
                    """Wrapper for the task object that clears its cancel scope from the
                    resulting dictionary when the task terminates.
                    """
                    cancel_scopes_by_key[event.key] = None
                    try:
                        await task(event.device)
                    finally:
                        del cancel_scopes_by_key[event.key]

            async for event in self.events():
                if event.type == HotplugEventType.ADDED and predicate(event.device):
                    if event.key not in cancel_scopes_by_key:
                        tasks.start_soon(_task_wrapper, event)
                elif event.type == HotplugEventType.REMOVED:
                    cancel_scope = cancel_scopes_by_key.get(event.key)
                    if cancel_scope:
                        cancel_scope.cancel()

    def suspend(self) -> None:
        """Temporarily suspends the hotplug detector."""
        self._suspended += 1
        if self._suspended and not self._resume_event:
            self._resume_event = Event()

    @contextmanager
    def suspended(self) -> None:
        """Async context manager that suspends the hotplug detector while the
        execution is in the context.
        """
        self.suspend()
        try:
            yield
        finally:
            self.resume()

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
