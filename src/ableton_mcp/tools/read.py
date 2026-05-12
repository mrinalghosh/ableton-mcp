"""Read tools — let Claude observe the Live set."""
from __future__ import annotations

from typing import Any

from ..osc_client import get_client


def get_session_overview() -> dict[str, Any]:
    """Tempo, time signature, and a summary of every track in the set."""
    osc = get_client()
    tempo = osc.query("/live/song/get/tempo")[0]
    sig_num = osc.query("/live/song/get/signature_numerator")[0]
    sig_den = osc.query("/live/song/get/signature_denominator")[0]
    num_tracks = osc.query("/live/song/get/num_tracks")[0]

    tracks = []
    for i in range(int(num_tracks)):
        name = osc.query("/live/track/get/name", i)[0]
        is_midi = osc.query("/live/track/get/has_midi_input", i)[0]
        tracks.append(
            {"index": i, "name": name, "type": "midi" if is_midi else "audio"}
        )
    return {
        "tempo": tempo,
        "time_signature": f"{sig_num}/{sig_den}",
        "tracks": tracks,
    }


def get_track_detail(track: int) -> dict[str, Any]:
    """Devices, clip slots, and routing for one track."""
    osc = get_client()
    name = osc.query("/live/track/get/name", track)[0]
    num_devices = osc.query("/live/track/get/num_devices", track)[0]
    devices = []
    for d in range(int(num_devices)):
        dname = osc.query("/live/device/get/name", track, d)[0]
        devices.append({"index": d, "name": dname})

    num_clips = osc.query("/live/track/get/num_clip_slots", track)[0]
    clips = []
    for c in range(int(num_clips)):
        has_clip = osc.query("/live/clip_slot/get/has_clip", track, c)[0]
        if has_clip:
            cname = osc.query("/live/clip/get/name", track, c)[0]
            clips.append({"slot": c, "name": cname})
    return {"name": name, "devices": devices, "clips": clips}


def get_clip_notes(track: int, clip: int) -> list[dict[str, float]]:
    """Notes in a MIDI clip: pitch, start (beats), duration (beats), velocity."""
    osc = get_client()
    raw = osc.query("/live/clip/get/notes", track, clip, timeout=2.0)
    notes = []
    for i in range(0, len(raw), 5):
        pitch, start, dur, vel, _mute = raw[i : i + 5]
        notes.append(
            {"pitch": int(pitch), "start": float(start), "duration": float(dur), "velocity": int(vel)}
        )
    return notes


def get_transport_state() -> dict[str, Any]:
    """Whether Live is playing, current beat, and loop state."""
    osc = get_client()
    playing = osc.query("/live/song/get/is_playing")[0]
    beat = osc.query("/live/song/get/current_song_time")[0]
    loop = osc.query("/live/song/get/loop")[0]
    return {"is_playing": bool(playing), "current_beat": float(beat), "loop": bool(loop)}


def get_selected() -> dict[str, Any]:
    """What the user currently has selected in Live. The grounding for 'explain this'."""
    osc = get_client()
    track = osc.query("/live/view/get/selected_track")[0]
    try:
        scene = osc.query("/live/view/get/selected_scene")[0]
    except TimeoutError:
        scene = None
    return {"track": int(track), "scene": int(scene) if scene is not None else None}
