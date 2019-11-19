"""Setup script for the aio_usb_hotplug package."""

from glob import glob
from os.path import basename, splitext
from setuptools import setup, find_packages

requires = [
    "anyio>=1.2.0",
    "async-generator>=1.10",
    "pyusb>=1.0.2",
    "pyudev>=0.21.0; platform_system=='Linux'",
]

extras_require = {
    "dev": ["curio>=0.9", "pytest>=5.2.4", "pytest-cov>=2.0.1", "trio>=0.13.0"]
}

__version__ = None
exec(open("src/aio_usb_hotplug/version.py").read())

setup(
    name="aio_usb_hotplug",
    version=__version__,
    author=u"Tam\u00e1s Nepusz",
    author_email="ntamas@gmail.com",
    url="https://github.com/ntamas/aio-usb-hotplug",
    packages=find_packages("src"),
    package_data={"aio_usb_hotplug": ["py.typed"]},
    package_dir={"": "src"},
    py_modules=[splitext(basename(path))[0] for path in glob("src/*.py")],
    include_package_data=True,
    python_requires=">=3.5",
    install_requires=requires,
    extras_require=extras_require,
    test_suite="test",
)
