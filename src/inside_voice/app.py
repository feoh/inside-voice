# pyright: reportMissingImports=false
"""Textual application for inside-voice."""

from __future__ import annotations

import time

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Footer, Header, Static

from .audio import DB_FLOOR, AudioMonitor, ChimePlayer, TriggerDetector
from .config import Settings, clamp, save_settings
from .widgets import ValueSlider


class InsideVoiceApp(App[None]):
    """A TUI that reminds you to keep your voice down."""

    CSS = """
    Screen {
        align: center middle;
    }
    #panel {
        width: 90%;
        max-width: 100;
        border: round $primary;
        padding: 1 2;
    }
    #title {
        text-style: bold;
        margin-bottom: 1;
    }
    #level {
        margin-top: 1;
    }
    #meter {
        margin: 1 0;
    }
    #status {
        margin-bottom: 1;
    }
    #help {
        margin-top: 1;
        color: $text-muted;
    }
    .error {
        color: red;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("m", "toggle_mute", "Mute chime"),
        ("c", "calibrate", "Calibrate"),
    ]

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings
        self.monitor = AudioMonitor(input_device=settings.input_device)
        self.detector = TriggerDetector()
        self.chime = ChimePlayer()
        self._last_chime_at: float | None = None
        self._audio_started = False

    def compose(self) -> ComposeResult:
        """Compose the UI."""

        yield Header(show_clock=True)
        with Container(id="panel"):
            yield Static("inside-voice", id="title")
            yield Static("Starting microphone monitor…", id="level")
            yield Static("", id="meter")
            yield Static("", id="status")
            yield ValueSlider(
                "Threshold",
                minimum=DB_FLOOR,
                maximum=0.0,
                value=self.settings.threshold_db,
                step=1.0,
                unit=" dB",
                precision=0,
                id="threshold",
            )
            yield ValueSlider(
                "Repeat sustain",
                minimum=0.1,
                maximum=2.0,
                value=self.settings.trigger_duration_s,
                step=0.1,
                unit=" s",
                precision=1,
                id="trigger",
            )
            yield ValueSlider(
                "Cooldown",
                minimum=0.5,
                maximum=10.0,
                value=self.settings.cooldown_s,
                step=0.5,
                unit=" s",
                precision=1,
                id="cooldown",
            )
            yield ValueSlider(
                "Chime volume",
                minimum=0.0,
                maximum=100.0,
                value=self.settings.chime_volume * 100.0,
                step=5.0,
                unit="%",
                precision=0,
                id="volume",
            )
            yield Static(
                "Keys: q quit • m mute/unmute • c calibrate • arrows adjust focused slider",
                id="help",
            )
        yield Footer()

    def on_mount(self) -> None:
        """Start audio and UI refresh timers."""

        try:
            self.monitor.start()
            self._audio_started = True
        except Exception as exc:  # noqa: BLE001 - display device/PortAudio failures in the TUI.
            self.query_one("#status", Static).update(Text(f"Audio error: {exc}", style="red"))
        self.set_interval(0.1, self.refresh_audio_state)

    def on_unmount(self) -> None:
        """Stop audio when the app exits."""

        if self._audio_started:
            self.monitor.stop()
        save_settings(self.settings)

    def on_value_slider_changed(self, event: ValueSlider.Changed) -> None:
        """Persist setting changes from sliders."""

        slider_id = event.slider.id
        if slider_id == "threshold":
            self.settings.threshold_db = event.value
        elif slider_id == "trigger":
            self.settings.trigger_duration_s = event.value
        elif slider_id == "cooldown":
            self.settings.cooldown_s = event.value
        elif slider_id == "volume":
            self.settings.chime_volume = event.value / 100.0
        save_settings(self.settings)

    def action_toggle_mute(self) -> None:
        """Toggle audible chime playback."""

        self.settings.muted = not self.settings.muted
        save_settings(self.settings)
        self.refresh_audio_state()

    def action_calibrate(self) -> None:
        """Set threshold slightly above the current mic level."""

        current_db = self.monitor.get_state().db
        threshold = clamp(current_db + 6.0, DB_FLOOR, 0.0)
        self.settings.threshold_db = threshold
        self.query_one("#threshold", ValueSlider).set_value(threshold)
        save_settings(self.settings)
        self.notify(f"Threshold calibrated to {threshold:.0f} dB")

    def refresh_audio_state(self) -> None:
        """Refresh meter/status and play chime when appropriate."""

        state = self.monitor.get_state()
        level = state.db
        too_loud = level >= self.settings.threshold_db
        should_chime = self.detector.update(
            level_db=level,
            threshold_db=self.settings.threshold_db,
            trigger_duration_s=self.settings.trigger_duration_s,
            cooldown_s=self.settings.cooldown_s,
        )
        if (
            should_chime
            and not self.settings.muted
            and self.chime.play(volume=self.settings.chime_volume)
        ):
            self._last_chime_at = time.monotonic()

        self.query_one("#level", Static).update(f"Current level: {level:5.1f} dBFS")
        self.query_one("#meter", Static).update(
            render_meter(level_db=level, threshold_db=self.settings.threshold_db)
        )
        self.query_one("#status", Static).update(
            self._status_text(
                too_loud=too_loud,
                input_status=state.input_status,
                error=state.last_error or self.chime.last_error,
            )
        )

    def _status_text(self, *, too_loud: bool, input_status: str | None, error: str | None) -> Text:
        muted = "muted" if self.settings.muted else "armed"
        if error:
            return Text(f"Input error: {error}", style="red")
        if input_status:
            return Text(f"Input warning: {input_status}", style="yellow")
        if too_loud:
            return Text(f"Too loud — chime {muted}", style="bold red")
        return Text(f"Listening — chime {muted}", style="green")


def render_meter(*, level_db: float, threshold_db: float, width: int = 60) -> Text:
    """Render a horizontal dB meter with a threshold marker."""

    level_fraction = (clamp(level_db, DB_FLOOR, 0.0) - DB_FLOOR) / abs(DB_FLOOR)
    threshold_fraction = (clamp(threshold_db, DB_FLOOR, 0.0) - DB_FLOOR) / abs(DB_FLOOR)
    level_index = round(level_fraction * (width - 1))
    threshold_index = round(threshold_fraction * (width - 1))
    text = Text("[")
    for index in range(width):
        if index == threshold_index:
            char = "▲"
            style = "yellow"
        elif index <= level_index:
            char = "█"
            style = "red" if level_db >= threshold_db else "green"
        else:
            char = "·"
            style = "dim"
        text.append(char, style=style)
    text.append("] ")
    text.append(f"threshold {threshold_db:.0f} dB")
    return text
