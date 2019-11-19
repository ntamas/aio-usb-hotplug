from .base import USBBusScannerBackend


def choose_backend() -> USBBusScannerBackend:
    """Chooses an appropriate USB bus scanner backend for the current
    platform when invoked with no arguments.

    Returns:
        a newly constructed USB bus scanner backend instance
    """
    from .pyusb import PyUSBBusScannerBackend

    return PyUSBBusScannerBackend()
