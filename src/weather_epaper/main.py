from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

from weather_epaper.config import Settings, truthy_env
from weather_epaper.device import Epd27Device, MockDevice
from weather_epaper.render import weather_image
from weather_epaper.weather_client import fetch_current


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
    location_label = f"{settings.latitude:.2f},{settings.longitude:.2f}"

    while True:
        try:
            w = fetch_current(
                settings.latitude,
                settings.longitude,
                timezone_name=settings.timezone,
            )
            img = weather_image(w, location_label=location_label)
            device.show(img)
        except Exception:
            logging.exception("Update failed")
        if args.once:
            break
        time.sleep(max(60, settings.refresh_seconds))
    return 0


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    mock = args.mock or truthy_env("WEATHER_EPAPER_MOCK")
    settings = Settings.from_environ(mock=mock)
    raise SystemExit(run_loop(settings, args))


if __name__ == "__main__":
    main()
