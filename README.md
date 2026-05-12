# ableton-mcp

An MCP server that lets Claude observe and compose in Ableton Live 12 via [AbletonOSC](https://github.com/ideoforms/AbletonOSC).

Designed for musicians who want a pair-programming-style collaborator: Claude can read your Live set, explain what's there, and write musical ideas directly into clips — then narrate the choices so you learn as you go.

## Status

**v0** — scaffold. Tools defined and wired to AbletonOSC; not yet end-to-end tested against a live Ableton instance.

## How it works

```
Claude  ←→  MCP (this repo, stdio)  ←→  python-osc  ←→  AbletonOSC remote script  ←→  Ableton Live 12
```

## Tool surface (v0)

**Read** — `get_session_overview`, `get_track_detail`, `get_clip_notes`, `get_transport_state`, `get_selected`

**Write** — `create_midi_clip`, `modify_clip_notes`, `set_tempo`, `set_time_signature`, `create_track`, `fire_clip` / `stop_clip` (gated — Claude must ask the user)

**Guide** — `explain_shortcut`

## Setup

### 1. Install AbletonOSC in Live

Clone [AbletonOSC](https://github.com/ideoforms/AbletonOSC) into Live's MIDI Remote Scripts folder:

- macOS: `~/Music/Ableton/User Library/Remote Scripts/`
- Windows: `Documents\Ableton\User Library\Remote Scripts\`

Then in Live → Preferences → Link/Tempo/MIDI, add `AbletonOSC` as a Control Surface.

### 2. Install this MCP server

```bash
git clone https://github.com/mrinalghosh/ableton-mcp.git
cd ableton-mcp
pip install -e .
```

### 3. Register with Claude

Add to your Claude Code / Claude Desktop MCP config:

```json
{
  "mcpServers": {
    "ableton": {
      "command": "ableton-mcp"
    }
  }
}
```

## Pedagogy

The system prompt asks Claude to **write first, then explain**: when you ask for a musical idea, Claude generates the MIDI directly into Live, then narrates the choices (key, rhythm, voice leading). When you ask "what is this?", Claude grounds itself with `get_selected` before answering.

## Roadmap

- v0.1: end-to-end smoke test against real Live instance; name tracks after creation
- v0.2: device parameter control; automation lanes
- v0.3: scale/key inference; song structure suggestions

## License

MIT — see [LICENSE](LICENSE).
