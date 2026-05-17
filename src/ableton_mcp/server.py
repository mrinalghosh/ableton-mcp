"""MCP server entrypoint. Registers read/write tools over stdio."""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .prompts import SYSTEM_PROMPT
from .tools import analyze, read, write

mcp = FastMCP("ableton-mcp", instructions=SYSTEM_PROMPT)

# --- Read tools ---
mcp.tool(description="Tempo, time signature, and summary of every track.")(
    read.get_session_overview
)
mcp.tool(description="Devices, clip slots, and routing for one track.")(
    read.get_track_detail
)
mcp.tool(description="MIDI notes in a clip: pitch, start (beats), duration, velocity.")(
    read.get_clip_notes
)
mcp.tool(description="Transport state: playing, current beat, loop.")(
    read.get_transport_state
)
mcp.tool(
    description="What the user currently has selected in Live. Call this first when the user asks 'what is this?'."
)(read.get_selected)
mcp.tool(
    description="List a device's parameters with current value, min, and max. Use before set_device_parameter to discover names."
)(read.get_device_parameters)
mcp.tool(
    description=(
        "Browse Live's device library. category is one of 'instruments', "
        "'drums', 'sounds', 'audio_effects', 'midi_effects'. path is a list "
        "of folder names to descend into (empty for the root). Returns "
        "children with is_folder, is_loadable, and has_children flags. Use "
        "to discover what to pass to load_device."
    )
)(read.list_browser)

# --- Analysis tools ---
mcp.tool(
    description=(
        "Estimate the musical key of a single MIDI clip via Krumhansl-Kessler "
        "correlation on a duration-weighted pitch-class histogram. Returns "
        "the best-fit key, confidence, and runner-up (often the relative "
        "major/minor — small margin means ambiguous)."
    )
)(analyze.detect_clip_key)
mcp.tool(
    description=(
        "Estimate the key of a whole track by aggregating notes across every "
        "MIDI clip on it. More robust than detect_clip_key for short or "
        "chromatic clips."
    )
)(analyze.detect_track_key)
mcp.tool(
    description=(
        "Estimate the key of the whole set by aggregating every MIDI clip on "
        "every track. Drum tracks are excluded by default — their pitch "
        "content is percussive mapping, not tonal."
    )
)(analyze.detect_session_key)

# --- Write tools ---
mcp.tool(
    description=(
        "Create a MIDI clip and fill with notes. Lowest-level write — prefer "
        "create_chord_progression or create_drum_pattern when the idea fits "
        "those shapes, since they take a much shorter spec."
    )
)(write.create_midi_clip)
mcp.tool(description="Replace all notes in an existing MIDI clip.")(write.modify_clip_notes)
mcp.tool(
    description=(
        "Write a chord progression as block chords into a MIDI clip. `chords` "
        "is a list of tokens — roman numerals ('I', 'vi', 'V7', 'bVII', 'ii°') "
        "or absolute chord names ('Cm', 'F#maj7', 'G7'); the two may mix. "
        "Roman tokens require `key` (e.g. 'C' or 'Am'). `voicing` is 'triad' "
        "(default), 'seventh', or 'power' — applied only to tokens without "
        "an explicit suffix. `beats_per_chord` may be a scalar or a per-chord "
        "list. PREFER this over create_midi_clip when writing harmony."
    )
)(write.create_chord_progression)
mcp.tool(
    description=(
        "Write a drum pattern from step strings into a MIDI clip. `pattern` "
        "is a dict {voice: step_string}. Voice keys can be drum-map names "
        "('kick', 'snare', 'hat', 'open_hat', 'clap', 'tom_low', 'ride', "
        "...), note names ('C1', 'D1'), or raw MIDI ints. Step chars: "
        "'x'/'X'/'1' = hit, '.'/'-'/'_'/'0'/' ' = rest, '2'-'9' = hit at "
        "scaled velocity ('9' loudest). Rows may have different lengths "
        "(mix 16ths and triplets). "
        "PREFER this over create_midi_clip when writing drums."
    )
)(write.create_drum_pattern)
mcp.tool(description="Set song tempo (BPM).")(write.set_tempo)
mcp.tool(description="Set song time signature.")(write.set_time_signature)
mcp.tool(description="Create a new MIDI or audio track at end of set.")(write.create_track)
mcp.tool(
    description=(
        "Load a device (instrument, audio effect, or MIDI effect) from Live's "
        "browser onto a track. Pass the full path of folder names ending at a "
        "loadable item (use list_browser to discover). The track is selected "
        "and the device is appended to its device chain."
    )
)(write.load_device)
mcp.tool(
    description="Start playing a clip. ASK THE USER FIRST before calling — surprise playback is disruptive."
)(write.fire_clip)
mcp.tool(
    description="Stop a clip. Less disruptive than fire_clip, but still avoid stopping mid-performance without checking with the user."
)(write.stop_clip)
mcp.tool(
    description="Set one parameter on a device. Prefer addressing by name. Value is clamped to the parameter range."
)(write.set_device_parameter)
mcp.tool(
    description="Set track volume. 0.0 silence, 0.85 unity (0 dB), 1.0 maximum (+6 dB). Clamped to [0, 1]."
)(write.set_track_volume)
mcp.tool(
    description="Set track pan. -1.0 hard left, 0.0 center, 1.0 hard right. Clamped to [-1, 1]."
)(write.set_track_panning)
mcp.tool(description="Mute or unmute a track.")(write.set_track_mute)
mcp.tool(description="Solo or unsolo a track.")(write.set_track_solo)
mcp.tool(
    description=(
        "Write a clip-level automation envelope for a device parameter. "
        "points is a list of {time, value} or {time, duration, value} "
        "(beats relative to clip start); when duration is omitted it tiles "
        "to the next point. Live only supports flat step segments — for a "
        "smooth ramp, pass many closely spaced breakpoints. Existing "
        "automation is not cleared first; call clear_clip_automation first "
        "if you want a fresh start. Values clamped to the parameter range."
    )
)(write.set_clip_automation)
mcp.tool(
    description=(
        "Sample an automation envelope at evenly spaced times in [start, end]. "
        "Live's LOM doesn't expose breakpoints, so reads are sampled."
    )
)(write.sample_clip_automation)
mcp.tool(
    description=(
        "Clear automation on a clip. Pass device+parameter to clear one "
        "envelope, or omit them to clear every envelope on the clip."
    )
)(write.clear_clip_automation)
mcp.tool(
    description=(
        "Undo the most recent action in Live. Note: a single MCP write may "
        "map to multiple Live undo steps (e.g. create_track + load_device + "
        "create_midi_clip is three undos). Call repeatedly to fully reverse "
        "a multi-step change; the reply's can_undo_more flag indicates "
        "whether more history remains."
    )
)(write.undo)
mcp.tool(
    description=(
        "Edit a track. `op` is 'delete', 'duplicate', or 'rename'. "
        "'rename' requires `name`. Duplicate inserts the copy directly after "
        "the source. ASK THE USER FIRST for op='delete' — losing a track is "
        "destructive."
    )
)(write.edit_track)
mcp.tool(
    description=(
        "Edit a clip. `op` is 'delete', 'duplicate', or 'rename'. "
        "'rename' requires `name`. Duplicate with no target lands in the "
        "next empty slot on the same track; pass target_track/target_clip "
        "for explicit placement. ASK THE USER FIRST for op='delete' — "
        "losing a clip is destructive."
    )
)(write.edit_clip)
mcp.tool(
    description=(
        "Arm or disarm a track for recording / MIDI capture. Required before "
        "capture_midi will pick up input from that track. ASK THE USER FIRST "
        "— arming changes how Live responds to input and can disrupt their "
        "session setup."
    )
)(write.set_track_arm)
mcp.tool(
    description=(
        "Capture recently played MIDI from armed tracks into a new clip at "
        "the playhead. The track must be armed and have received recent MIDI "
        "input — otherwise this is a silent no-op. Use set_track_arm first "
        "if the user wants you to riff on what they're about to play."
    )
)(write.capture_midi)
mcp.tool(
    description="Create a scene. Default index=-1 appends at the end; optionally name it on creation."
)(write.create_scene)
mcp.tool(
    description=(
        "Edit a scene. `op` is 'delete', 'duplicate', or 'rename'. "
        "'rename' requires `name`. Duplicate inserts the copy directly after "
        "the source. ASK THE USER FIRST for op='delete' — losing a scene is "
        "destructive."
    )
)(write.edit_scene)
mcp.tool(
    description=(
        "Fire a scene — plays every clip in that row. ASK THE USER FIRST "
        "before calling; whole-row playback is even more disruptive than a "
        "single clip."
    )
)(write.fire_scene)
mcp.tool(
    description="Set a scene's color. Pass a hex string like '#FF8800'."
)(write.set_scene_color)
mcp.tool(
    description=(
        "Set a clip's color. Pass a hex string like '#FF8800'. Use to "
        "visually group variants — e.g. all verse clips one color, all "
        "chorus clips another."
    )
)(write.set_clip_color)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
