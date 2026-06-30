# pyright: reportMissingImports=false
from __future__ import annotations

from inside_voice.app import render_meter


def test_render_meter_includes_threshold_label() -> None:
    rendered = render_meter(level_db=-35.0, threshold_db=-25.0)

    if "threshold -25 dB" not in rendered.plain:
        raise AssertionError("meter should include threshold label")
    if "▲" not in rendered.plain:
        raise AssertionError("meter should include threshold marker")
