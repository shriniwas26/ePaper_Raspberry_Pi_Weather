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
SPLIT_X = CANVAS_WIDTH // 2
HEADER_H = 0
ICON_BOX = 16
ICON_MDI_PX = 15  # Material Design Icons in the 16px cell
ROW_H = 22
LEFT_PAD = 8
RIGHT_PAD = 6

def _right_panel_fonts() -> tuple[
    ImageFont.FreeTypeFont | ImageFont.ImageFont,
    ImageFont.FreeTypeFont | ImageFont.ImageFont,
    ImageFont.FreeTypeFont | ImageFont.ImageFont,
]:
    return (
        _load_font(14),
        _load_font(13),
        _load_mono_font(36),
    )


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


def _truncate_to_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_w: int,
) -> str:
    if _text_width(draw, text, font) <= max_w:
        return text
    ell = "..."
    while len(text) > 1:
        text = text[:-1]
        candidate = text + ell
        if _text_width(draw, candidate, font) <= max_w:
            return candidate
    return ell


def _weather_age_label(fetched_at_utc: dt.datetime) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    ft = fetched_at_utc.astimezone(dt.timezone.utc)
    secs = int(max(0, (now - ft).total_seconds()))
    if secs < 45:
        return "just now"
    mins = (secs + 30) // 60
    if mins == 1:
        return "1 minute"
    return f"{mins} minutes"


def _draw_mdi_in_box(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    glyph: str,
    font: ImageFont.ImageFont,
    box: int = ICON_BOX,
) -> None:
    bbox = font.getbbox(glyph)
    gw = bbox[2] - bbox[0]
    gh = bbox[3] - bbox[1]
    tx = x + (box - gw) // 2 - bbox[0]
    ty = y + (box - gh) // 2 - bbox[1]
    draw.text((tx, ty), glyph, font=font, fill=0)


def _draw_metric_row(
    draw: ImageDraw.ImageDraw,
    x_icon: int,
    y: int,
    glyph: str,
    icon_font: ImageFont.ImageFont,
    label: str,
    font: ImageFont.ImageFont,
) -> None:
    iy = y + max(0, (ROW_H - ICON_BOX) // 2)
    _draw_mdi_in_box(draw, x_icon, iy, glyph, icon_font)
    tx = x_icon + ICON_BOX + 5
    ty = y + (ROW_H - _text_height(draw, label, font)) // 2
    draw.text((tx, ty), label, font=font, fill=0)


def _draw_right_panel(
    draw: ImageDraw.ImageDraw,
    *,
    split_x: int,
    canvas_w: int,
    canvas_h: int,
    display_tz: dt.tzinfo,
    font_weekday: ImageFont.ImageFont,
    font_date: ImageFont.ImageFont,
    font_time: ImageFont.ImageFont,
) -> None:
    now = dt.datetime.now(display_tz)
    weekday = now.strftime("%A")
    date_s = now.strftime("%d %b")
    time_s = now.strftime("%H:%M")

    inner_x0 = split_x + RIGHT_PAD
    inner_x1 = canvas_w - RIGHT_PAD
    inner_y0 = HEADER_H + RIGHT_PAD
    inner_y1 = canvas_h - RIGHT_PAD
    inner_w = inner_x1 - inner_x0
    inner_h = inner_y1 - inner_y0

    rw = inner_w - 8
    if _text_width(draw, weekday, font_weekday) > rw:
        weekday = now.strftime("%a")

    d_h = _text_height(draw, weekday, font_weekday)
    dt_h = _text_height(draw, date_s, font_date)
    tm_h = _text_height(draw, time_s, font_time)
    gap = 4
    gap2 = 6
    block_h = d_h + gap + dt_h + gap2 + tm_h
    y_c = inner_y0 + max(0, (inner_h - block_h) // 2)

    draw.text((inner_x0 + (inner_w - _text_width(draw, weekday, font_weekday)) // 2, y_c), weekday, font=font_weekday, fill=0)
    y_c += d_h + gap
    draw.text((inner_x0 + (inner_w - _text_width(draw, date_s, font_date)) // 2, y_c), date_s, font=font_date, fill=0)
    y_c += dt_h + gap2
    draw.text((inner_x0 + (inner_w - _text_width(draw, time_s, font_time)) // 2, y_c), time_s, font=font_time, fill=0)


def weather_image(
    weather: CurrentWeather,
    *,
    location_label: str | None = None,
    display_tz: dt.tzinfo | None = None,
) -> Image.Image:
    w, h = CANVAS_WIDTH, CANVAS_HEIGHT
    image = Image.new("1", (w, h), 255)
    draw = ImageDraw.Draw(image)

    font_hero = _load_font(34)
    font_cond = _load_font(14)
    font_metric = _load_font(12)
    font_weekday, font_rdate, font_rtime = _right_panel_fonts()
    font_ago = _load_font(10)
    font_mdi = mdi_font(ICON_MDI_PX)

    draw.line((SPLIT_X, 0, SPLIT_X, h - 1), fill=0, width=1)

    left_max = SPLIT_X - LEFT_PAD - 4
    y = LEFT_PAD
    tc = round(weather.temperature_c)
    tf = round(weather.temperature_c * 9.0 / 5.0 + 32.0)
    temp_line = f"{tc}C / {tf} F"
    font_temp = font_hero
    if _text_width(draw, temp_line, font_temp) > left_max:
        font_temp = _load_font(26)
    if _text_width(draw, temp_line, font_temp) > left_max:
        font_temp = _load_font(22)
    draw.text((LEFT_PAD, y), temp_line, font=font_temp, fill=0)
    th = _text_height(draw, temp_line, font_temp)

    y += max(th, 28) + 2
    cond = _truncate_to_width(draw, weather.weather_label, font_cond, left_max)
    draw.text((LEFT_PAD, y), cond, font=font_cond, fill=0)
    y += _text_height(draw, cond, font_cond) + 6

    if weather.relative_humidity_pct is not None:
        _draw_metric_row(
            draw,
            LEFT_PAD,
            y,
            GLYPH_WATER,
            font_mdi,
            f"{weather.relative_humidity_pct}%",
            font_metric,
        )
        y += ROW_H
    if weather.apparent_temperature_c is not None:
        _draw_metric_row(
            draw,
            LEFT_PAD,
            y,
            GLYPH_THERMOMETER,
            font_mdi,
            f"{weather.apparent_temperature_c:.0f} C feels",
            font_metric,
        )
        y += ROW_H
    if weather.wind_speed_kmh is not None:
        wk = round(weather.wind_speed_kmh)
        _draw_metric_row(
            draw,
            LEFT_PAD,
            y,
            GLYPH_WIND,
            font_mdi,
            f"{wk} km/h wind",
            font_metric,
        )
        y += ROW_H

    ago_s = _weather_age_label(weather.fetched_at_utc)
    _draw_metric_row(
        draw,
        LEFT_PAD,
        y,
        GLYPH_REFRESH,
        font_mdi,
        ago_s,
        font_ago,
    )

    tz = display_tz or weather.fetched_at_utc.astimezone().tzinfo
    if tz is None:
        tz = dt.timezone.utc
    _draw_right_panel(
        draw,
        split_x=SPLIT_X,
        canvas_w=w,
        canvas_h=h,
        display_tz=tz,
        font_weekday=font_weekday,
        font_date=font_rdate,
        font_time=font_rtime,
    )

    return image
