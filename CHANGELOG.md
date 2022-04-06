# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [5.0.0] - 2022-04-07

### Changed

- `HotplugEvent` is now a Python dataclass, not a `namedtuple`.

- `libusb-package` is now detected automatically and this library will use the
  bundled `libusb` version when `libusb-package` is available.

## [4.0.1] - 2021-10-08

This is the release that serves as a basis for changelog entries above. Refer
to the commit logs for changes affecting this version and earlier versions.
