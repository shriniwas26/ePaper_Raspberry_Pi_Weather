from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpx

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass(frozen=True)
class CurrentWeather:
    temperature_c: float
    apparent_temperature_c: float | None
    relative_humidity_pct: int | None
    weather_label: str
    fetched_at_utc: datetime


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
    timeout: float = 30.0,
) -> CurrentWeather:
    params: dict[str, str] = {
        "latitude": str(latitude),
        "longitude": str(longitude),
        "current": ",".join(
            [
                "temperature_2m",
                "apparent_temperature",
                "relative_humidity_2m",
                "weather_code",
            ]
        ),
    }
    if timezone_name:
        params["timezone"] = timezone_name

    with httpx.Client(timeout=timeout) as client:
        response = client.get(OPEN_METEO_URL, params=params)
        response.raise_for_status()
        payload = response.json()

    current = payload["current"]
    tz = timezone_name or payload.get("timezone") or "UTC"
    try:
        zi = ZoneInfo(tz)
    except Exception:
        zi = timezone.utc

    time_str = current["time"]
    fetched_at = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=zi)
    else:
        fetched_at = fetched_at.astimezone(timezone.utc)

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
        weather_label=label,
        fetched_at_utc=fetched_at,
    )
