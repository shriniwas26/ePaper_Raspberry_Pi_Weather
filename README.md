# Weather e-Paper Display

Weather station for a Waveshare 2.7" e-paper display on a Raspberry Pi. Shows temperature (C/F), clock, date, and key metrics at a glance.

![Display preview](docs/preview.png)

## Hardware

- Raspberry Pi (tested on Pi 4 / Pi 5 with Bookworm)
- Waveshare 2.7" B/W e-paper HAT (V2, SSD1680 controller)

## Features

- Temperature in Celsius and Fahrenheit
- Real-time clock updated on the minute
- Bottom bar with feels-like, humidity, wind speed, and last-updated time
- Weather data from [Open-Meteo](https://open-meteo.com/) (no API key required)
- Threaded architecture: weather fetching and display rendering run independently
- Automatic retry on API failure (3 attempts, 10s timeout)
- JSON history of the last 48 weather readings
- Graceful crash recovery (weather thread auto-restarts)

## Quick Start

```bash
# Install dependencies
uv sync

# Run with mock display (outputs PNG instead of driving hardware)
WEATHER_EPAPER_MOCK=1 uv run python -m weather_epaper.main --mock --once
```

## Deploy to Raspberry Pi

```bash
bash scripts/deploy.sh
ssh pi@raspi-epaper.local "bash ~/ePaper_Raspi/scripts/install-service.sh"
```

## Configuration

All settings are via environment variables (set in `deploy/weather-epaper.service`):

| Variable | Default | Description |
|---|---|---|
| `WEATHER_EPAPER_LAT` | `51.4416` | Latitude |
| `WEATHER_EPAPER_LON` | `5.4697` | Longitude |
| `WEATHER_EPAPER_TZ` | system tz | IANA timezone (e.g. `Europe/Amsterdam`) |
| `WEATHER_EPAPER_REFRESH_SEC` | `600` | Weather fetch interval (seconds) |
| `WEATHER_EPAPER_HISTORY_JSON` | `data/weather_history.json` | Path to history file |
| `WEATHER_EPAPER_MOCK` | unset | Set to `1` to write PNG instead of driving e-paper |

## Project Structure

```
src/weather_epaper/
  main.py            # Entry point, threading, display loop
  render.py          # PIL image generation for the e-paper layout
  device.py          # Hardware abstraction (real e-paper / mock PNG)
  config.py          # Settings from environment variables
  weather_client.py  # Open-Meteo API client with retry
  weather_history.py # JSON persistence for weather readings
  icons.py           # MDI icon glyph constants
fonts/               # Bundled TTF fonts (Roboto Bold)
third_party/waveshare/  # Vendored Waveshare driver
scripts/             # Deploy and service management scripts
deploy/              # systemd unit file
```
