from __future__ import annotations

import argparse
import datetime as dt
import logging
import time
from pathlib import Path

from weather_epaper.config import Settings, truthy_env
from weather_epaper.device import Epd27Device, MockDevice
from weather_epaper.render import weather_image
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

    while True:
        now_mono = time.monotonic()
        if w is None or now_mono >= next_weather_mono:
            try:
                w = fetch_current(
                    settings.latitude,
                    settings.longitude,
                    timezone_name=settings.timezone,
                )
                next_weather_mono = now_mono + settings.weather_refresh_seconds
                try:
                    append_weather_history(Path(settings.weather_history_path), w)
                except OSError:
                    logging.exception("Weather history write failed")
            except Exception:
                logging.exception("Weather fetch failed")
                if w is None:
                    logging.error("No weather data yet; retrying after display interval")
        if w is not None:
            try:
                img = weather_image(
                    w,
                    display_tz=settings.display_tz,
                )
                device.show(img)
            except Exception:
                logging.exception("Display update failed")
        if args.once:
            break
        now = dt.datetime.now()
        sleep_ms = 1.0 - now.microsecond / 1_000_000
        time.sleep(sleep_ms)
    return 0


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    mock = args.mock or truthy_env("WEATHER_EPAPER_MOCK")
    settings = Settings.from_environ(mock=mock)
    raise SystemExit(run_loop(settings, args))


if __name__ == "__main__":
    main()
