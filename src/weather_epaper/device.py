from __future__ import annotations

import atexit
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


class DisplayDevice(ABC):
    @abstractmethod
    def show(self, image: Image.Image) -> None:
        """Send a PIL image (mode '1', landscape 264x176) to the display or sink."""


class MockDevice(DisplayDevice):
    def __init__(self, output_path: Path) -> None:
        self._output_path = output_path

    def show(self, image: Image.Image) -> None:
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(self._output_path, format="PNG")
        logger.info("Wrote mock preview to %s", self._output_path)


def _is_v2() -> bool:
    variant = os.environ.get("WEATHER_EPAPER_EPD", "v2").strip().lower()
    return variant not in ("v1", "1", "legacy", "old")


def _epd_driver_class():
    """V2 SSD1680 protocol is used on current 2.7\" B/W HATs; V1 is older stock."""
    if not _is_v2():
        from waveshare.epd2in7 import EPD

        logger.info("e-Paper driver: epd2in7 (legacy V1)")
        return EPD
    from waveshare.epd2in7_V2 import EPD

    logger.info("e-Paper driver: epd2in7_V2 (V2, default)")
    return EPD


class Epd27Device(DisplayDevice):
    """Waveshare 2.7\" B/W HAT via vendored waveshare driver (PI only)."""

    def __init__(self) -> None:
        os.environ.setdefault("GPIOZERO_PIN_FACTORY", "lgpio")
        self._EPD = _epd_driver_class()
        self._v2 = _is_v2()
        self._epd: object | None = None
        self._prev_buffer: list | None = None
        self._base_seeded = False
        atexit.register(self._shutdown_epd)

    def _ensure_epd(self) -> object:
        if self._epd is None:
            epd = self._EPD()
            if epd.init() != 0:
                raise RuntimeError("e-Paper init failed")
            self._epd = epd
        return self._epd

    def _shutdown_epd(self) -> None:
        epd = self._epd
        if epd is None:
            return
        try:
            epd.sleep()
        except Exception:
            logger.exception("e-Paper sleep failed on shutdown")
        finally:
            self._epd = None
            self._base_seeded = False
            self._prev_buffer = None

    def show(self, image: Image.Image) -> None:
        epd = self._ensure_epd()
        buffer = epd.getbuffer(image)
        if buffer == self._prev_buffer:
            return
        self._prev_buffer = list(buffer)
        if not self._base_seeded or not self._v2:
            if self._v2:
                epd.display_Base(buffer)
            else:
                epd.display(buffer)
            self._base_seeded = True
            return
        epd.display_Partial_Wait(buffer)
