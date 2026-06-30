"""Audio capture, level detection, and chime playback."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from threading import Lock, Thread
from typing import Any

import numpy as np

DB_FLOOR = -80.0
DB_CEILING = 0.0


@dataclass(slots=True)
class LevelState:
    """Current microphone level state."""

    db: float = DB_FLOOR
    last_error: str | None = None
    input_status: str | None = None


class TriggerDetector:
    """Detect over-threshold audio with cooldown.

    The first transition from quiet to loud triggers immediately. If the level
    remains loud, additional chimes are allowed only after both the sustain
    duration and cooldown have elapsed.
    """

    def __init__(self) -> None:
        self._over_since: float | None = None
        self._last_triggered_at = -math.inf
        self._was_over_threshold = False

    def update(
        self,
        *,
        level_db: float,
        threshold_db: float,
        trigger_duration_s: float,
        cooldown_s: float,
        now: float | None = None,
    ) -> bool:
        """Return True when the loudness condition should trigger a chime."""

        now = time.monotonic() if now is None else now
        if level_db < threshold_db:
            self._over_since = None
            self._was_over_threshold = False
            return False

        crossed_threshold = not self._was_over_threshold
        self._was_over_threshold = True
        if self._over_since is None:
            self._over_since = now

        cooled_down = now - self._last_triggered_at >= cooldown_s
        if crossed_threshold and cooled_down:
            self._last_triggered_at = now
            return True

        loud_long_enough = now - self._over_since >= trigger_duration_s
        if loud_long_enough and cooled_down:
            self._last_triggered_at = now
            return True
        return False


class AudioMonitor:
    """Monitor microphone input and expose a smoothed dBFS level."""

    def __init__(
        self,
        *,
        input_device: str | int | None = None,
        smoothing: float = 0.25,
        blocksize: int = 1024,
    ) -> None:
        self.input_device = input_device
        self.smoothing = smoothing
        self.blocksize = blocksize
        self._state = LevelState()
        self._lock = Lock()
        self._stream: Any | None = None
        self._initialized = False

    def start(self) -> None:
        """Start microphone capture."""

        import sounddevice as sd

        stream = sd.InputStream(
            device=self.input_device,
            channels=1,
            blocksize=self.blocksize,
            callback=self._audio_callback,
        )
        stream.start()
        self._stream = stream

    def stop(self) -> None:
        """Stop microphone capture."""

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def get_state(self) -> LevelState:
        """Return a copy of the current state."""

        with self._lock:
            return LevelState(
                db=self._state.db,
                last_error=self._state.last_error,
                input_status=self._state.input_status,
            )

    def _audio_callback(
        self,
        indata: np.ndarray[Any, np.dtype[np.floating[Any]]],
        _frames: int,
        _time_info: Any,
        status: Any,
    ) -> None:
        try:
            db = rms_dbfs(indata)
            with self._lock:
                if not self._initialized:
                    self._state.db = db
                    self._initialized = True
                else:
                    self._state.db = smooth_db(self._state.db, db, self.smoothing)
                self._state.input_status = str(status) if status else None
                self._state.last_error = None
        except (FloatingPointError, ValueError) as exc:
            with self._lock:
                self._state.last_error = str(exc)


class ChimePlayer:
    """Play a short generated chime on the local output device."""

    def __init__(self, *, samplerate: int = 44_100) -> None:
        self.samplerate = samplerate
        self._lock = Lock()
        self.last_error: str | None = None

    def play(self, *, volume: float) -> bool:
        """Play the chime asynchronously.

        Returns True when playback was queued. Any playback error is captured in
        ``last_error`` so the TUI can make silent failures visible.
        """

        if volume <= 0:
            return False
        thread = Thread(target=self._play_blocking, kwargs={"volume": volume}, daemon=True)
        thread.start()
        return True

    def _play_blocking(self, *, volume: float) -> None:
        import sounddevice as sd

        audio = make_chime(volume=volume, samplerate=self.samplerate)
        with self._lock:
            try:
                sd.play(audio, samplerate=self.samplerate, blocking=True)
            except Exception as exc:  # noqa: BLE001 - audio backends raise environment-specific errors.
                self.last_error = str(exc)
            else:
                self.last_error = None


def rms_dbfs(samples: np.ndarray[Any, np.dtype[np.floating[Any]]]) -> float:
    """Convert input samples in the -1.0..1.0 range to dBFS."""

    if samples.size == 0:
        return DB_FLOOR
    try:
        rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
    except FloatingPointError, TypeError, ValueError:
        return DB_FLOOR
    if rms <= 0:
        return DB_FLOOR
    return max(DB_FLOOR, min(DB_CEILING, 20.0 * math.log10(rms)))


def smooth_db(previous_db: float, current_db: float, smoothing: float) -> float:
    """Exponential moving average for dB readings."""

    smoothing = max(0.0, min(1.0, smoothing))
    return (previous_db * (1.0 - smoothing)) + (current_db * smoothing)


def make_chime(*, volume: float, samplerate: int) -> np.ndarray[Any, np.dtype[np.float32]]:
    """Generate a distinctive two-tone chime."""

    volume = max(0.0, min(1.0, volume))
    first = _tone(frequency=880.0, duration_s=0.11, samplerate=samplerate)
    gap = np.zeros(_sample_count(samplerate=samplerate, duration_s=0.035), dtype=np.float32)
    second = _tone(frequency=1_320.0, duration_s=0.16, samplerate=samplerate)
    return np.concatenate([first, gap, second]) * np.float32(volume)


def _tone(
    *, frequency: float, duration_s: float, samplerate: int
) -> np.ndarray[Any, np.dtype[np.float32]]:
    sample_count = _sample_count(samplerate=samplerate, duration_s=duration_s)
    t = np.linspace(0.0, duration_s, sample_count, endpoint=False, dtype=np.float32)
    wave = np.sin(2.0 * np.pi * frequency * t).astype(np.float32)
    fade_len = _sample_count(samplerate=samplerate, duration_s=0.01)
    fade_in = np.linspace(0.0, 1.0, fade_len, dtype=np.float32)
    fade_out = np.linspace(1.0, 0.0, fade_len, dtype=np.float32)
    wave[:fade_len] *= fade_in
    wave[-fade_len:] *= fade_out
    return wave


def list_input_devices() -> list[str]:
    """Return human-readable audio input device descriptions."""

    import sounddevice as sd

    devices = sd.query_devices()
    default_input = sd.default.device[0]
    lines: list[str] = []
    for index, device in enumerate(devices):
        max_inputs = _safe_int(device.get("max_input_channels", 0))
        if max_inputs <= 0:
            continue
        marker = "*" if index == default_input else " "
        name = device.get("name", "unknown")
        hostapi = sd.query_hostapis(device.get("hostapi", 0)).get("name", "unknown")
        lines.append(f"{marker} {index}: {name} ({hostapi}, {max_inputs} input channels)")
    return lines


def _sample_count(*, samplerate: int, duration_s: float) -> int:
    try:
        return max(1, int(float(samplerate) * duration_s))
    except TypeError, ValueError:
        return 1


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except TypeError, ValueError:
        return 0
