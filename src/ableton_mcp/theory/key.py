"""Krumhansl-style key detection from a pitch-class distribution."""
from __future__ import annotations

import math
from typing import Any, Iterable

from .pitch import NOTES

# see https://rnhart.net/articles/key-finding/
# Krumhansl-Kessler profiles (1990). Index 0 = tonic, 1 = b2/min2, ..., 11 = maj7.
# Swap in Temperley or Albrecht-Shanahan profiles later if KK underperforms.
KK_MAJOR: tuple[float, ...] = (
    6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88,
)
KK_MINOR: tuple[float, ...] = (
    6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17,
)


def pitch_class_histogram(notes: Iterable[dict[str, Any]], *, weight_by: str = "duration") -> list[float]:
    """Sum note weights into a 12-bin pitch-class vector.

    notes: iterable of dicts with at least 'pitch' (MIDI int) and 'duration' (beats).
           May also carry 'velocity'. Matches the shape returned by get_clip_notes.
    weight_by: 'duration', 'velocity', 'duration_velocity' (product), or 'count'.
    """
    hist = [0.0] * 12
    for n in notes:
        pc = int(n['pitch']) % 12
        if weight_by == 'duration':
            w = float(n.get('duration', 0.0))
        elif weight_by == 'velocity':
            w = float(n.get('velocity', 0.0))
        elif weight_by == 'duration_velocity':
            w = float(n.get('duration', 0.0)) * float(n.get('velocity', 0.0))
        elif weight_by == 'count':
            w = 1.0
        else:
            raise ValueError(f"unknown weight_by: {weight_by!r}")
        hist[pc] += w
    return hist


def correlate(histogram: list[float], profile: tuple[float, ...]) -> float:
    """Pearson correlation between a 12-bin histogram and a 12-bin key profile.

    Both inputs are aligned to the same tonic; rotate the histogram (or profile)
    before calling to score a non-C key.
    """
    n = len(histogram)
    mh = sum(histogram) / n
    mp = sum(profile) / n
    num = 0.0
    dh = 0.0
    dp = 0.0
    for h, p in zip(histogram, profile):
        a = h - mh
        b = p - mp
        num += a * b
        dh += a * a
        dp += b * b
    denom = math.sqrt(dh * dp)
    if denom == 0.0:
        return 0.0
    return num / denom


def detect_key_from_pcs(histogram: list[float]) -> dict[str, Any]:
    """Score the histogram against all 24 keys and return the best match.

    Returns:
        {
          'tonic_pc': int,        # 0-11
          'mode': 'major'|'minor',
          'confidence': float,    # best correlation score
          'margin': float,        # best - runner-up; small margin = ambiguous
          'runner_up': {'tonic_pc': int, 'mode': str, 'score': float},
          'all_scores': list[tuple[int, str, float]],  # sorted desc, for debugging
        }
    """
    scores: list[tuple[int, str, float]] = []
    for tonic in range(12):
        rotated = histogram[tonic:] + histogram[:tonic]
        scores.append((tonic, 'major', correlate(rotated, KK_MAJOR)))
        scores.append((tonic, 'minor', correlate(rotated, KK_MINOR)))
    scores.sort(key=lambda s: s[2], reverse=True)
    best = scores[0]
    runner = scores[1]
    return {
        'tonic_pc': best[0],
        'mode': best[1],
        'confidence': best[2],
        'margin': best[2] - runner[2],
        'runner_up': {'tonic_pc': runner[0], 'mode': runner[1], 'score': runner[2]},
        'all_scores': scores,
    }


def format_key(tonic_pc: int, mode: str) -> str:
    """Render a (pc, mode) pair as 'C major' / 'F# minor'."""
    return f'{NOTES[tonic_pc]} {mode}'
