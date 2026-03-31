"""Weather display for Waveshare 2.7\" B/W e-paper."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("weather-epaper")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["__version__"]
