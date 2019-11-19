"""Setup script for the aio_usb_hotplug package."""

from glob import glob
from os.path import basename, splitext
from setuptools import setup, find_packages

requires = [
    "anyio>=1.2.0",
    "async-generator>=1.10",
    "pyudev>=0.21.0; platform_system=='Linux'",
]

__version__ = None
exec(open("src/aio_usb_hotplug/version.py").read())

setup(
    name="aio_usb_hotplug",
    version=__version__,
    author=u"Tam\u00e1s Nepusz",
    author_email="ntamas@gmail.com",
    packages=find_packages("src"),
    package_data={"aio_usb_hotplug": ["py.typed"]},
    package_dir={"": "src"},
    py_modules=[splitext(basename(path))[0] for path in glob("src/*.py")],
    include_package_data=True,
    python_requires=">=3.5",
    install_requires=requires,
    extras_require={},
    test_suite="test",
)
