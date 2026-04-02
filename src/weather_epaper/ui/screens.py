from __future__ import annotations

import socket
from dataclasses import dataclass
from enum import Enum, auto
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from PIL import Image, ImageDraw

from weather_epaper.config import Settings
from weather_epaper.render import (
    BLACK,
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    MARGIN,
    WHITE,
    ui_font,
    weather_image,
)
from weather_epaper.weather_client import CurrentWeather


class ScreenId(Enum):
    WEATHER = auto()
    SYSTEM = auto()
    RESTART = auto()


@dataclass(frozen=True)
class RenderContext:
    settings: Settings
    weather: CurrentWeather | None
    reboot_armed: bool


def render_screen(screen: ScreenId, ctx: RenderContext) -> Image.Image:
    if screen is ScreenId.WEATHER:
        if ctx.weather is None:
            return _render_no_weather()
        return weather_image(ctx.weather, display_tz=ctx.settings.display_tz)
    if screen is ScreenId.SYSTEM:
        return _render_system()
    return _render_restart(ctx.reboot_armed)


def _render_no_weather() -> Image.Image:
    img = Image.new("1", (CANVAS_WIDTH, CANVAS_HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)
    font = ui_font(18)
    draw.text((MARGIN, CANVAS_HEIGHT // 2 - 20), "No weather yet", font=font, fill=BLACK)
    draw.text((MARGIN, CANVAS_HEIGHT // 2 + 6), "Fetching...", font=ui_font(14), fill=BLACK)
    return img


def _render_system() -> Image.Image:
    img = Image.new("1", (CANVAS_WIDTH, CANVAS_HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)
    y = MARGIN
    title = ui_font(22)
    body = ui_font(14)
    small = ui_font(12)
    draw.text((MARGIN, y), "System", font=title, fill=BLACK)
    y += 28
    draw.text((MARGIN, y), f"Host: {socket.gethostname()}", font=body, fill=BLACK)
    y += 20
    try:
        ver = version("weather-epaper")
    except PackageNotFoundError:
        ver = "dev"
    draw.text((MARGIN, y), f"App: {ver}", font=body, fill=BLACK)
    y += 20
    try:
        load = Path("/proc/loadavg").read_text(encoding="utf-8").split()[0]
        draw.text((MARGIN, y), f"Load: {load}", font=body, fill=BLACK)
        y += 20
    except OSError:
        pass
    draw.text((MARGIN, CANVAS_HEIGHT - MARGIN - 14), "K1/K2 nav  K3 home", font=small, fill=BLACK)
    return img


def _render_restart(reboot_armed: bool) -> Image.Image:
    img = Image.new("1", (CANVAS_WIDTH, CANVAS_HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)
    y = MARGIN
    title = ui_font(20)
    body = ui_font(14)
    draw.text((MARGIN, y), "Restart Pi", font=title, fill=BLACK)
    y += 28
    lines = [
        "Two-step:",
        "Press K4 to arm.",
    ]
    if reboot_armed:
        lines += ["", "ARMED.", "Press K4 again", "to reboot.", "", "K1/K2/K3 cancel"]
    else:
        lines += ["", "K1/K2: other screens", "K3: home (cancel)"]
    for line in lines:
        draw.text((MARGIN, y), line, font=body, fill=BLACK)
        y += 18
    return img
