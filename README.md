# aio-usb-hotplug

`aio-usb-hotplug` is a Python library that provides asynchronous generators
yielding detected hotplug events on the USB buses.

Requires Python >= 3.5.

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

```python
from aio_usb_hotplug import HotplugDetector
from trio import run  # ...or asyncio, or curio

async def dump_events():
    async for event in HotplugDetector.for_device(vid="1050", pid="0407"):
        print(repr(event))

trio.run(dump_events)
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to
discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)
