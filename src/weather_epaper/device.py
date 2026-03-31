from __future__ import annotations

import atexit
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path

from PIL import Image

from weather_epaper.render import clock_partial_bbox_panel

logger = logging.getLogger(__name__)


class DisplayDevice(ABC):
    @abstractmethod
    def show(self, image: Image.Image, *, full_refresh: bool = True) -> None:
        """Send a PIL image (mode '1', landscape 264x176) to the display or sink."""


class MockDevice(DisplayDevice):
    def __init__(self, output_path: Path) -> None:
        self._output_path = output_path

    def show(self, image: Image.Image, *, full_refresh: bool = True) -> None:
        _ = full_refresh
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        # 1-bit PNG is fine; also readable in preview tools
        image.save(self._output_path, format="PNG")
        logger.info("Wrote mock preview to %s", self._output_path)


def _epd_supports_partial() -> bool:
    variant = os.environ.get("WEATHER_EPAPER_EPD", "v2").strip().lower()
    return variant not in ("v1", "1", "legacy", "old")


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
        self._supports_partial = _epd_supports_partial()
        self._epd: object | None = None
        self._did_full_display = False
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
            self._did_full_display = False

    def show(self, image: Image.Image, *, full_refresh: bool = True) -> None:
        epd = self._ensure_epd()
        buffer = epd.getbuffer(image)
        need_full = (
            full_refresh
            or not self._supports_partial
            or not self._did_full_display
        )
        if need_full:
            epd.display(buffer)
            self._did_full_display = True
            return
        xs, ys, xe, ye = clock_partial_bbox_panel()
        epd.display_Partial(buffer, xs, ys, xe, ye)
