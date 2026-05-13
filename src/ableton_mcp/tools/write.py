"""Write tools — let Claude compose into the Live set.

Pedagogy reminder: after any write, narrate what was done and why (key
choice, rhythmic idea, voice leading). The system prompt enforces this.
"""
from __future__ import annotations

from ..osc_client import get_client


def create_midi_clip(
    track: int,
    clip_slot: int,
    length_beats: float,
    notes: list[dict],
) -> dict:
    """Create a MIDI clip and fill it with notes.

    notes: list of {pitch, start, duration, velocity}.
    """
    osc = get_client()
    osc.send("/live/clip_slot/create_clip", track, clip_slot, length_beats)
    flat: list = []
    for n in notes:
        flat.extend(
            [
                int(n["pitch"]),
                float(n["start"]),
                float(n["duration"]),
                int(n.get("velocity", 100)),
                0,  # mute
            ]
        )
    if flat:
        osc.send("/live/clip/add/notes", track, clip_slot, *flat)
    return {"track": track, "clip_slot": clip_slot, "note_count": len(notes)}


def modify_clip_notes(track: int, clip: int, notes: list[dict]) -> dict:
    """Replace all notes in an existing MIDI clip."""
    osc = get_client()
    osc.send("/live/clip/remove/notes", track, clip)
    flat: list = []
    for n in notes:
        flat.extend(
            [
                int(n["pitch"]),
                float(n["start"]),
                float(n["duration"]),
                int(n.get("velocity", 100)),
                0,
            ]
        )
    if flat:
        osc.send("/live/clip/add/notes", track, clip, *flat)
    return {"track": track, "clip": clip, "note_count": len(notes)}


def set_tempo(bpm: float) -> dict:
    get_client().send("/live/song/set/tempo", float(bpm))
    return {"tempo": bpm}


def set_time_signature(numerator: int, denominator: int) -> dict:
    osc = get_client()
    osc.send("/live/song/set/signature_numerator", int(numerator))
    osc.send("/live/song/set/signature_denominator", int(denominator))
    return {"time_signature": f"{numerator}/{denominator}"}


def create_track(track_type: str = "midi", name: str | None = None) -> dict:
    """Create a new MIDI or audio track at the end of the set."""
    osc = get_client()
    address = (
        "/live/song/create_midi_track" if track_type == "midi"
        else "/live/song/create_audio_track"
    )
    reply = osc.query(address, -1)
    # AbletonOSC may echo the requested-position arg before the new index.
    index = int(reply[-1]) if reply else -1
    if name and index >= 0:
        osc.send("/live/track/set/name", index, name)
    return {"created": track_type, "index": index, "name": name}


def fire_clip(track: int, clip: int) -> dict:
    """Start playing a clip. The system prompt requires Claude to confirm with the user first."""
    get_client().send("/live/clip/fire", track, clip)
    return {"fired": {"track": track, "clip": clip}}


def stop_clip(track: int, clip: int) -> dict:
    get_client().send("/live/clip/stop", track, clip)
    return {"stopped": {"track": track, "clip": clip}}
