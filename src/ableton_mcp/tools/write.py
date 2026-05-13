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
    # AbletonOSC's create_*_track is fire-and-forget. Capture the new index
    # by reading num_tracks before the call — appending at -1 puts the new
    # track at that position.
    index = int(osc.query("/live/song/get/num_tracks")[0])
    osc.send(address, -1)
    if name:
        osc.send("/live/track/set/name", index, name)
    return {"created": track_type, "index": index, "name": name}


def set_track_volume(track: int, volume: float) -> dict:
    """Set track volume. 0.0 = -inf dB, 0.85 = unity (0 dB), 1.0 = +6 dB."""
    clamped = max(0.0, min(1.0, float(volume)))
    get_client().send("/live/track/set/volume", track, clamped)
    return {"track": track, "volume": clamped, "clamped": clamped != float(volume)}


def set_track_panning(track: int, panning: float) -> dict:
    """Set track pan. -1.0 = hard left, 0.0 = center, 1.0 = hard right."""
    clamped = max(-1.0, min(1.0, float(panning)))
    get_client().send("/live/track/set/panning", track, clamped)
    return {"track": track, "panning": clamped, "clamped": clamped != float(panning)}


def set_track_mute(track: int, mute: bool) -> dict:
    get_client().send("/live/track/set/mute", track, 1 if mute else 0)
    return {"track": track, "mute": bool(mute)}


def set_track_solo(track: int, solo: bool) -> dict:
    get_client().send("/live/track/set/solo", track, 1 if solo else 0)
    return {"track": track, "solo": bool(solo)}


def set_device_parameter(
    track: int,
    device: int,
    parameter: int | str,
    value: float,
) -> dict:
    """Set one parameter on a device. `parameter` may be an index or a name.

    Names are preferred — parameter indices aren't guaranteed stable across
    plugin reloads. Value is clamped to the parameter's [min, max] range.
    """
    osc = get_client()
    names = osc.query("/live/device/get/parameters/name", track, device)[2:]
    if isinstance(parameter, str):
        try:
            index = next(i for i, n in enumerate(names) if str(n) == parameter)
        except StopIteration as e:
            raise ValueError(
                f"No parameter named {parameter!r} on track {track} device {device}. "
                f"Available: {[str(n) for n in names]}"
            ) from e
    else:
        index = int(parameter)
        if index < 0 or index >= len(names):
            raise ValueError(
                f"Parameter index {index} out of range; device has {len(names)} parameters"
            )

    mins = osc.query("/live/device/get/parameters/min", track, device)[2:]
    maxes = osc.query("/live/device/get/parameters/max", track, device)[2:]
    clamped = max(float(mins[index]), min(float(maxes[index]), float(value)))
    osc.send("/live/device/set/parameter/value", track, device, index, clamped)
    return {
        "track": track,
        "device": device,
        "parameter": {"index": index, "name": str(names[index])},
        "value": clamped,
        "clamped": clamped != float(value),
    }


_BROWSER_CATEGORIES = ("instruments", "drums", "sounds")


def load_instrument(track: int, category: str, path: list[str]) -> dict:
    """Load a device from Live's browser onto a track.

    category: one of "instruments", "drums", "sounds".
    path: full path of folder names ending at a loadable leaf, e.g.
        ["Operator", "Bass", "Sub Bass.adv"]. Use list_browser to discover.
    The target track is selected before loading; the device is appended.
    """
    if category not in _BROWSER_CATEGORIES:
        raise ValueError(
            f"category must be one of {_BROWSER_CATEGORIES}, got {category!r}"
        )
    if not path:
        raise ValueError("path must name at least one browser item")
    osc = get_client()
    reply = osc.query("/live/browser/load", int(track), category, *path, timeout=3.0)
    _track, ok, detail = reply[0], reply[1], reply[2]
    if not int(ok):
        raise RuntimeError(f"load_item failed: {detail}")
    return {"track": int(_track), "category": category, "path": path, "loaded": str(detail)}


def fire_clip(track: int, clip: int) -> dict:
    """Start playing a clip. The system prompt requires Claude to confirm with the user first."""
    get_client().send("/live/clip/fire", track, clip)
    return {"fired": {"track": track, "clip": clip}}


def stop_clip(track: int, clip: int) -> dict:
    get_client().send("/live/clip/stop", track, clip)
    return {"stopped": {"track": track, "clip": clip}}
