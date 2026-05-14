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


_BROWSER_CATEGORIES = ("instruments", "drums", "sounds", "audio_effects", "midi_effects")


def load_device(track: int, category: str, path: list[str]) -> dict:
    """Load a device from Live's browser onto a track.

    category: one of "instruments", "drums", "sounds", "audio_effects", "midi_effects".
    path: full path of folder names ending at a loadable leaf, e.g.
        ["Operator", "Bass", "Sub Bass.adv"] or ["EQ Eight"]. Use list_browser
        to discover. The target track is selected before loading; the device
        is appended to the end of its device chain.
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


def _resolve_parameter(osc, track: int, device: int, parameter: int | str) -> tuple[int, str, float, float]:
    """Resolve `parameter` (name or index) to (index, name, min, max)."""
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
    return index, str(names[index]), float(mins[index]), float(maxes[index])


_TAIL_DURATION_BEATS = 1.0


def set_clip_automation(
    track: int,
    clip: int,
    device: int,
    parameter: int | str,
    points: list[dict],
) -> dict:
    """Write an automation envelope for a device parameter inside a clip.

    Each entry in `points` is {time, value} or {time, duration, value}, in
    beats relative to clip start. Points are sorted by time before writing.

    Live's LOM only supports flat *step* segments — there is no real
    single-breakpoint primitive (`insert_step(time, 0, value)` is a no-op),
    and steps are left-exclusive (a step at time=0 doesn't cover t=0
    exactly). To smooth this over:

    - If a point omits `duration`, it auto-fills to the next point's time
      (or +1 beat for the final point), so callers can pass {time, value}
      breakpoints and get a tiled step envelope.
    - For a smooth ramp, pass many closely spaced breakpoints — Live will
      render visible stair-steps but they will be small.

    Values are clamped to the parameter's [min, max] range. Existing
    automation for this parameter is NOT cleared first — call
    clear_clip_automation if you want a clean slate.
    """
    if not points:
        raise ValueError("points must contain at least one entry")
    osc = get_client()
    index, name, pmin, pmax = _resolve_parameter(osc, track, device, parameter)

    sorted_points = sorted(points, key=lambda p: float(p["time"]))
    written = []
    for i, p in enumerate(sorted_points):
        t = float(p["time"])
        v = float(p["value"])
        if "duration" in p:
            d = float(p["duration"])
        elif i + 1 < len(sorted_points):
            d = float(sorted_points[i + 1]["time"]) - t
        else:
            d = _TAIL_DURATION_BEATS
        if d <= 0:
            raise ValueError(
                f"duration must be > 0 (insert_step with duration<=0 is a no-op); "
                f"got {d} for point at time={t}"
            )
        clamped = max(pmin, min(pmax, v))
        osc.send(
            "/live/clip/automation/insert_step",
            track, clip, device, index, t, d, clamped,
        )
        written.append({"time": t, "duration": d, "value": clamped, "clamped": clamped != v})
    return {
        "track": track,
        "clip": clip,
        "device": device,
        "parameter": {"index": index, "name": name, "min": pmin, "max": pmax},
        "points": written,
    }


def sample_clip_automation(
    track: int,
    clip: int,
    device: int,
    parameter: int | str,
    start: float,
    end: float,
    steps: int = 16,
) -> dict:
    """Sample an automation envelope at `steps` evenly spaced times in [start, end].

    Live's LOM doesn't expose breakpoints directly, so reads are sampled.
    Returns {time, value} pairs.
    """
    if end <= start:
        raise ValueError(f"end ({end}) must be greater than start ({start})")
    if steps < 2:
        raise ValueError(f"steps must be >= 2, got {steps}")
    osc = get_client()
    index, name, pmin, pmax = _resolve_parameter(osc, track, device, parameter)
    reply = osc.query(
        "/live/clip/automation/sample",
        track, clip, device, index, float(start), float(end), int(steps),
        timeout=3.0,
    )
    # Reply: (track, clip, device, param, steps, t0, v0, t1, v1, ...) on success,
    # or (0, "error message") on failure.
    if len(reply) >= 2 and reply[0] == 0 and isinstance(reply[1], str):
        raise RuntimeError(f"sample failed: {reply[1]}")
    payload = reply[5:]
    samples = [{"time": float(payload[i]), "value": float(payload[i + 1])}
               for i in range(0, len(payload), 2)]
    return {
        "track": track,
        "clip": clip,
        "device": device,
        "parameter": {"index": index, "name": name, "min": pmin, "max": pmax},
        "samples": samples,
    }


def clear_clip_automation(
    track: int,
    clip: int,
    device: int | None = None,
    parameter: int | str | None = None,
) -> dict:
    """Clear automation on a clip.

    If `device` and `parameter` are both given, clears only that parameter's
    envelope. Otherwise clears every envelope on the clip.
    """
    osc = get_client()
    if device is None and parameter is None:
        osc.send("/live/clip/automation/clear_all", track, clip)
        return {"track": track, "clip": clip, "cleared": "all"}
    if device is None or parameter is None:
        raise ValueError("device and parameter must be given together, or both omitted")
    index, name, _pmin, _pmax = _resolve_parameter(osc, track, device, parameter)
    osc.send("/live/clip/automation/clear", track, clip, device, index)
    return {
        "track": track,
        "clip": clip,
        "device": device,
        "parameter": {"index": index, "name": name},
        "cleared": "one",
    }


def fire_clip(track: int, clip: int) -> dict:
    """Start playing a clip. The system prompt requires Claude to confirm with the user first."""
    get_client().send("/live/clip/fire", track, clip)
    return {"fired": {"track": track, "clip": clip}}


def stop_clip(track: int, clip: int) -> dict:
    get_client().send("/live/clip/stop", track, clip)
    return {"stopped": {"track": track, "clip": clip}}


def undo() -> dict:
    """Undo the most recent action in Live.

    Live's undo stack is per-user-action, so a single MCP call may map to one
    or many undo steps. For example, create_midi_clip with 16 notes is one
    undo, but create_track + load_device + create_midi_clip is three. Callers
    that want to fully reverse a multi-step write should invoke undo
    repeatedly and check can_undo.
    """
    osc = get_client()
    osc.send("/live/song/undo")
    can_undo = bool(int(osc.query("/live/song/get/can_undo")[0]))
    return {"undone": True, "can_undo_more": can_undo}


def delete_track(track: int) -> dict:
    get_client().send("/live/song/delete_track", int(track))
    return {"deleted_track": int(track)}


def duplicate_track(track: int) -> dict:
    """Duplicate a track. Live inserts the copy directly after the source."""
    osc = get_client()
    before = int(osc.query("/live/song/get/num_tracks")[0])
    osc.send("/live/song/duplicate_track", int(track))
    return {"duplicated_track": int(track), "new_index": int(track) + 1, "prev_track_count": before}


def rename_track(track: int, name: str) -> dict:
    get_client().send("/live/track/set/name", int(track), str(name))
    return {"track": int(track), "name": str(name)}


def delete_clip(track: int, clip: int) -> dict:
    get_client().send("/live/clip_slot/delete_clip", int(track), int(clip))
    return {"deleted_clip": {"track": int(track), "clip": int(clip)}}


def duplicate_clip(
    track: int,
    clip: int,
    target_track: int | None = None,
    target_clip: int | None = None,
) -> dict:
    """Duplicate a clip to another slot.

    If target_track/target_clip are omitted, the clip is duplicated to the
    next empty slot on the same track. Errors if no empty slot exists.
    """
    osc = get_client()
    tt = int(track) if target_track is None else int(target_track)
    if target_clip is None:
        # Walk clip slots on tt looking for the first empty one. Live's slot
        # count equals num_scenes; probing past that would raise on the Live
        # side. On the same track, start just after the source clip.
        num_scenes = int(osc.query("/live/song/get/num_scenes")[0])
        start = int(clip) + 1 if tt == int(track) else 0
        tc = None
        for slot in range(start, num_scenes):
            reply = osc.query("/live/clip_slot/get/has_clip", tt, slot)
            if not int(reply[2]):
                tc = slot
                break
        if tc is None:
            raise RuntimeError(
                f"No empty clip slot on track {tt} between slot {start} and {num_scenes - 1}. "
                f"Add a scene or pass an explicit target_clip."
            )
    else:
        tc = int(target_clip)
    osc.send(
        "/live/clip_slot/duplicate_clip_to",
        int(track), int(clip), tt, tc,
    )
    return {
        "source": {"track": int(track), "clip": int(clip)},
        "target": {"track": tt, "clip": tc},
    }


def rename_clip(track: int, clip: int, name: str) -> dict:
    get_client().send("/live/clip/set/name", int(track), int(clip), str(name))
    return {"track": int(track), "clip": int(clip), "name": str(name)}


def set_track_arm(track: int, arm: bool) -> dict:
    """Arm or disarm a track for recording / MIDI capture."""
    get_client().send("/live/track/set/arm", int(track), 1 if arm else 0)
    return {"track": int(track), "arm": bool(arm)}


def _parse_color(color: str | int) -> int:
    """Accept '#RRGGBB', 'RRGGBB', or a raw int; return Live's color int."""
    if isinstance(color, int):
        return color
    s = str(color).strip().lstrip("#")
    if len(s) != 6:
        raise ValueError(f"color must be 6-digit hex like '#FF8800', got {color!r}")
    try:
        return int(s, 16)
    except ValueError as e:
        raise ValueError(f"color {color!r} is not valid hex") from e


def create_scene(index: int = -1, name: str | None = None) -> dict:
    """Create a scene. Default -1 appends at the end."""
    osc = get_client()
    before = int(osc.query("/live/song/get/num_scenes")[0])
    osc.send("/live/song/create_scene", int(index))
    new_index = before if index == -1 else int(index)
    if name:
        osc.send("/live/scene/set/name", new_index, str(name))
    return {"created_scene": new_index, "name": name}


def delete_scene(scene: int) -> dict:
    get_client().send("/live/song/delete_scene", int(scene))
    return {"deleted_scene": int(scene)}


def duplicate_scene(scene: int) -> dict:
    """Duplicate a scene. Live inserts the copy directly after the source."""
    get_client().send("/live/song/duplicate_scene", int(scene))
    return {"duplicated_scene": int(scene), "new_index": int(scene) + 1}


def rename_scene(scene: int, name: str) -> dict:
    get_client().send("/live/scene/set/name", int(scene), str(name))
    return {"scene": int(scene), "name": str(name)}


def fire_scene(scene: int) -> dict:
    """Fire a scene (plays every clip in that row). Gated — Claude must ask the user first."""
    get_client().send("/live/scene/fire", int(scene))
    return {"fired_scene": int(scene)}


def set_scene_color(scene: int, color: str | int) -> dict:
    """Set a scene's color. `color` is a hex string like '#FF8800'."""
    rgb = _parse_color(color)
    get_client().send("/live/scene/set/color", int(scene), rgb)
    return {"scene": int(scene), "color": f"#{rgb:06X}"}


def set_clip_color(track: int, clip: int, color: str | int) -> dict:
    """Set a clip's color. `color` is a hex string like '#FF8800'.

    Useful for visually grouping variants — e.g. tint all verse clips one
    color and all chorus clips another so the session view reads at a glance.
    """
    rgb = _parse_color(color)
    get_client().send("/live/clip/set/color", int(track), int(clip), rgb)
    return {"track": int(track), "clip": int(clip), "color": f"#{rgb:06X}"}


def capture_midi() -> dict:
    """Capture recently played MIDI into a new clip on the armed track.

    Live's Capture MIDI looks at the buffer of MIDI input on armed tracks and
    materializes it as a clip at the playhead. The track must be armed and
    have received recent MIDI input; otherwise this is a silent no-op. Use
    set_track_arm first if needed.
    """
    get_client().send("/live/song/capture_midi")
    return {"captured": True}
