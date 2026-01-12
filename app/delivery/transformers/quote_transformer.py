"""
Quote-specific transformer.
"""

from typing import Dict, Any

from app.delivery.transformers.base import BaseBriefTransformer


class QuoteTransformer(BaseBriefTransformer):
    """Transform QuoteContent JSON into Markdown."""

    def transform_content(self, content_json: Dict[str, Any]) -> str:
        """
        Transform QuoteContent into Markdown.

        Expected content_json structure:
        {
            "quote_text": str,
            "quote_text_alt": str,
            "caption": Optional[str],
            "internal_notes": {
                "mode_used": str,
                "primary_emotion_targeted": str,
                "why_this_works": str,
                "tattoo_test_pass": bool
            }
        }
        """
        quote_text = content_json.get("quote_text", "")
        quote_alt = content_json.get("quote_text_alt", "")
        caption = content_json.get("caption", "")
        internal_notes = content_json.get("internal_notes", {})

        tattoo_pass = internal_notes.get("tattoo_test_pass", False)
        tattoo_indicator = "✅ Yes" if tattoo_pass else "❌ No"

        return f"""
## 💬 QUOTE TEXT (Primary)

> "{quote_text}"

---

## 💬 ALTERNATIVE VERSION

> "{quote_alt}"

---

## 📝 CAPTION (for Instagram)

> {caption if caption else "_No caption suggested — consider adding context_"}

---

## 📱 PRODUCTION NOTES

| Element | Value |
|---------|-------|
| **Primary Emotion** | {internal_notes.get("primary_emotion_targeted", "N/A")} |
| **Tattoo Test** | {tattoo_indicator} |
| **Font Style** | Bold, minimal, high contrast |
| **Image Size** | 1080 × 1350px (4:5 ratio) |

---

## 💡 WHY THIS WORKS

> {internal_notes.get("why_this_works", "N/A")}

"""
