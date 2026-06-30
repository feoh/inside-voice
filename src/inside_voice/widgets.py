# pyright: reportMissingImports=false
"""Small Textual widgets used by inside-voice."""

from __future__ import annotations

from typing import ClassVar

from rich.text import Text
from textual import events
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from .config import clamp


class ValueSlider(Static):
    """A lightweight horizontal slider for Textual versions without one built in."""

    DEFAULT_CSS = """
    ValueSlider {
        height: 1;
        margin: 1 0 0 0;
    }
    ValueSlider:focus {
        text-style: bold;
    }
    """

    can_focus = True
    value = reactive(0.0)

    class Changed(Message):
        """Posted when a slider value changes."""

        def __init__(self, slider: ValueSlider, value: float) -> None:
            super().__init__()
            self.slider = slider
            self.value = value

    _dragging: bool = False
    _keys: ClassVar[dict[str, float]] = {
        "left": -1.0,
        "down": -1.0,
        "right": 1.0,
        "up": 1.0,
        "pagedown": -5.0,
        "pageup": 5.0,
    }

    def __init__(
        self,
        label: str,
        *,
        minimum: float,
        maximum: float,
        value: float,
        step: float,
        unit: str = "",
        precision: int = 1,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.label = label
        self.minimum = minimum
        self.maximum = maximum
        self.step = step
        self.unit = unit
        self.precision = precision
        self.value = clamp(value, minimum, maximum)

    def render(self) -> Text:
        """Render the slider track."""

        width = max(20, self.size.width)
        value_text = f"{self.value:.{self.precision}f}{self.unit}"
        prefix = f"{self.label}: {value_text} "
        track_width = max(10, width - len(prefix) - 1)
        fraction = (self.value - self.minimum) / (self.maximum - self.minimum)
        thumb = round(fraction * (track_width - 1))
        pieces = ["━" for _ in range(track_width)]
        pieces[thumb] = "●"
        text = Text(prefix)
        style = "bold cyan" if self.has_focus else "cyan"
        text.append("".join(pieces), style=style)
        return text

    def set_value(self, value: float, *, notify: bool = True) -> None:
        """Set the slider value, snapping to the configured step."""

        stepped = round(value / self.step) * self.step
        new_value = clamp(stepped, self.minimum, self.maximum)
        if abs(new_value - self.value) < 0.0001:
            return
        self.value = new_value
        self.refresh()
        if notify:
            self.post_message(self.Changed(self, new_value))

    def on_key(self, event: events.Key) -> None:
        """Adjust focused slider from the keyboard."""

        if event.key == "home":
            self.set_value(self.minimum)
            event.stop()
            return
        if event.key == "end":
            self.set_value(self.maximum)
            event.stop()
            return
        multiplier = self._keys.get(event.key)
        if multiplier is None:
            return
        self.set_value(self.value + (self.step * multiplier))
        event.stop()

    def on_click(self, event: events.Click) -> None:
        """Move the thumb to the clicked position."""

        self.focus()
        self._set_from_x(event.x)
        event.stop()

    def on_mouse_down(self, event: events.MouseDown) -> None:
        """Start dragging the slider thumb."""

        self.focus()
        self.capture_mouse()
        self._dragging = True
        self._set_from_x(event.x)
        event.stop()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        """Update the slider while dragging."""

        if not self._dragging:
            return
        self._set_from_x(event.x)
        event.stop()

    def on_mouse_up(self, event: events.MouseUp) -> None:
        """Finish a drag interaction."""

        if self._dragging:
            self._dragging = False
            self.release_mouse()
            event.stop()

    def _set_from_x(self, x: int) -> None:
        width = max(1, self.size.width - 1)
        fraction = clamp(x / width, 0.0, 1.0)
        self.set_value(self.minimum + (fraction * (self.maximum - self.minimum)))
