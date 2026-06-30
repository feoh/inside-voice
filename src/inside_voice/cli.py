# pyright: reportMissingImports=false
"""Command-line entry point for inside-voice."""

from __future__ import annotations

from typing import Annotated

import cyclopts
from rich.console import Console

from .app import InsideVoiceApp
from .audio import list_input_devices
from .config import load_settings, save_settings

app = cyclopts.App(name="inside-voice", help="Keep your voice down with a local mic-level chime.")
console = Console()


@app.default
def run(
    *,
    threshold: Annotated[
        float | None,
        cyclopts.Parameter(help="Initial threshold in dBFS, e.g. -25. Saved for next run."),
    ] = None,
    input_device: Annotated[
        str | None,
        cyclopts.Parameter(
            help="Input device index or name substring. Use --list-devices to inspect choices."
        ),
    ] = None,
    list_devices: Annotated[
        bool,
        cyclopts.Parameter(name="--list-devices", help="List microphone input devices and exit."),
    ] = False,
) -> None:
    """Launch inside-voice."""

    if list_devices:
        for line in list_input_devices():
            console.print(line)
        return

    settings = load_settings()
    if threshold is not None:
        settings.threshold_db = threshold
    if input_device is not None:
        settings.input_device = parse_device(input_device)
    save_settings(settings)
    InsideVoiceApp(settings).run()


def parse_device(value: str) -> str | int:
    """Convert numeric device values to indexes, otherwise preserve names."""

    try:
        return int(value)
    except ValueError:
        return value


if __name__ == "__main__":
    app()
