from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

from PIL import Image

from weather_epaper.config import Settings, truthy_env
from weather_epaper.device import Epd27Device, MockDevice
from weather_epaper.render import (
    left_panel_fingerprint,
    weather_image,
    weather_image_clock_only,
)
from weather_epaper.weather_history import append_weather_history
from weather_epaper.weather_client import CurrentWeather, fetch_current


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Weather on Waveshare 2.7\" e-paper")
    p.add_argument(
        "--mock",
        action="store_true",
        help="Write PNG instead of driving SPI (also WEATHER_EPAPER_MOCK=1)",
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="Fetch and display once, then exit (no sleep loop)",
    )
    return p.parse_args(argv)


def _device(settings: Settings):
    if settings.mock:
        return MockDevice(Path(settings.mock_output_path))
    return Epd27Device()


def run_loop(settings: Settings, args: argparse.Namespace) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    device = _device(settings)

    w: CurrentWeather | None = None
    next_weather_mono = 0.0
    last_full_image: Image.Image | None = None

    while True:
        now_mono = time.monotonic()
        left_changed = False
        if w is None or now_mono >= next_weather_mono:
            try:
                w_new = fetch_current(
                    settings.latitude,
                    settings.longitude,
                    timezone_name=settings.timezone,
                )
                next_weather_mono = now_mono + settings.weather_refresh_seconds
                left_changed = w is None or left_panel_fingerprint(w) != left_panel_fingerprint(
                    w_new
                )
                w = w_new
                try:
                    append_weather_history(Path(settings.weather_history_path), w_new)
                except OSError:
                    logging.exception("Weather history write failed")
            except Exception:
                logging.exception("Weather fetch failed")
                if w is None:
                    logging.error("No weather data yet; retrying after display interval")
        if w is not None:
            try:
                hardware_full = args.once or left_changed
                if hardware_full or last_full_image is None:
                    img = weather_image(
                        w,
                        location_label=settings.location_label,
                        display_tz=settings.display_tz,
                    )
                    last_full_image = img.copy()
                else:
                    img = weather_image_clock_only(
                        last_full_image,
                        w,
                        display_tz=settings.display_tz,
                    )
                device.show(img, full_refresh=hardware_full)
            except Exception:
                logging.exception("Display update failed")
        if args.once:
            break
        time.sleep(settings.display_refresh_seconds)
    return 0


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    mock = args.mock or truthy_env("WEATHER_EPAPER_MOCK")
    settings = Settings.from_environ(mock=mock)
    raise SystemExit(run_loop(settings, args))


if __name__ == "__main__":
    main()
