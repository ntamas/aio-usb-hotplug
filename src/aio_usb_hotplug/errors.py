__all__ = ("NoBackendError",)


class NoBackendError(RuntimeError):
    """Error thrown when there is no suitable backend for scanning the USB
    bus on the current platform.
    """

    pass
