# aio-usb-hotplug

`aio-usb-hotplug` is a Python library that provides asynchronous generators
yielding detected hotplug events on the USB buses.

Requires Python >= 3.7.

Works with [`asyncio`](https://docs.python.org/3/library/asyncio.html),
[`curio`](https://curio.readthedocs.io/en/latest/) and
[`trio`](https://trio.readthedocs.io/en/stable/).

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install
`aio-usb-hotplug`.

```bash
pip install aio-usb-hotplug
```

## Usage

### Dump all hotplug events related to a specific USB device

```python
from aio_usb_hotplug import HotplugDetector
from trio import run  # ...or asyncio, or curio

async def dump_events():
    detector = HotplugDetector.for_device(vid="1050", pid="0407")
    async for event in detector.events():
        print(repr(event))

trio.run(dump_events)
```

### Run an async task for each USB device matching a VID/PID pair

```python
from aio_usb_hotplug import HotplugDetector
from trio import sleep_forever


async def handle_device(device):
    print("Handling device:", repr(device))
    try:
        # Do something meaningful with the device. The task gets cancelled
        # when the device is unplugged.
        await sleep_forever()
    finally:
        # Device unplugged or an exception happened
        print("Stopped handling device:", repr(device))


async def handle_detected_devices():
    detector = HotplugDetector.for_device(vid="1050", pid="0407")
    await detector.run_for_each_device(handle_device)


trio.run(handle_detected_devices)
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to
discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)
