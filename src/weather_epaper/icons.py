from __future__ import annotations

from functools import cache

from fonticon_mdi6 import MDI6
from PIL import ImageFont


def mdi_char(mdi_attr: str) -> str:
    """`fonticon_mdi6` stores values as ``'mdi6.<char>'``; return the single codepoint."""
    _prefix, ch = mdi_attr.split(".", 1)
    return ch


@cache
def mdi_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(MDI6.__font_file__, size)
    except OSError:
        return ImageFont.load_default()


# Glyphs used on the weather / clock layout (MaterialDesignIcons v6).
GLYPH_WATER = mdi_char(MDI6.water)
GLYPH_THERMOMETER = mdi_char(MDI6.thermometer)
GLYPH_WIND = mdi_char(MDI6.weather_windy)
GLYPH_REFRESH = mdi_char(MDI6.refresh)
