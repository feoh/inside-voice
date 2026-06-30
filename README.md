# inside-voice

`inside-voice` is a terminal app that helps you keep your speaking volume down
while you are on Zoom, Google Meet, or other calls. It watches your microphone
level and plays a short local chime when your voice crosses above an adjustable
dB threshold, or after it stays above the threshold for a configurable duration.

The app is Linux-first and built with cross-platform pieces
(`sounddevice`/PortAudio + Textual), so macOS and Windows should be achievable
even though Linux is the primary target.

## Features

- Live microphone level meter in dBFS
- Textual TUI with mouse/keyboard-adjustable sliders
- Sliders for threshold, repeat sustain duration, cooldown, and chime volume
- Configurable first chime behavior: immediate crossing or sustained loudness
- Generated two-tone chime; no bundled audio asset required
- Mute toggle and quick calibration action
- Settings saved under your platform config directory
- Audio input device listing and selection

## Requirements

- Python 3.14+
- [`uv`](https://docs.astral.sh/uv/)
- PortAudio runtime libraries

On Debian/Ubuntu-style Linux systems, PortAudio is typically available with:

```bash
sudo apt install libportaudio2 portaudio19-dev
```

Package names vary by distribution.

## Install and run from source

```bash
git clone https://github.com/feoh/inside-voice.git
cd inside-voice
uv sync
uv run inside-voice
```

List input devices:

```bash
uv run inside-voice --list-devices
```

Choose a device by index or name substring:

```bash
uv run inside-voice --input-device 3
uv run inside-voice --input-device "USB Headset"
```

Start with a threshold override:

```bash
uv run inside-voice --threshold -28
```

## Controls

- `q` — quit
- `m` — mute/unmute chime playback
- `c` — one-shot threshold calibration: set threshold to current level + 6 dB
- `t` — toggle first chime behavior between immediate and sustained
- Arrow keys — adjust the focused slider; after `c`, Threshold gets focus
- Page Up/Page Down — adjust focused slider in larger steps
- Home/End — move focused slider to minimum/maximum
- Mouse click/drag — set slider values

## Tuning tips

1. Join a call with your normal headphones/microphone setup.
2. Speak at a comfortable normal volume.
3. Press `c` to place the threshold slightly above that level.
   - `c` is not a mode; it immediately updates the Threshold slider and saves it.
   - After calibration, arrow keys adjust the Threshold slider for fine-tuning.
4. Leave "Immediate first chime" enabled if you want prompt feedback.
5. Disable "Immediate first chime" if you only want alerts after sustained loudness.
6. If the chime triggers too often, raise the threshold or increase cooldown.
7. If it triggers too late, lower the threshold or re-enable immediate first chime.
8. Increase repeat sustain if repeated chimes are annoying while staying loud.

The meter uses dBFS, where `0 dBFS` is the loudest possible digital input and
quieter sounds are negative numbers. Typical microphone speech levels often land
somewhere between `-45` and `-15 dBFS`, depending on gain and hardware.

## Configuration

Settings are saved automatically to your platform config directory, for example:

- Linux: `~/.config/inside-voice/settings.json`
- macOS: `~/Library/Application Support/inside-voice/settings.json`
- Windows: `%LOCALAPPDATA%\\inside-voice\\settings.json`

## Development

```bash
uv sync
uv run ruff check .
uv run mypy src tests
uv run pytest
```

## License

MIT
