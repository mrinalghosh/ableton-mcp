"""Guidance tools — Live workflow shortcuts surfaced as structured data."""
from __future__ import annotations

# Keyed by a short action name. macOS-first since the user is on Darwin;
# Windows equivalents in parentheses.
SHORTCUTS: dict[str, dict[str, str]] = {
    "duplicate_clip": {
        "keys": "Cmd+D (Ctrl+D)",
        "context": "Select a clip in Session View, then Cmd+D duplicates it to the next slot.",
    },
    "new_midi_track": {
        "keys": "Cmd+Shift+T (Ctrl+Shift+T)",
        "context": "Adds a new MIDI track after the currently selected track.",
    },
    "new_audio_track": {
        "keys": "Cmd+T (Ctrl+T)",
        "context": "Adds a new audio track.",
    },
    "toggle_session_arrangement": {
        "keys": "Tab",
        "context": "Switch between Session View (clips) and Arrangement View (timeline).",
    },
    "play_stop": {
        "keys": "Space",
        "context": "Play/stop transport. Shift+Space plays from the selection.",
    },
    "draw_mode": {
        "keys": "B",
        "context": "Toggle Draw Mode in the MIDI editor for drawing in notes with the mouse.",
    },
    "loop_selection": {
        "keys": "Cmd+L (Ctrl+L)",
        "context": "Loop the current selection in Arrangement View.",
    },
    "quantize": {
        "keys": "Cmd+U (Ctrl+U)",
        "context": "Quantize selected MIDI notes to the current grid.",
    },
}


def explain_shortcut(action: str) -> dict:
    """Return the Live keyboard shortcut for an action, with context."""
    entry = SHORTCUTS.get(action)
    if not entry:
        return {
            "action": action,
            "found": False,
            "known_actions": sorted(SHORTCUTS.keys()),
        }
    return {"action": action, "found": True, **entry}
