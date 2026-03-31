from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import logging
import time

import httpx

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass(frozen=True)
class CurrentWeather:
    temperature_c: float
    apparent_temperature_c: float | None
    relative_humidity_pct: int | None
    wind_speed_kmh: float | None
    weather_label: str
    fetched_at_utc: datetime

    @property
    def temperature_f(self) -> float:
        return self.temperature_c * 9.0 / 5.0 + 32.0


# WMO Weather interpretation codes (subset for common conditions)
def _weather_code_label(code: int) -> str:
    if code == 0:
        return "Clear"
    if code in (1, 2, 3):
        return "Mainly clear"
    if code in (45, 48):
        return "Fog"
    if code in (51, 53, 55, 56, 57):
        return "Drizzle"
    if code in (61, 63, 65, 80, 81, 82):
        return "Rain"
    if code in (66, 67):
        return "Freezing rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "Snow"
    if code in (95, 96, 99):
        return "Thunderstorm"
    return f"Code {code}"


def fetch_current(
    latitude: float,
    longitude: float,
    *,
    timezone_name: str | None,
    timeout: float = 10.0,
    retries: int = 3,
    retry_delay: float = 2.0,
) -> CurrentWeather:
    params: dict[str, str] = {
        "latitude": str(latitude),
        "longitude": str(longitude),
        "current": ",".join(
            [
                "temperature_2m",
                "apparent_temperature",
                "relative_humidity_2m",
                "wind_speed_10m",
                "weather_code",
            ]
        ),
        "wind_speed_unit": "kmh",
    }
    if timezone_name:
        params["timezone"] = timezone_name
    else:
        params["timezone"] = "auto"

    for attempt in range(1, retries + 1):
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(OPEN_METEO_URL, params=params)
                response.raise_for_status()
                payload = response.json()
            break
        except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            if attempt < retries:
                logger.warning("Fetch attempt %d/%d failed: %s – retrying in %.1fs", attempt, retries, exc, retry_delay)
                time.sleep(retry_delay)
            else:
                logger.error("All %d fetch attempts failed", retries)
                raise

    current = payload["current"]
    api_tz_name = payload.get("timezone") or "UTC"
    try:
        api_tz = ZoneInfo(api_tz_name)
    except Exception:
        api_tz = timezone.utc

    time_str = current["time"]
    if time_str.endswith("Z"):
        fetched_at = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    else:
        fetched_at = datetime.fromisoformat(time_str)
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=api_tz)
    fetched_at_utc = fetched_at.astimezone(timezone.utc)

    code = int(current["weather_code"])
    label = _weather_code_label(code)

    return CurrentWeather(
        temperature_c=float(current["temperature_2m"]),
        apparent_temperature_c=(
            float(current["apparent_temperature"])
            if current.get("apparent_temperature") is not None
            else None
        ),
        relative_humidity_pct=(
            int(current["relative_humidity_2m"])
            if current.get("relative_humidity_2m") is not None
            else None
        ),
        wind_speed_kmh=(
            float(current["wind_speed_10m"])
            if current.get("wind_speed_10m") is not None
            else None
        ),
        weather_label=label,
        fetched_at_utc=fetched_at_utc,
    )
