from .task import HotplugDetector

from trio import run


async def main():
    detector = HotplugDetector.for_device(vid="1050", pid="0407")
    async for event in detector.run():
        print("{0.type.value} device {0.key}".format(event))


if __name__ == "__main__":
    run(main)
