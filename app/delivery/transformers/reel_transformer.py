"""
Reel-specific transformer.
"""

from typing import Dict, Any, List

from app.delivery.transformers.base import BaseBriefTransformer


class ReelTransformer(BaseBriefTransformer):
    """Transform ReelContent JSON into Markdown."""

    def transform_content(self, content_json: Dict[str, Any]) -> str:
        """
        Transform ReelContent into Markdown.

        Expected content_json structure:
        {
            "hook_line": str,
            "body": List[str],
            "punch_line": str,
            "screenshot_line": str,
            "estimated_duration_seconds": int,
            "text_overlay_suggestion": Optional[str],
            "internal_notes": {
                "mode_used": str,
                "emotional_journey_achieved": str,
                "why_this_works": str
            }
        }
        """
        hook_line = content_json.get("hook_line", "")
        body: List[str] = content_json.get("body", [])
        punch_line = content_json.get("punch_line", "")
        screenshot_line = content_json.get("screenshot_line", "")
        duration = content_json.get("estimated_duration_seconds", 0)
        text_overlay = content_json.get("text_overlay_suggestion", "")
        internal_notes = content_json.get("internal_notes", {})

        # Build body lines
        body_lines = "\n".join(
            [f'{i + 1}. "{line}"' for i, line in enumerate(body)]
        )

        # Get voice suggestion from mode
        mode_used = internal_notes.get("mode_used", "")
        voice_suggestion = self._get_voice_suggestion(mode_used)

        return f"""
## 🎯 HOOK (First 2 seconds)

> "{hook_line}"

---

## 📝 SCRIPT

{body_lines}

---

## 💥 PUNCH LINE

> "{punch_line}"

---

## 📱 PRODUCTION NOTES

| Element | Value |
|---------|-------|
| **Duration** | ~{duration} seconds |
| **Text Overlay** | "{text_overlay}" |
| **Screenshot Line** | "{screenshot_line}" |
| **Voice Suggestion** | {voice_suggestion} |

---

## 💡 WHY THIS WORKS

> {internal_notes.get("why_this_works", "N/A")}

"""

    def _get_voice_suggestion(self, mode: str) -> str:
        """Get voice tone suggestion based on mode."""
        voice_map = {
            "ROAST_MASTER": "Direct, slightly confrontational, no softening",
            "MIRROR": "Warm, knowing, like talking to a friend",
            "ORACLE": "Measured, prophetic, slight mystery",
            "SURGEON": "Clinical, precise, matter-of-fact",
            "ROAST_TO_SURGEON": "Start sharp, transition to helpful",
            "ROAST_TO_MIRROR": "Start confrontational, end with understanding",
            "ORACLE_SURGEON": "Wise but practical",
            "ORACLE_COMPRESSED": "Zen-like brevity",
        }
        return voice_map.get(mode, "Conversational, authentic")
