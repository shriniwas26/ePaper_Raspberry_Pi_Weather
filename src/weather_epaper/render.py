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
SPLIT_X = 156
MARGIN = 5
ICON_BOX = 20
ICON_MDI_PX = 19
ROW_H = 24

def _right_panel_fonts() -> tuple[
    ImageFont.FreeTypeFont | ImageFont.ImageFont,
    ImageFont.FreeTypeFont | ImageFont.ImageFont,
    ImageFont.FreeTypeFont | ImageFont.ImageFont,
]:
    return (
        _load_font(16),
        _load_font(14),
        _load_mono_font(32),
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
    mid_y = y + ROW_H // 2
    tb = draw.textbbox((0, 0), label, font=font)
    text_h = tb[3] - tb[1]
    ty = mid_y - text_h // 2

    ib = icon_font.getbbox(glyph)
    icon_h = ib[3] - ib[1]
    icon_w = ib[2] - ib[0]
    ix = x_icon + (ICON_BOX - icon_w) // 2 - ib[0]
    iy = mid_y - icon_h // 2 - ib[1]
    draw.text((ix, iy), glyph, font=icon_font, fill=0)

    tx = x_icon + ICON_BOX + 4
    draw.text((tx, ty), label, font=font, fill=0)


def _draw_right_panel(
    draw: ImageDraw.ImageDraw,
    *,
    split_x: int,
    canvas_w: int,
    canvas_h: int,
    display_tz: dt.tzinfo,
    location_label: str,
    font_location: ImageFont.ImageFont,
    font_weekday: ImageFont.ImageFont,
    font_date: ImageFont.ImageFont,
    font_time: ImageFont.ImageFont,
) -> None:
    now = dt.datetime.now(display_tz)
    weekday = now.strftime("%A")
    date_s = now.strftime("%d %b")
    time_s = now.strftime("%H:%M")

    x0 = split_x + MARGIN
    x1 = canvas_w - MARGIN
    y0 = MARGIN
    y1 = canvas_h - MARGIN
    inner_w = x1 - x0
    inner_h = y1 - y0

    location = _truncate_to_width(draw, location_label, font_location, inner_w)
    if _text_width(draw, weekday, font_weekday) > inner_w:
        weekday = now.strftime("%a")

    loc_h = _text_height(draw, location, font_location)
    d_h = _text_height(draw, weekday, font_weekday)
    dt_h = _text_height(draw, date_s, font_date)
    tm_h = _text_height(draw, time_s, font_time)
    gap = 3
    gap2 = 5
    block_h = loc_h + gap + d_h + gap + dt_h + gap2 + tm_h
    y_c = y0 + max(0, (inner_h - block_h) // 2)

    def _cx(text: str, font: ImageFont.ImageFont) -> int:
        return x0 + (inner_w - _text_width(draw, text, font)) // 2

    draw.text((_cx(location, font_location), y_c), location, font=font_location, fill=0)
    y_c += loc_h + gap
    draw.text((_cx(weekday, font_weekday), y_c), weekday, font=font_weekday, fill=0)
    y_c += d_h + gap
    draw.text((_cx(date_s, font_date), y_c), date_s, font=font_date, fill=0)
    y_c += dt_h + gap2
    draw.text((_cx(time_s, font_time), y_c), time_s, font=font_time, fill=0)


def weather_image(
    weather: CurrentWeather,
    *,
    location_label: str | None = None,
    display_tz: dt.tzinfo | None = None,
) -> Image.Image:
    w, h = CANVAS_WIDTH, CANVAS_HEIGHT
    image = Image.new("1", (w, h), 255)
    draw = ImageDraw.Draw(image)

    font_temp = _load_font(28)
    font_cond = _load_font(16)
    font_metric = _load_font(14)
    font_ago = _load_font(12)
    font_mdi = mdi_font(ICON_MDI_PX)
    font_weekday, font_rdate, font_rtime = _right_panel_fonts()

    lx = MARGIN
    left_max = SPLIT_X - 2 * MARGIN
    y = MARGIN

    tc = round(weather.temperature_c)
    tf = round(weather.temperature_c * 9.0 / 5.0 + 32.0)
    temp_line = f"{tc}\u00b0C / {tf}\u00b0F"
    for fallback in (26, 24):
        if _text_width(draw, temp_line, font_temp) <= left_max:
            break
        font_temp = _load_font(fallback)
    draw.text((lx, y), temp_line, font=font_temp, fill=0)
    y += _text_height(draw, temp_line, font_temp) + 10

    cond = _truncate_to_width(draw, weather.weather_label, font_cond, left_max)
    draw.text((lx, y), cond, font=font_cond, fill=0)
    y += _text_height(draw, cond, font_cond) + 8

    if weather.apparent_temperature_c is not None:
        fc = round(weather.apparent_temperature_c)
        ff = round(weather.apparent_temperature_c * 9.0 / 5.0 + 32.0)
        _draw_metric_row(
            draw, lx, y, GLYPH_THERMOMETER, font_mdi,
            f"{fc}\u00b0C / {ff}\u00b0F", font_metric,
        )
        y += ROW_H
    if weather.relative_humidity_pct is not None:
        _draw_metric_row(
            draw, lx, y, GLYPH_WATER, font_mdi,
            f"{weather.relative_humidity_pct}%", font_metric,
        )
        y += ROW_H
    if weather.wind_speed_kmh is not None:
        wk = round(weather.wind_speed_kmh)
        _draw_metric_row(
            draw, lx, y, GLYPH_WIND, font_mdi,
            f"{wk} km/h", font_metric,
        )
        y += ROW_H

    ago_s = _weather_age_label(weather.fetched_at_utc)
    _draw_metric_row(draw, lx, y, GLYPH_REFRESH, font_mdi, ago_s, font_ago)

    tz = display_tz or weather.fetched_at_utc.astimezone().tzinfo
    if tz is None:
        tz = dt.timezone.utc
    font_loc = _load_font(11)
    _draw_right_panel(
        draw,
        split_x=SPLIT_X,
        canvas_w=w,
        canvas_h=h,
        display_tz=tz,
        location_label=(location_label or "").strip(),
        font_location=font_loc,
        font_weekday=font_weekday,
        font_date=font_rdate,
        font_time=font_rtime,
    )

    return image
