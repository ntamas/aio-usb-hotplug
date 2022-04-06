from functools import partial
from typing import Callable, List

from .base import USBBusScannerBackend

from ..errors import NoBackendError

__all__ = ("choose_backend",)


def choose_backend(
    allow_dummy: bool = False, allow_libusb_package: bool = True
) -> USBBusScannerBackend:
    """Chooses an appropriate USB bus scanner backend for the current
    platform when invoked with no arguments.

    Parameters:
        allow_dummy: whether the function is allowed to return a dummy backend
            if no backend is supported on the current platform
        allow_libusb_package: whether the function is allowed to make use of
            a packaged libusb instance provided by the ``libusb_package``
            Python package

    Returns:
        a newly constructed USB bus scanner backend instance

    Raises:
        NoBackendError: if there is no suitable USB bus scanner backend
            for the current platform and `allow_dummy` is set to `False`
    """
    from .dummy import DummyUSBBusScannerBackend
    from .pyusb import PyUSBBusScannerBackend

    backends: List[Callable[[], USBBusScannerBackend]] = [PyUSBBusScannerBackend]

    if allow_libusb_package:
        backends.insert(0, partial(PyUSBBusScannerBackend, use_libusb_package=True))
    if allow_dummy:
        backends.append(DummyUSBBusScannerBackend)

    for backend_factory in backends:
        backend = backend_factory()
        if backend.is_supported():
            return backend

    raise NoBackendError(
        "No supported backend for scanning the USB bus on this platform"
    )
