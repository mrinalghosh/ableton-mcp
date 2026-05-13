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

# --- Write tools ---
mcp.tool(
    description="Create a MIDI clip and fill with notes. Use this when the user wants a musical idea written into the set."
)(write.create_midi_clip)
mcp.tool(description="Replace all notes in an existing MIDI clip.")(write.modify_clip_notes)
mcp.tool(description="Set song tempo (BPM).")(write.set_tempo)
mcp.tool(description="Set song time signature.")(write.set_time_signature)
mcp.tool(description="Create a new MIDI or audio track at end of set.")(write.create_track)
mcp.tool(
    description="Start playing a clip. ASK THE USER FIRST before calling — surprise playback is disruptive."
)(write.fire_clip)
mcp.tool(description="Stop a clip.")(write.stop_clip)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
