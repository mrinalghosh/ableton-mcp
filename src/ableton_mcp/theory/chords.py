"""Chord parsing and construction.

Two input flavors:
- Roman numerals (key-relative): "i", "IV", "V7", "bVII", "ii°".
  Case carries quality (upper = major-ish, lower = minor-ish). Suffix can
  override quality or add extensions. Accidentals "b" / "#" shift the root by
  a semitone (for borrowed/modal-interchange chords).
- Chord names (absolute): "Cm", "F#maj7", "G7", "Bbsus4".

build_chord turns a (root_pc, quality) pair into MIDI pitches at a given
octave using Ableton's C3=60 convention.
"""
from __future__ import annotations

import re

from .pitch import _LETTER_PC

MAJOR_SCALE = (0, 2, 4, 5, 7, 9, 11)
NATURAL_MINOR_SCALE = (0, 2, 3, 5, 7, 8, 10)

# (root_offset_semitones, default_quality) for each scale degree, by mode.
# Diatonic triads in major: I ii iii IV V vi vii°
# Diatonic triads in natural minor: i ii° III iv v VI VII
_DIATONIC_MAJOR = (
    (0, "maj"), (2, "min"), (4, "min"), (5, "maj"),
    (7, "maj"), (9, "min"), (11, "dim"),
)
_DIATONIC_MINOR = (
    (0, "min"), (2, "dim"), (3, "maj"), (5, "min"),
    (7, "min"), (8, "maj"), (10, "maj"),
)

QUALITY_INTERVALS: dict[str, tuple[int, ...]] = {
    "maj":   (0, 4, 7),
    "min":   (0, 3, 7),
    "dim":   (0, 3, 6),
    "aug":   (0, 4, 8),
    "sus2":  (0, 2, 7),
    "sus4":  (0, 5, 7),
    "5":     (0, 7),                # power chord
    "maj7":  (0, 4, 7, 11),
    "min7":  (0, 3, 7, 10),
    "7":     (0, 4, 7, 10),         # dominant 7
    "dim7":  (0, 3, 6, 9),
    "m7b5":  (0, 3, 6, 10),         # half-diminished
    "minmaj7": (0, 3, 7, 11),
    "6":     (0, 4, 7, 9),
    "min6":  (0, 3, 7, 9),
    "add9":  (0, 4, 7, 14),
    "min9":  (0, 3, 7, 10, 14),
    "maj9":  (0, 4, 7, 11, 14),
    "9":     (0, 4, 7, 10, 14),
}

_ROMAN_NUMERALS = ("VII", "VI", "IV", "V", "III", "II", "I")
_ROMAN_RE = re.compile(
    r"^(?P<acc>b|#)?(?P<num>VII|VI|IV|V|III|II|I|vii|vi|iv|v|iii|ii|i)"
    r"(?P<suffix>.*)$"
)
_CHORD_NAME_RE = re.compile(
    r"^(?P<root>[A-G])(?P<acc>[#b]?)(?P<suffix>.*)$"
)

# Suffix shorthand -> canonical quality key in QUALITY_INTERVALS.
# Empty suffix is handled by the caller (uses the default quality from context).
_SUFFIX_ALIASES = {
    "": None,           # caller default
    "m": "min",
    "M": "maj",
    "min": "min",
    "maj": "maj",
    "dim": "dim",
    "°": "dim",
    "o": "dim",
    "aug": "aug",
    "+": "aug",
    "sus2": "sus2",
    "sus4": "sus4",
    "sus": "sus4",
    "5": "5",
    "7": "7",
    "maj7": "maj7",
    "M7": "maj7",
    "m7": "min7",
    "min7": "min7",
    "dim7": "dim7",
    "m7b5": "m7b5",
    "ø": "m7b5",
    "mM7": "minmaj7",
    "minmaj7": "minmaj7",
    "6": "6",
    "m6": "min6",
    "min6": "min6",
    "add9": "add9",
    "9": "9",
    "m9": "min9",
    "min9": "min9",
    "maj9": "maj9",
    "M9": "maj9",
}


def _resolve_suffix(suffix: str, default: str) -> str:
    if suffix in _SUFFIX_ALIASES:
        mapped = _SUFFIX_ALIASES[suffix]
        return mapped if mapped is not None else default
    raise ValueError(f"unknown chord suffix: {suffix!r}")


def parse_key(key: str) -> tuple[int, str]:
    """Parse 'C', 'Am', 'F#m', 'Bb' into (tonic_pc, mode)."""
    m = re.match(r"^([A-G])([#b]?)(m|min|minor|maj|major)?$", key.strip())
    if not m:
        raise ValueError(f"invalid key: {key!r}")
    letter, acc, mode_suffix = m.groups()
    pc = _LETTER_PC[letter] + (1 if acc == "#" else -1 if acc == "b" else 0)
    pc %= 12
    mode = "minor" if mode_suffix in ("m", "min", "minor") else "major"
    return pc, mode


def parse_roman(token: str, key_tonic_pc: int, mode: str) -> tuple[int, str, bool]:
    """Parse a roman-numeral chord token relative to a key.

    Examples (in C major): 'I' -> (0, 'maj'), 'vi' -> (9, 'min'), 'V7' -> (7, '7'),
    'bVII' -> (10, 'maj'), 'ii°' -> (2, 'dim').

    Case of the numeral picks the default quality (major when upper, minor
    when lower). A suffix overrides that default.
    """
    m = _ROMAN_RE.match(token.strip())
    if not m:
        raise ValueError(f"not a roman-numeral chord: {token!r}")
    acc = m.group("acc")
    num = m.group("num")
    suffix = m.group("suffix")

    # Root offset comes from the diatonic table; quality is case-only so that
    # 'bVII' / 'bII' read as borrowed major chords (rock-pop convention) and
    # dim/aug always require an explicit suffix.
    table = _DIATONIC_MAJOR if mode == "major" else _DIATONIC_MINOR
    _DEGREE_INDEX = {"I": 0, "II": 1, "III": 2, "IV": 3, "V": 4, "VI": 5, "VII": 6}
    offset, _ = table[_DEGREE_INDEX[num.upper()]]
    default_quality = "min" if num[0].islower() else "maj"

    if acc == "b":
        offset -= 1
    elif acc == "#":
        offset += 1

    quality = _resolve_suffix(suffix, default_quality)
    root_pc = (key_tonic_pc + offset) % 12
    return root_pc, quality, bool(suffix)


def parse_chord_name(token: str) -> tuple[int, str, bool]:
    """Parse an absolute chord name into (root_pc, quality).

    Examples: 'C' -> (0, 'maj'), 'Cm' -> (0, 'min'), 'F#maj7' -> (6, 'maj7'),
    'Bb7' -> (10, '7').
    """
    m = _CHORD_NAME_RE.match(token.strip())
    if not m:
        raise ValueError(f"not a chord name: {token!r}")
    root_letter = m.group("root")
    acc = m.group("acc")
    suffix = m.group("suffix")
    pc = _LETTER_PC[root_letter] + (1 if acc == "#" else -1 if acc == "b" else 0)
    quality = _resolve_suffix(suffix, "maj")
    return pc % 12, quality, bool(suffix)


def parse_chord_token(
    token: str,
    key_tonic_pc: int | None,
    mode: str | None,
) -> tuple[int, str, bool]:
    """Dispatch on first character: roman if [iIvV], else chord name.

    Roman tokens require key_tonic_pc and mode.
    """
    stripped = token.strip()
    head = stripped[1:2] if stripped[:1] in "b#" else stripped[:1]
    if head in "iIvV":
        if key_tonic_pc is None or mode is None:
            raise ValueError(
                f"roman-numeral token {token!r} needs a key — pass key='C' or 'Am'"
            )
        return parse_roman(token, key_tonic_pc, mode)
    return parse_chord_name(token)


def build_chord(
    root_pc: int,
    quality: str,
    *,
    octave: int = 3,
    ableton_octave: bool = True,
) -> list[int]:
    """Return MIDI pitches for the chord, with the root at the given octave.

    Ableton's display convention puts C3 at MIDI 60; pass ableton_octave=False
    to use the standard MIDI convention (C4=60) instead.
    """
    if quality not in QUALITY_INTERVALS:
        raise ValueError(
            f"unknown quality {quality!r}; known: {sorted(QUALITY_INTERVALS)}"
        )
    base = (octave + 1 + (1 if ableton_octave else 0)) * 12 + (root_pc % 12)
    return [base + i for i in QUALITY_INTERVALS[quality]]
