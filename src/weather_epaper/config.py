from __future__ import annotations

import os
from dataclasses import dataclass


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return float(raw)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    latitude: float
    longitude: float
    timezone: str | None
    refresh_seconds: int
    mock_output_path: str
    mock: bool

    @classmethod
    def from_environ(cls, mock: bool) -> Settings:
        return cls(
            latitude=_env_float("WEATHER_EPAPER_LAT", 40.7128),
            longitude=_env_float("WEATHER_EPAPER_LON", -74.0060),
            timezone=os.environ.get("WEATHER_EPAPER_TZ") or None,
            refresh_seconds=_env_int("WEATHER_EPAPER_REFRESH_SEC", 1800),
            mock_output_path=os.environ.get("WEATHER_EPAPER_MOCK_OUTPUT", "out/preview.png"),
            mock=mock,
        )


def truthy_env(name: str) -> bool:
    return os.environ.get(name, "").lower() in ("1", "true", "yes")
