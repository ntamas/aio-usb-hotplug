from aio_usb_hotplug import HotplugDetector
from aio_usb_hotplug.backends.base import USBBusScannerBackend
from anyio import create_task_group, open_cancel_scope, move_on_after, sleep
from pytest import fixture, mark
from typing import List


class MockBackend(USBBusScannerBackend):
    """Mock backend for testing without having access to real USB devices."""

    def __init__(self):
        self._devices = set()
        self.params = {}

    def add(self, device: str) -> None:
        self._devices.add(device)

    def configure(self, params):
        self.params = dict(params)

    def key_of(self, device: str) -> str:
        return device

    def remove(self, device: str) -> None:
        self._devices.remove(device)

    async def scan(self) -> List[str]:
        await sleep(0.01)
        return sorted(self._devices)

    async def wait_until_next_scan(self) -> None:
        await sleep(0.01)


@fixture
def backend():
    return MockBackend()


@fixture
def events():
    class EventCollector:
        def __init__(self):
            self._items = []

        def add(self, event):
            self._items.append(event)

        def get(self):
            result = list(self._items)
            self._items.clear()
            return result

    return EventCollector()


@mark.anyio
async def test_event_generator(backend, events):
    scanner = HotplugDetector(backend=backend)

    async def scenario(end):
        backend.add("foo")
        await sleep(0.03)
        assert events.get() == [("added", "foo")]

        backend.add("bar")
        backend.add("bar")
        backend.add("bar")
        await sleep(0.03)
        assert events.get() == [("added", "bar")]

        backend.remove("bar")
        backend.add("baz")
        await sleep(0.03)
        assert sorted(events.get()) == [("added", "baz"), ("removed", "bar")]

        backend.remove("foo")
        backend.remove("baz")
        await sleep(0.03)
        assert sorted(events.get()) == [("removed", "baz"), ("removed", "foo")]

        await end()

    async with create_task_group() as tg:
        async with open_cancel_scope() as scope:
            await tg.spawn(scenario, scope.cancel)
            async for event in scanner.events():
                events.add((event.type.value, event.device))


@mark.anyio
async def test_event_generator_suspension(backend, events):
    scanner = HotplugDetector(backend=backend)

    async def scenario(end):
        async with scanner.suspended():
            await sleep(0.03)

            backend.add("foo")
            await sleep(0.03)
            assert events.get() == []

            backend.add("bar")
            backend.add("bar")
            backend.add("bar")
            await sleep(0.03)
            assert events.get() == []

            backend.remove("bar")
            backend.add("baz")
            await sleep(0.03)
            assert events.get() == []

        await sleep(0.03)
        assert sorted(events.get()) == [("added", "baz"), ("added", "foo")]

        backend.remove("foo")
        backend.remove("baz")
        await sleep(0.03)
        assert sorted(events.get()) == [("removed", "baz"), ("removed", "foo")]

        await end()

    async with create_task_group() as tg:
        async with open_cancel_scope() as scope:
            await tg.spawn(scenario, scope.cancel)
            async for event in scanner.events():
                events.add((event.type.value, event.device))


@mark.anyio
async def test_vid_pid_transformation(backend):
    scanner = HotplugDetector.for_device(vid="0402", pid="0x0204", backend=backend)

    async with move_on_after(0.001):
        async for event in scanner.events():
            pass

    assert backend.params["idVendor"] == 0x0402
    assert backend.params["idProduct"] == 0x0204
