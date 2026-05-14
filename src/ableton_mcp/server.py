"""MCP server entrypoint. Registers read/write tools over stdio."""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .prompts import SYSTEM_PROMPT
from .tools import read, write

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

# --- Write tools ---
mcp.tool(
    description="Create a MIDI clip and fill with notes. Use this when the user wants a musical idea written into the set."
)(write.create_midi_clip)
mcp.tool(description="Replace all notes in an existing MIDI clip.")(write.modify_clip_notes)
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
mcp.tool(description="Stop a clip.")(write.stop_clip)
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
        "points is a list of {time, value} or {time, duration, value} entries "
        "(beats relative to clip start). Existing automation is not cleared "
        "first — use clear_clip_automation for a fresh start. Values clamped "
        "to the parameter range."
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


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
