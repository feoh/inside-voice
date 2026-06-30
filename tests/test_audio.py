# pyright: reportMissingImports=false
from __future__ import annotations

import numpy as np

from inside_voice.audio import (
    DB_FLOOR,
    TriggerDetector,
    make_chime,
    rms_dbfs,
    smooth_db,
)


def test_rms_dbfs_returns_floor_for_silence() -> None:
    samples = np.zeros((128, 1), dtype=np.float32)

    if rms_dbfs(samples) != DB_FLOOR:
        raise AssertionError("silence should report the dB floor")


def test_rms_dbfs_reports_expected_full_scale_value() -> None:
    samples = np.ones((128, 1), dtype=np.float32) * 0.5

    if not -6.1 < rms_dbfs(samples) < -5.9:
        raise AssertionError("0.5 amplitude should be about -6 dBFS")


def test_smooth_db_moves_toward_current_value() -> None:
    if smooth_db(-80.0, -20.0, 0.25) != -65.0:
        raise AssertionError("smoothed value should move toward current level")


def test_trigger_detector_chimes_on_threshold_crossing_then_uses_cooldown() -> None:
    detector = TriggerDetector()

    first = detector.update(
        level_db=-20.0,
        threshold_db=-30.0,
        trigger_duration_s=0.5,
        cooldown_s=1.0,
        now=0.0,
    )
    second = detector.update(
        level_db=-20.0,
        threshold_db=-30.0,
        trigger_duration_s=0.5,
        cooldown_s=1.0,
        now=0.4,
    )
    third = detector.update(
        level_db=-20.0,
        threshold_db=-30.0,
        trigger_duration_s=0.5,
        cooldown_s=1.0,
        now=0.6,
    )
    fourth = detector.update(
        level_db=-20.0,
        threshold_db=-30.0,
        trigger_duration_s=0.5,
        cooldown_s=1.0,
        now=1.0,
    )
    fifth = detector.update(
        level_db=-20.0,
        threshold_db=-30.0,
        trigger_duration_s=0.5,
        cooldown_s=1.0,
        now=1.7,
    )
    if [first, second, third, fourth, fifth] != [True, False, False, True, False]:
        raise AssertionError("detector should chime on crossing, then respect cooldown")


def test_trigger_detector_can_wait_for_sustained_loudness_before_first_chime() -> None:
    detector = TriggerDetector()

    first = detector.update(
        level_db=-20.0,
        threshold_db=-30.0,
        trigger_duration_s=0.5,
        cooldown_s=1.0,
        immediate_first_chime=False,
        now=0.0,
    )
    second = detector.update(
        level_db=-20.0,
        threshold_db=-30.0,
        trigger_duration_s=0.5,
        cooldown_s=1.0,
        immediate_first_chime=False,
        now=0.4,
    )
    third = detector.update(
        level_db=-20.0,
        threshold_db=-30.0,
        trigger_duration_s=0.5,
        cooldown_s=1.0,
        immediate_first_chime=False,
        now=0.6,
    )
    if [first, second, third] != [False, False, True]:
        raise AssertionError("sustained mode should wait before the first chime")


def test_trigger_detector_rearms_after_returning_below_threshold() -> None:
    detector = TriggerDetector()

    first = detector.update(
        level_db=-20.0,
        threshold_db=-30.0,
        trigger_duration_s=0.5,
        cooldown_s=1.0,
        now=0.0,
    )
    below = detector.update(
        level_db=-40.0,
        threshold_db=-30.0,
        trigger_duration_s=0.5,
        cooldown_s=1.0,
        now=1.1,
    )
    second = detector.update(
        level_db=-20.0,
        threshold_db=-30.0,
        trigger_duration_s=0.5,
        cooldown_s=1.0,
        now=1.2,
    )
    if [first, below, second] != [True, False, True]:
        raise AssertionError("detector should re-arm after the level drops below threshold")


def test_make_chime_generates_audio() -> None:
    chime = make_chime(volume=0.5, samplerate=44_100)

    if chime.dtype != np.float32:
        raise AssertionError("chime should use float32 samples")
    if chime.size <= 0:
        raise AssertionError("chime should contain samples")
    if np.max(np.abs(chime)) > np.float32(0.5):
        raise AssertionError("chime peak should not exceed requested volume")
