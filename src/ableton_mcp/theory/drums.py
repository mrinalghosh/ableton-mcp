"""Default drum-voice -> MIDI pitch map (Ableton C3=60 convention).

Aligned with Live's stock Drum Rack layout: kick on C1, snare on D1, hats on
the F#/A# row, toms walking up from A1. Aliases included for the names
musicians actually type ('hat', 'ch', 'oh').
"""
from __future__ import annotations

DEFAULT_DRUM_MAP: dict[str, int] = {
    "kick":         36,
    "kick2":        35,
    "snare":        38,
    "snare2":       40,
    "rim":          37,
    "rimshot":      37,
    "clap":         39,
    "hat":          42,
    "closed_hat":   42,
    "ch":           42,
    "pedal_hat":    44,
    "open_hat":     46,
    "oh":           46,
    "tom_low":      45,
    "tom_mid":      47,
    "tom_high":     50,
    "crash":        49,
    "ride":         51,
    "cowbell":      56,
    "tambourine":   54,
    "shaker":       70,
    "conga_low":    64,
    "conga_high":   63,
}
