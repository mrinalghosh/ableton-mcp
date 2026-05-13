# ableton-mcp

An MCP server that lets Claude observe and compose in Ableton Live 12 via [AbletonOSC](https://github.com/ideoforms/AbletonOSC).

Designed for musicians who want a pair-programming-style collaborator: Claude can read your Live set, explain what's there, and write musical ideas directly into clips — then narrate the choices so you learn as you go.

## Status

**v0.3** — smoke-tested end-to-end against Live 12. Claude can browse Live's library and load instruments onto tracks (requires the [forked AbletonOSC](https://github.com/mrinalghosh/AbletonOSC) tracked here as a submodule — adds a `BrowserHandler` exposing `application.browser` over OSC).

## How it works

```
Claude  ←→  MCP (this repo, stdio)  ←→  python-osc  ←→  AbletonOSC remote script  ←→  Ableton Live 12
```

## Tool surface (v0.3)

**Read** — `get_session_overview`, `get_track_detail`, `get_clip_notes`, `get_transport_state`, `get_selected`, `get_device_parameters`, `list_browser`

**Write** — `create_midi_clip`, `modify_clip_notes`, `set_tempo`, `set_time_signature`, `create_track`, `load_instrument`, `set_device_parameter`, `set_track_volume` / `set_track_panning` / `set_track_mute` / `set_track_solo`, `fire_clip` / `stop_clip` (gated — Claude must ask the user)

## Setup

### 1. Install AbletonOSC in Live

This repo bundles a [forked AbletonOSC](https://github.com/mrinalghosh/AbletonOSC) as a submodule with a `BrowserHandler` added for `list_browser` / `load_instrument`. Clone with submodules and symlink into Live's MIDI Remote Scripts folder:

```bash
git clone --recurse-submodules https://github.com/mrinalghosh/ableton-mcp.git
cd ableton-mcp
# macOS
ln -s "$PWD/AbletonOSC" "$HOME/Music/Ableton/User Library/Remote Scripts/AbletonOSC"
```

- macOS: `~/Music/Ableton/User Library/Remote Scripts/`
- Windows: `Documents\Ableton\User Library\Remote Scripts\`

Then in Live → Settings → Link, Tempo & MIDI, add `AbletonOSC` as a Control Surface.

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

## Known quirks

- **Track/clip names come back with hyphens instead of spaces.** AbletonOSC normalizes whitespace in string responses, so a track displayed in Live as `1 MIDI` is reported as `1-MIDI`. We pass this through unchanged — reversing it would corrupt names the user actually wrote with hyphens.

## Roadmap

- ~~v0.1: end-to-end smoke test against real Live instance; name tracks after creation~~ ✅
- ~~v0.2: device parameter control (`get_device_parameters`, `set_device_parameter`); per-track mixer (volume, pan, mute, solo)~~ ✅
- ~~v0.3: browse Live's Library and load instruments/effects onto tracks (forked AbletonOSC adds `BrowserHandler`)~~ ✅
- v0.4: clip automation lanes (time-varying parameter envelopes inside a clip)
- v0.5: scale/key inference; song structure suggestions

## License

MIT — see [LICENSE](LICENSE).
