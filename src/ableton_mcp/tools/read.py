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
        name = osc.query("/live/track/get/name", i)[1]
        is_midi = osc.query("/live/track/get/has_midi_input", i)[1]
        tracks.append(
            {"index": i, "name": name, "type": "midi" if is_midi else "audio"}
        )
    return {
        "tempo": tempo,
        "time_signature": f"{sig_num}/{sig_den}",
        "tracks": tracks,
    }


def get_track_detail(track: int) -> dict[str, Any]:
    """Devices, clip slots, mixer state, and routing for one track."""
    osc = get_client()
    name = osc.query("/live/track/get/name", track)[1]
    volume = osc.query("/live/track/get/volume", track)[1]
    panning = osc.query("/live/track/get/panning", track)[1]
    mute = osc.query("/live/track/get/mute", track)[1]
    solo = osc.query("/live/track/get/solo", track)[1]
    num_devices = osc.query("/live/track/get/num_devices", track)[1]
    devices = []
    for d in range(int(num_devices)):
        dname = osc.query("/live/device/get/name", track, d)[2]
        devices.append({"index": d, "name": dname})

    # In session view, clip slot count per track == number of scenes.
    num_clips = osc.query("/live/song/get/num_scenes")[0]
    clips = []
    for c in range(int(num_clips)):
        has_clip = osc.query("/live/clip_slot/get/has_clip", track, c)[2]
        if has_clip:
            cname = osc.query("/live/clip/get/name", track, c)[2]
            clips.append({"slot": c, "name": cname})
    return {
        "name": name,
        "mixer": {
            "volume": float(volume),
            "panning": float(panning),
            "mute": bool(mute),
            "solo": bool(solo),
        },
        "devices": devices,
        "clips": clips,
    }


def get_device_parameters(track: int, device: int) -> list[dict[str, Any]]:
    """List a device's parameters with current value and range.

    Use parameter `index` (or `name`) to address one in set_device_parameter.
    """
    osc = get_client()
    names = osc.query("/live/device/get/parameters/name", track, device)[2:]
    values = osc.query("/live/device/get/parameters/value", track, device)[2:]
    mins = osc.query("/live/device/get/parameters/min", track, device)[2:]
    maxes = osc.query("/live/device/get/parameters/max", track, device)[2:]
    return [
        {
            "index": i,
            "name": str(name),
            "value": float(val),
            "min": float(mn),
            "max": float(mx),
        }
        for i, (name, val, mn, mx) in enumerate(zip(names, values, mins, maxes))
    ]


def get_clip_notes(track: int, clip: int) -> list[dict[str, float]]:
    """Notes in a MIDI clip: pitch, start (beats), duration (beats), velocity."""
    osc = get_client()
    raw = osc.query("/live/clip/get/notes", track, clip, timeout=2.0)
    raw = raw[2:]  # strip echoed (track, clip) prefix
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
    # AbletonOSC doesn't reply for return/main track selections, so treat
    # a timeout as "selection isn't a regular track" rather than an error.
    try:
        track: int | None = int(osc.query("/live/view/get/selected_track")[0])
    except TimeoutError:
        track = None
    try:
        scene: int | None = int(osc.query("/live/view/get/selected_scene")[0])
    except TimeoutError:
        scene = None
    return {"track": track, "scene": scene, "note": None if track is not None else "selection is a return or main track (not addressable via track index)"}
