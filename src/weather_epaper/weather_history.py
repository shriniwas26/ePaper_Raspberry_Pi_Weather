from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from weather_epaper.weather_client import CurrentWeather

logger = logging.getLogger(__name__)

MAX_ENTRIES = 5


def history_entry_from_weather(w: CurrentWeather) -> dict[str, Any]:
    """Rounded values as shown on the panel + ISO fetch time (UTC)."""
    tc = round(w.temperature_c)
    tf = round(w.temperature_f)
    return {
        "fetched_at_utc": w.fetched_at_utc.isoformat(),
        "temp_c": tc,
        "temp_f": tf,
        "weather_label": w.weather_label,
        "humidity_pct": w.relative_humidity_pct,
        "feels_c": (
            None if w.apparent_temperature_c is None else round(w.apparent_temperature_c)
        ),
        "wind_kmh": None if w.wind_speed_kmh is None else round(w.wind_speed_kmh),
    }


def load_weather_history(path: Path) -> list[dict[str, Any]]:
    """Return stored entries (newest first); empty if missing or invalid."""
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("Could not read weather history at %s", path)
        return []
    if not isinstance(raw, dict):
        return []
    entries = raw.get("entries")
    if not isinstance(entries, list):
        return []
    return [e for e in entries if isinstance(e, dict)]


def append_weather_history(path: Path, w: CurrentWeather) -> None:
    """Prepend a snapshot and keep at most `MAX_ENTRIES` (newest first)."""
    entry = history_entry_from_weather(w)
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = load_weather_history(path)
    entries.insert(0, entry)
    entries = entries[:MAX_ENTRIES]
    payload = {"entries": entries}
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
