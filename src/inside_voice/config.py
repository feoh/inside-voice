"""Configuration persistence for inside-voice."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir

APP_NAME = "inside-voice"
CONFIG_FILE = "settings.json"


@dataclass(slots=True)
class Settings:
    """User-adjustable application settings."""

    threshold_db: float = -25.0
    trigger_duration_s: float = 0.4
    immediate_first_chime: bool = True
    cooldown_s: float = 3.0
    chime_volume: float = 0.35
    muted: bool = False
    input_device: str | int | None = None


def config_path() -> Path:
    """Return the settings file path for the current platform."""

    return Path(user_config_dir(APP_NAME, appauthor=False)) / CONFIG_FILE


def load_settings(path: Path | None = None) -> Settings:
    """Load settings, returning defaults when no config exists."""

    path = path or config_path()
    if not path.exists():
        return Settings()

    try:
        raw = json.loads(path.read_text())
    except OSError, json.JSONDecodeError:
        return Settings()

    allowed = {field.name for field in fields(Settings)}
    kwargs: dict[str, Any] = {key: value for key, value in raw.items() if key in allowed}
    settings = Settings(**kwargs)
    settings.threshold_db = clamp(settings.threshold_db, -80.0, 0.0)
    settings.trigger_duration_s = clamp(settings.trigger_duration_s, 0.1, 2.0)
    settings.cooldown_s = clamp(settings.cooldown_s, 0.5, 10.0)
    settings.chime_volume = clamp(settings.chime_volume, 0.0, 1.0)
    return settings


def save_settings(settings: Settings, path: Path | None = None) -> Path:
    """Persist settings and return the path written."""

    target = (path or config_path()).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(settings), indent=2, sort_keys=True) + "\n")
    return target


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp a float into an inclusive range."""

    try:
        number = float(value)
    except TypeError, ValueError:
        return minimum
    return max(minimum, min(maximum, number))
