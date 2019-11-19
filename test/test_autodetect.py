from aio_usb_hotplug import choose_backend


def test_autodetection():
    backend = choose_backend()
    assert backend.__class__.__name__ == "PyUSBBusScannerBackend"
