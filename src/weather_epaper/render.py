from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from weather_epaper.weather_client import CurrentWeather

# Match waveshare.epd2in7 vertical layout
CANVAS_WIDTH = 176
CANVAS_HEIGHT = 264


def weather_image(weather: CurrentWeather, *, location_label: str | None = None) -> Image.Image:
    image = Image.new("1", (CANVAS_WIDTH, CANVAS_HEIGHT), 255)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    y = 4
    line_h = 10

    title = location_label or "Weather"
    draw.text((4, y), title, font=font, fill=0)
    y += line_h + 6

    temp = f"{weather.temperature_c:.0f} C"
    draw.text((4, y), temp, font=font, fill=0)
    y += line_h + 2

    if weather.apparent_temperature_c is not None:
        draw.text((4, y), f"Feels {weather.apparent_temperature_c:.0f} C", font=font, fill=0)
        y += line_h + 2

    draw.text((4, y), weather.weather_label, font=font, fill=0)
    y += line_h + 4

    if weather.relative_humidity_pct is not None:
        draw.text((4, y), f"RH {weather.relative_humidity_pct}%", font=font, fill=0)
        y += line_h + 4

    updated = weather.fetched_at_utc.strftime("%Y-%m-%d %H:%MZ")
    draw.text((4, CANVAS_HEIGHT - line_h - 8), f"Upd {updated}", font=font, fill=0)

    return image
