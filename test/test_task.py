from aio_usb_hotplug import HotplugDetector
from aio_usb_hotplug.backends.base import USBBusScannerBackend
from anyio import (
    create_event,
    create_task_group,
    open_cancel_scope,
    move_on_after,
    sleep,
)
from collections import defaultdict
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
        await sleep(0.001)
        return sorted(self._devices)

    async def wait_until_next_scan(self) -> None:
        await sleep(0.001)


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
        await sleep(0.003)
        assert events.get() == [("added", "foo")]

        backend.add("bar")
        backend.add("bar")
        backend.add("bar")
        await sleep(0.003)
        assert events.get() == [("added", "bar")]

        backend.remove("bar")
        backend.add("baz")
        await sleep(0.003)
        assert sorted(events.get()) == [("added", "baz"), ("removed", "bar")]

        backend.remove("foo")
        backend.remove("baz")
        await sleep(0.003)
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
            await sleep(0.003)

            backend.add("foo")
            await sleep(0.003)
            assert events.get() == []

            backend.add("bar")
            backend.add("bar")
            backend.add("bar")
            await sleep(0.003)
            assert events.get() == []

            backend.remove("bar")
            backend.add("baz")
            await sleep(0.003)
            assert events.get() == []

        await sleep(0.003)
        assert sorted(events.get()) == [("added", "baz"), ("added", "foo")]

        backend.remove("foo")
        backend.remove("baz")
        await sleep(0.003)
        assert sorted(events.get()) == [("removed", "baz"), ("removed", "foo")]

        await end()

    async with create_task_group() as tg:
        async with open_cancel_scope() as scope:
            await tg.spawn(scenario, scope.cancel)
            async for event in scanner.events():
                events.add((event.type.value, event.device))


@mark.anyio
async def test_added_device_generator(backend, events):
    scanner = HotplugDetector(backend=backend)

    async def scenario(end):
        backend.add("foo")
        await sleep(0.003)
        assert events.get() == ["foo"]

        backend.add("bar")
        backend.add("bar")
        backend.add("bar")
        await sleep(0.003)
        assert events.get() == ["bar"]

        backend.remove("bar")
        backend.add("baz")
        await sleep(0.003)
        assert events.get() == ["baz"]

        backend.remove("foo")
        backend.remove("baz")
        await sleep(0.003)
        assert events.get() == []

        await end()

    async with create_task_group() as tg:
        async with open_cancel_scope() as scope:
            await tg.spawn(scenario, scope.cancel)
            async for device in scanner.added_devices():
                events.add(device)


@mark.anyio
async def test_removed_device_generator(backend, events):
    scanner = HotplugDetector(backend=backend)

    async def scenario(end):
        backend.add("foo")
        await sleep(0.003)
        assert events.get() == []

        backend.add("bar")
        backend.add("bar")
        backend.add("bar")
        await sleep(0.003)
        assert events.get() == []

        backend.remove("bar")
        backend.add("baz")
        await sleep(0.003)
        assert events.get() == ["bar"]

        backend.remove("foo")
        backend.remove("baz")
        await sleep(0.003)
        assert sorted(events.get()) == ["baz", "foo"]

        await end()

    async with create_task_group() as tg:
        async with open_cancel_scope() as scope:
            await tg.spawn(scenario, scope.cancel)
            async for device in scanner.removed_devices():
                events.add(device)


@mark.anyio
async def test_run_for_each_device(backend):
    scanner = HotplugDetector(backend=backend)
    counters = defaultdict(int)

    async def handler(device):
        counters[device] += 1
        try:
            while True:
                await sleep(1000)
        finally:
            counters[device] -= 1

    async def scenario(end):
        backend.add("foo")
        await sleep(0.01)
        assert counters == {"foo": 1}

        backend.add("bar")
        backend.add("bar")
        backend.add("bar")
        await sleep(0.01)
        assert counters == {"foo": 1, "bar": 1}

        backend.remove("bar")
        backend.add("baz")
        await sleep(0.01)
        assert counters == {"foo": 1, "bar": 0, "baz": 1}

        backend.remove("foo")
        backend.remove("baz")
        await sleep(0.01)
        assert counters == {"foo": 0, "bar": 0, "baz": 0}

        await end()

    async with create_task_group() as tg:
        async with open_cancel_scope() as scope:
            await tg.spawn(scenario, scope.cancel)
            await scanner.run_for_each_device(handler)


@mark.anyio
async def test_run_for_each_device_non_cancellable(backend):
    scanner = HotplugDetector(backend=backend)
    counters = defaultdict(int)
    stopped = create_event()

    async def handler(device):
        counters[device] += 1
        try:
            await stopped.wait()
        finally:
            counters[device] -= 1

    async def scenario(end):
        backend.add("foo")
        await sleep(0.003)
        assert counters == {"foo": 1}

        backend.add("bar")
        backend.add("bar")
        backend.add("bar")
        await sleep(0.01)
        assert counters == {"foo": 1, "bar": 1}

        backend.remove("bar")
        backend.add("baz")
        await sleep(0.01)
        assert counters == {"foo": 1, "bar": 1, "baz": 1}

        backend.remove("foo")
        backend.remove("baz")
        await sleep(0.01)
        assert counters == {"foo": 1, "bar": 1, "baz": 1}

        await stopped.set()

        await sleep(0.01)
        assert counters == {"foo": 0, "bar": 0, "baz": 0}
        await end()

    async with create_task_group() as tg:
        async with open_cancel_scope() as scope:
            await tg.spawn(scenario, scope.cancel)
            await scanner.run_for_each_device(handler, cancellable=False)


@mark.anyio
async def test_vid_pid_transformation(backend):
    scanner = HotplugDetector.for_device(vid="0402", pid="0x0204", backend=backend)

    async with move_on_after(0.001):
        async for event in scanner.events():
            pass

    assert backend.params["idVendor"] == 0x0402
    assert backend.params["idProduct"] == 0x0204
