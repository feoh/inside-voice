# pyright: reportMissingImports=false
from __future__ import annotations

from pathlib import Path

from inside_voice.config import Settings, clamp, load_settings, save_settings


def test_clamp_limits_values() -> None:
    if clamp(-100.0, -80.0, 0.0) != -80.0:
        raise AssertionError("clamp should limit low values")
    if clamp(10.0, -80.0, 0.0) != 0.0:
        raise AssertionError("clamp should limit high values")
    if clamp(-20.0, -80.0, 0.0) != -20.0:
        raise AssertionError("clamp should preserve in-range values")


def test_settings_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    original = Settings(
        threshold_db=-30.0,
        trigger_duration_s=0.7,
        cooldown_s=4.0,
        chime_volume=0.5,
    )

    save_settings(original, path)
    loaded = load_settings(path)

    if loaded != original:
        raise AssertionError("saved settings should load unchanged")
