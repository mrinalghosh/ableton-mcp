"""Analysis tools — read from Live, compute musical insights, return them."""
from __future__ import annotations

from typing import Any, Iterator

from ..osc_client import get_client
from ..theory.key import (
    detect_key_from_pcs,
    format_key,
    pitch_class_histogram,
)
from . import read


def _num_scenes() -> int:
    return int(get_client().query("/live/song/get/num_scenes")[0])


def _num_tracks() -> int:
    return int(get_client().query("/live/song/get/num_tracks")[0])


def _track_is_midi(track: int) -> bool:
    return bool(get_client().query("/live/track/get/has_midi_input", track)[1])


def _track_is_drum(track: int) -> bool:
    """Heuristic: a track with a Drum Rack device, or whose name suggests percussion.

    AbletonOSC doesn't expose has_drum_pads on Track directly, so we walk the
    device chain. Drum Rack device class is named 'DrumGroupDevice' in Live but
    surfaces as 'Drum Rack' via the get/name endpoint.
    """
    osc = get_client()
    num_devices = int(osc.query("/live/track/get/num_devices", track)[1])
    for d in range(num_devices):
        dname = str(osc.query("/live/device/get/name", track, d)[2]).lower()
        if "drum rack" in dname or "drum kit" in dname:
            return True
    name = str(osc.query("/live/track/get/name", track)[1]).lower()
    return any(kw in name for kw in ("drum", "kick", "snare", "hat", "perc"))


def _iter_midi_clip_slots(track: int) -> Iterator[int]:
    osc = get_client()
    for c in range(_num_scenes()):
        if bool(osc.query("/live/clip_slot/get/has_clip", track, c)[2]):
            yield c


def _shape_result(result: dict[str, Any], *, note_count: int, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    tonic = result["tonic_pc"]
    mode = result["mode"]
    runner = result["runner_up"]
    out: dict[str, Any] = {
        "key": format_key(tonic, mode),
        "tonic_pc": tonic,
        "mode": mode,
        "confidence": result["confidence"],
        "margin": result["margin"],
        "runner_up": {
            "key": format_key(runner["tonic_pc"], runner["mode"]),
            "tonic_pc": runner["tonic_pc"],
            "mode": runner["mode"],
            "score": runner["score"],
        },
        "note_count": note_count,
    }
    if extra:
        out.update(extra)
    return out


def detect_clip_key(track: int, clip: int) -> dict[str, Any]:
    """Estimate the key of a single MIDI clip.

    Pulls notes via get_clip_notes, builds a duration-weighted pitch-class
    histogram, and runs Krumhansl correlation. Returns the best-fit key, a
    confidence score, and the runner-up (often the relative major/minor or
    the dominant — useful for the user to see).
    """
    notes = read.get_clip_notes(track, clip)
    if not notes:
        return {"key": None, "note_count": 0, "reason": "clip has no notes"}
    hist = pitch_class_histogram(notes, weight_by="duration")
    return _shape_result(detect_key_from_pcs(hist), note_count=len(notes))


def detect_track_key(track: int) -> dict[str, Any]:
    """Estimate the key of a whole track by aggregating across all its MIDI clips.

    More robust than detect_clip_key for short or chromatic clips: longer
    sample = cleaner histogram. Skips empty slots and audio clips.
    """
    if not _track_is_midi(track):
        return {"key": None, "note_count": 0, "reason": "track is not a MIDI track"}
    all_notes: list[dict[str, Any]] = []
    used_slots: list[int] = []
    for slot in _iter_midi_clip_slots(track):
        notes = read.get_clip_notes(track, slot)
        if notes:
            all_notes.extend(notes)
            used_slots.append(slot)
    if not all_notes:
        return {"key": None, "note_count": 0, "reason": "track has no MIDI notes"}
    hist = pitch_class_histogram(all_notes, weight_by="duration")
    return _shape_result(
        detect_key_from_pcs(hist),
        note_count=len(all_notes),
        extra={"clips_used": used_slots},
    )


def detect_session_key(*, exclude_drum_tracks: bool = True) -> dict[str, Any]:
    """Estimate the key of the whole set by aggregating every MIDI clip on every track.

    Drum tracks are excluded by default — their pitch content is percussive
    mapping, not tonal, and would skew the histogram. Detection is based on
    Drum Rack device presence or track-name heuristics; surface which tracks
    were used.
    """
    osc = get_client()
    all_notes: list[dict[str, Any]] = []
    tracks_used: list[dict[str, Any]] = []
    tracks_skipped: list[dict[str, Any]] = []
    for t in range(_num_tracks()):
        name = str(osc.query("/live/track/get/name", t)[1])
        if not _track_is_midi(t):
            continue
        if exclude_drum_tracks and _track_is_drum(t):
            tracks_skipped.append({"index": t, "name": name, "reason": "drum track"})
            continue
        track_notes: list[dict[str, Any]] = []
        for slot in _iter_midi_clip_slots(t):
            track_notes.extend(read.get_clip_notes(t, slot))
        if track_notes:
            all_notes.extend(track_notes)
            tracks_used.append({"index": t, "name": name, "note_count": len(track_notes)})
    if not all_notes:
        return {
            "key": None,
            "note_count": 0,
            "reason": "no tonal MIDI notes in session",
            "tracks_used": tracks_used,
            "tracks_skipped": tracks_skipped,
        }
    hist = pitch_class_histogram(all_notes, weight_by="duration")
    return _shape_result(
        detect_key_from_pcs(hist),
        note_count=len(all_notes),
        extra={"tracks_used": tracks_used, "tracks_skipped": tracks_skipped},
    )
