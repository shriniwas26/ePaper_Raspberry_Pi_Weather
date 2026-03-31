from __future__ import annotations

import datetime as dt

from PIL import Image, ImageDraw, ImageFont

from weather_epaper.icons import (
    GLYPH_REFRESH,
    GLYPH_THERMOMETER,
    GLYPH_WATER,
    GLYPH_WIND,
    mdi_font,
)
from weather_epaper.weather_client import CurrentWeather

# Landscape: 264x176 (epd2in7 horizontal buffer).
CANVAS_WIDTH = 264
CANVAS_HEIGHT = 176
MARGIN = 8
BAR_H = 20
BAR_ICON_PX = 14
BAR_ICON_BOX = 16

_FONT_CANDIDATES: tuple[tuple[str, int | None], ...] = (
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", None),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", None),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", None),
    ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", None),
    ("/System/Library/Fonts/Supplemental/Arial.ttf", None),
    ("/System/Library/Fonts/Helvetica.ttc", 0),
)

_FONT_MONO: tuple[tuple[str, int | None], ...] = (
    ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", None),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", None),
    ("/System/Library/Fonts/Supplemental/Menlo.ttc", 0),
    ("/Library/Fonts/Menlo.ttc", 0),
)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path, index in _FONT_CANDIDATES:
        try:
            if path.endswith(".ttc") and index is not None:
                return ImageFont.truetype(path, size, index=index)
            if not path.endswith(".ttc"):
                return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _load_mono_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path, index in _FONT_MONO:
        try:
            if path.endswith(".ttc") and index is not None:
                return ImageFont.truetype(path, size, index=index)
            if not path.endswith(".ttc"):
                return ImageFont.truetype(path, size)
        except OSError:
            continue
    return _load_font(size)


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    b = draw.textbbox((0, 0), text, font=font)
    return b[2] - b[0]


def _text_height(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    b = draw.textbbox((0, 0), text, font=font)
    return b[3] - b[1]


def _weather_age_label(fetched_at_utc: dt.datetime) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    ft = fetched_at_utc.astimezone(dt.timezone.utc)
    secs = int(max(0, (now - ft).total_seconds()))
    if secs < 45:
        return "now"
    mins = (secs + 30) // 60
    if mins == 1:
        return "1 min"
    return f"{mins} min"


def _draw_bar_item(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    glyph: str,
    icon_font: ImageFont.ImageFont,
    label: str,
    text_font: ImageFont.ImageFont,
) -> int:
    """Draw icon + label centered on BAR_H. Return total width consumed."""
    mid_y = y + BAR_H // 2

    ib = icon_font.getbbox(glyph)
    icon_h = ib[3] - ib[1]
    icon_w = ib[2] - ib[0]
    ix = x + (BAR_ICON_BOX - icon_w) // 2 - ib[0]
    iy = mid_y - icon_h // 2 - ib[1]
    draw.text((ix, iy), glyph, font=icon_font, fill=0)

    tx = x + BAR_ICON_BOX + 3
    tb = draw.textbbox((0, 0), label, font=text_font)
    text_h = tb[3] - tb[1]
    ty = mid_y - text_h // 2
    draw.text((tx, ty), label, font=text_font, fill=0)

    return BAR_ICON_BOX + 3 + (tb[2] - tb[0])


def _draw_bottom_bar(
    draw: ImageDraw.ImageDraw,
    y: int,
    items: list[tuple[str, str]],
    icon_font: ImageFont.ImageFont,
    text_font: ImageFont.ImageFont,
) -> None:
    """Evenly space metric items across the full canvas width."""
    usable = CANVAS_WIDTH - 2 * MARGIN

    item_widths: list[int] = []
    for glyph, label in items:
        tb = draw.textbbox((0, 0), label, font=text_font)
        item_widths.append(BAR_ICON_BOX + 3 + (tb[2] - tb[0]))

    total_items_w = sum(item_widths)
    n = len(items)
    if n > 1 and total_items_w < usable:
        gap = (usable - total_items_w) // (n - 1)
    else:
        gap = 6

    x = MARGIN
    for (glyph, label), iw in zip(items, item_widths):
        _draw_bar_item(draw, x, y, glyph, icon_font, label, text_font)
        x += iw + gap


def weather_image(
    weather: CurrentWeather,
    *,
    location_label: str | None = None,
    display_tz: dt.tzinfo | None = None,
) -> Image.Image:
    w, h = CANVAS_WIDTH, CANVAS_HEIGHT
    image = Image.new("1", (w, h), 255)
    draw = ImageDraw.Draw(image)

    tz = display_tz or weather.fetched_at_utc.astimezone().tzinfo
    if tz is None:
        tz = dt.timezone.utc

    font_temp = _load_font(46)
    font_clock = _load_mono_font(44)
    font_date = _load_font(16)
    font_bar = _load_font(12)
    font_bar_mdi = mdi_font(BAR_ICON_PX)

    usable_w = w - 2 * MARGIN

    tc = round(weather.temperature_c)
    tf = round(weather.temperature_c * 9.0 / 5.0 + 32.0)
    temp_line = f"{tc}\u00b0C / {tf}\u00b0F"
    for fallback in (44, 42, 38):
        if _text_width(draw, temp_line, font_temp) <= usable_w:
            break
        font_temp = _load_font(fallback)

    now = dt.datetime.now(tz)
    time_s = now.strftime("%H:%M")
    date_s = now.strftime("%A, %d %b")
    if _text_width(draw, date_s, font_date) > usable_w:
        date_s = now.strftime("%a, %d %b")

    temp_h = _text_height(draw, temp_line, font_temp)
    clock_h = _text_height(draw, time_s, font_clock)
    date_h = _text_height(draw, date_s, font_date)

    gap_temp_clock = 14
    gap_clock_date = 8
    block_h = temp_h + gap_temp_clock + clock_h + gap_clock_date + date_h

    bar_y = h - MARGIN - BAR_H
    space_above_bar = bar_y - MARGIN
    y_start = MARGIN + max(0, (space_above_bar - block_h) // 3)

    def _cx(text: str, font: ImageFont.ImageFont) -> int:
        return MARGIN + (usable_w - _text_width(draw, text, font)) // 2

    y = y_start
    draw.text((_cx(temp_line, font_temp), y), temp_line, font=font_temp, fill=0)
    y += temp_h + gap_temp_clock

    draw.text((_cx(time_s, font_clock), y), time_s, font=font_clock, fill=0)
    y += clock_h + gap_clock_date

    draw.text((_cx(date_s, font_date), y), date_s, font=font_date, fill=0)

    bar_items: list[tuple[str, str]] = []
    if weather.apparent_temperature_c is not None:
        fc = round(weather.apparent_temperature_c)
        ff = round(weather.apparent_temperature_c * 9.0 / 5.0 + 32.0)
        bar_items.append((GLYPH_THERMOMETER, f"{fc}\u00b0/{ff}\u00b0"))
    if weather.relative_humidity_pct is not None:
        bar_items.append((GLYPH_WATER, f"{weather.relative_humidity_pct}%"))
    if weather.wind_speed_kmh is not None:
        bar_items.append((GLYPH_WIND, f"{round(weather.wind_speed_kmh)} km/h"))
    bar_items.append((GLYPH_REFRESH, _weather_age_label(weather.fetched_at_utc)))

    _draw_bottom_bar(draw, bar_y, bar_items, font_bar_mdi, font_bar)

    return image
