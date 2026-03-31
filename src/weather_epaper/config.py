from __future__ import annotations

import datetime as dt
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("Invalid float for %s=%r, using default %s", name, raw, default)
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid int for %s=%r, using default %s", name, raw, default)
        return default


def resolve_display_tz(zone_name: str | None) -> dt.tzinfo:
    """IANA zone from WEATHER_EPAPER_TZ, else the process/system local zone (e.g. Pi /etc/localtime)."""
    if zone_name:
        try:
            return ZoneInfo(zone_name)
        except Exception:
            logger.warning("Invalid timezone %r, falling back to system local", zone_name)
    local = datetime.now().astimezone().tzinfo
    return local if local is not None else dt.UTC


def _weather_poll_seconds() -> int:
    """Open-Meteo fetch interval (unchanged env: WEATHER_EPAPER_REFRESH_SEC)."""
    if (w := os.environ.get("WEATHER_EPAPER_WEATHER_SEC")) is not None and w != "":
        return int(w)
    return _env_int("WEATHER_EPAPER_REFRESH_SEC", 600)


@dataclass(frozen=True)
class Settings:
    latitude: float
    longitude: float
    timezone: str | None
    weather_refresh_seconds: int
    mock_output_path: str
    weather_history_path: str
    mock: bool
    display_tz: dt.tzinfo

    @classmethod
    def from_environ(cls, mock: bool) -> Settings:
        tz_opt = os.environ.get("WEATHER_EPAPER_TZ") or None
        return cls(
            latitude=_env_float("WEATHER_EPAPER_LAT", 51.4416),
            longitude=_env_float("WEATHER_EPAPER_LON", 5.4697),
            timezone=tz_opt,
            weather_refresh_seconds=max(1, _weather_poll_seconds()),
            mock_output_path=os.environ.get("WEATHER_EPAPER_MOCK_OUTPUT", "out/preview.png"),
            weather_history_path=os.environ.get(
                "WEATHER_EPAPER_HISTORY_JSON",
                "data/weather_history.json",
            ),
            mock=mock,
            display_tz=resolve_display_tz(tz_opt),
        )


def truthy_env(name: str) -> bool:
    return os.environ.get(name, "").lower() in ("1", "true", "yes")
