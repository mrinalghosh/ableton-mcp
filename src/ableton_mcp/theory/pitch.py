"""MIDI/pitch-class conversions, including Ableton's C3=60 octave convention."""
from __future__ import annotations

import re

NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
_LETTER_PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
_NAME_RE = re.compile(r'^([A-Ga-g])([#b]?)(-?\d+)$')


def pc_of(midi: int) -> int:
    """Pitch class (0-11) of a MIDI note number. C=0, C#=1, ..., B=11."""
    return midi % 12


def midi_to_name(midi: int, *, ableton_octave: bool = True) -> str:
    """MIDI number to note name like 'C3' or 'F#4'.

    When ableton_octave is True, uses Live's convention where MIDI 60 = C3.
    Standard MIDI convention (used by most other software) has MIDI 60 = C4.
    """
    return NOTES[midi % 12] + str(midi // 12 - 1 - ableton_octave)


def name_to_midi(name: str, *, ableton_octave: bool = True) -> int:
    """Inverse of midi_to_name. Accepts 'C3', 'Db4', 'F#-1', etc."""
    m = _NAME_RE.match(name.strip())
    if not m:
        raise ValueError(f"invalid note name: {name!r}")
    letter, accidental, octave = m.groups()
    pc = _LETTER_PC[letter.upper()] + (1 if accidental == '#' else -1 if accidental == 'b' else 0)
    return (int(octave) + 1 + ableton_octave) * 12 + pc


def pc_name(pc: int) -> str:
    """Pitch class integer to canonical name ('C', 'C#', 'D', ...). Sharps only."""
    return NOTES[pc % 12]
