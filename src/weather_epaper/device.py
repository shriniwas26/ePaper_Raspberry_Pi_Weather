from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


class DisplayDevice(ABC):
    @abstractmethod
    def show(self, image: Image.Image) -> None:
        """Send a PIL image (mode '1', size 176x264) to the display or sink."""


class MockDevice(DisplayDevice):
    def __init__(self, output_path: Path) -> None:
        self._output_path = output_path

    def show(self, image: Image.Image) -> None:
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        # 1-bit PNG is fine; also readable in preview tools
        image.save(self._output_path, format="PNG")
        logger.info("Wrote mock preview to %s", self._output_path)


def _epd_driver_class():
    """V2 SSD1680 protocol is used on current 2.7\" B/W HATs; V1 is older stock."""
    variant = os.environ.get("WEATHER_EPAPER_EPD", "v2").strip().lower()
    if variant in ("v1", "1", "legacy", "old"):
        from waveshare.epd2in7 import EPD

        logger.info("e-Paper driver: epd2in7 (legacy V1)")
        return EPD
    from waveshare.epd2in7_V2 import EPD

    logger.info("e-Paper driver: epd2in7_V2 (V2, default)")
    return EPD


class Epd27Device(DisplayDevice):
    """Waveshare 2.7\" B/W HAT via vendored waveshare driver (PI only)."""

    def __init__(self) -> None:
        # Pi OS Bookworm+: sysfs GPIO is unavailable; gpiozero defaults to native and fails.
        os.environ.setdefault("GPIOZERO_PIN_FACTORY", "lgpio")
        self._EPD = _epd_driver_class()
        self._epd: object | None = None

    def show(self, image: Image.Image) -> None:
        epd = self._EPD()
        self._epd = epd
        if epd.init() != 0:
            raise RuntimeError("e-Paper init failed")
        try:
            buffer = epd.getbuffer(image)
            epd.display(buffer)
        finally:
            epd.sleep()
            self._epd = None
