from __future__ import annotations

import argparse
import datetime as dt
import logging
import time
from pathlib import Path
from queue import Empty, SimpleQueue

from weather_epaper.config import Settings, truthy_env
from weather_epaper.device import DisplayDevice, Epd27Device, MockDevice
from weather_epaper.input_hat import HatButtons
from weather_epaper.ui.navigation import KeyId, ScreenManager
from weather_epaper.ui.screens import RenderContext
from weather_epaper.weather_client import CurrentWeather, fetch_current
from weather_epaper.weather_history import append_weather_history

logger = logging.getLogger(__name__)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Weather on Waveshare 2.7" e-paper')
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


def _device(settings: Settings) -> DisplayDevice:
    if settings.mock:
        return MockDevice(Path(settings.mock_output_path))
    return Epd27Device()


def run_loop(settings: Settings, args: argparse.Namespace) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    device = _device(settings)
    key_queue: SimpleQueue[KeyId] = SimpleQueue()
    manager = ScreenManager()

    w: CurrentWeather | None = None
    next_weather_mono = 0.0

    with HatButtons(settings, key_queue):
        while True:
            deadline = time.monotonic() + max(0.01, 1.0 - dt.datetime.now().microsecond / 1_000_000)
            while time.monotonic() < deadline:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                try:
                    key = key_queue.get(timeout=min(remaining, 0.05))
                except Empty:
                    continue
                manager.handle_key(key)

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
                        logger.exception("Weather history write failed")
                except Exception:
                    logger.exception("Weather fetch failed")
                    if w is None:
                        logger.error("No weather data yet; retrying after display interval")

            try:
                ctx = RenderContext(
                    settings=settings,
                    weather=w,
                    reboot_armed=manager.reboot_armed,
                )
                img = manager.render(ctx)
                device.show(img)
            except Exception:
                logger.exception("Display update failed")

            if args.once:
                break
    return 0


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    mock = args.mock or truthy_env("WEATHER_EPAPER_MOCK")
    settings = Settings.from_environ(mock=mock)
    raise SystemExit(run_loop(settings, args))


if __name__ == "__main__":
    main()
