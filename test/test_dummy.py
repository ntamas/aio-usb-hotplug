from aio_usb_hotplug.backends.dummy import DummyUSBBusScannerBackend
from anyio import move_on_after
from pytest import fixture, mark


@fixture
def backend():
    return DummyUSBBusScannerBackend()


def test_dummy_supported(backend):
    assert backend.is_supported()


def test_dummy_key(backend):
    assert backend.key_of("123") == str(id("123"))


@mark.anyio
async def test_dummy_scan(backend):
    items = await backend.scan()
    assert not items


@mark.anyio
async def test_wait_until_next_scan(backend):
    async with move_on_after(0.01):
        await backend.wait_until_next_scan()
        assert False, "wait_until_next_scan() should not have returned"
