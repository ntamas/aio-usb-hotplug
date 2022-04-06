from .task import HotplugDetector

from anyio import run


async def main():
    detector = HotplugDetector.for_device(vid="1050", pid="0407")
    async for event in detector.events():
        print(f"{event.type.value} device {event.key}")


if __name__ == "__main__":
    run(main)
