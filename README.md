# ableton-mcp

An MCP server that lets Claude observe and compose in Ableton Live 12 via [AbletonOSC](https://github.com/ideoforms/AbletonOSC).

Designed for musicians who want a pair-programming-style collaborator: Claude can read your Live set, explain what's there, and write musical ideas directly into clips — then narrate the choices so you learn as you go.

## Status

**v0.8** — high-level composition tools and a simpler write API. `create_chord_progression` (roman numerals or chord names + key) and `create_drum_pattern` (step strings like `x...x...x...x...`) let Claude express harmonic and rhythmic ideas in a few tokens instead of emitting raw note lists. The duplicate/delete/rename trio per object collapses into one `edit_track` / `edit_clip` / `edit_scene` tool each, cutting the surface area Claude has to reason about. Browser listing in the forked AbletonOSC now caches per-folder results, so the first hit pays the disk walk and subsequent `list_browser` calls return instantly (previously they tripped the 2.0s OSC timeout on large libraries). v0.7 added analyze tools (`detect_clip_key`, `detect_track_key`, `detect_session_key`) using Krumhansl-Schmuckler key profiles. Builds on v0.6 scenes + color, v0.5 revise-and-respond (undo, capture MIDI), v0.4 automation, and v0.3 browser/loading.

## How it works

```
Claude  ←→  MCP (this repo, stdio)  ←→  python-osc  ←→  AbletonOSC remote script  ←→  Ableton Live 12
```

## Tool surface (v0.8)

**Read** — `get_session_overview`, `get_track_detail`, `get_clip_notes`, `get_transport_state`, `get_selected`, `get_device_parameters`, `list_browser`, `sample_clip_automation`

**Analyze** — `detect_clip_key`, `detect_track_key`, `detect_session_key`

**Revise** — `undo`

**Write** — `create_midi_clip`, `modify_clip_notes`, `create_chord_progression`, `create_drum_pattern`, `set_tempo`, `set_time_signature`, `create_track`, `load_device`, `set_device_parameter`, `set_clip_automation` / `clear_clip_automation`, `set_track_volume` / `set_track_panning` / `set_track_mute` / `set_track_solo` / `set_track_arm`, `edit_track` / `edit_clip` / `edit_scene` (duplicate, delete, rename), `create_scene`, `set_clip_color` / `set_scene_color`, `capture_midi`, `fire_clip` / `fire_scene` / `stop_clip` (gated — Claude must ask the user)

## Setup

### 1. Install AbletonOSC in Live

This repo bundles a [forked AbletonOSC](https://github.com/mrinalghosh/AbletonOSC) as a submodule with a `BrowserHandler` added for `list_browser` / `load_device`. Clone with submodules and symlink into Live's MIDI Remote Scripts folder:

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
- **`undo` is per-Live-action, not per-MCP-tool.** A single MCP write may correspond to several Live undo steps (e.g. `create_track` + `load_device` + `create_midi_clip` is three undos), or to one (a `modify_clip_notes` with 16 notes is one). To fully reverse a multi-step change, call `undo` repeatedly — the reply's `can_undo_more` flag indicates whether more history remains. AbletonOSC doesn't expose undo grouping, so we can't fix this in the wrapper.

## Roadmap

- ~~v0.1: end-to-end smoke test against real Live instance; name tracks after creation~~
- ~~v0.2: device parameter control (`get_device_parameters`, `set_device_parameter`); per-track mixer (volume, pan, mute, solo)~~
- ~~v0.3: browse Live's Library and load instruments/effects onto tracks (forked AbletonOSC adds `BrowserHandler`)~~
- ~~v0.4: clip automation lanes — read/write parameter envelopes inside a clip (forked AbletonOSC adds `AutomationHandler`)~~
- ~~v0.5: revise-and-respond — `undo`; `duplicate_clip` / `delete_clip` / `delete_track` / `rename_track` / `rename_clip`; capture MIDI (record-arm + Capture) so Claude can riff on what you just played~~
- ~~v0.6: scene management (`create_scene`, `fire_scene`, `delete_scene`, `rename_scene`); clip color so Claude can visually group variants~~
- ~~v0.7: scale/key inference — `detect_clip_key` / `detect_track_key` / `detect_session_key` using Krumhansl-Schmuckler key profiles, plus pitch utility helpers~~
- ~~v0.8: high-level composition tools (`create_chord_progression`, `create_drum_pattern`) so Claude can express musical ideas in a few tokens; collapse per-object dup/delete/rename into single `edit_track` / `edit_clip` / `edit_scene` tools; cache browser folder listings in AbletonOSC fork to fix `list_browser` timeouts on large libraries~~
- v0.9: quantize captured MIDI — close the capture loop with `quantize_clip`

## License

MIT — see [LICENSE](LICENSE).
