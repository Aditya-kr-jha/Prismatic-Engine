"""
Carousel-specific transformer.
"""

from typing import Dict, Any, List

from app.delivery.transformers.base import BaseBriefTransformer


class CarouselTransformer(BaseBriefTransformer):
    """Transform CarouselContent JSON into Markdown."""

    def transform_content(self, content_json: Dict[str, Any]) -> str:
        """
        Transform CarouselContent into Markdown.

        Expected content_json structure:
        {
            "slides": [
                {
                    "slide_number": int,
                    "headline": str,
                    "body": Optional[str],
                    "design_note": Optional[str]
                },
                ...
            ],
            "cover_slide_text": str,
            "screenshot_slide": int,
            "internal_notes": {
                "mode_used": str,
                "mode_transitions": Optional[List[str]],
                "emotional_journey_achieved": str,
                "why_this_works": str
            }
        }
        """
        slides: List[Dict] = content_json.get("slides", [])
        cover_text = content_json.get("cover_slide_text", "")
        screenshot_slide = content_json.get("screenshot_slide", 1)
        internal_notes = content_json.get("internal_notes", {})

        # Build slides section
        slides_md = self._render_slides(slides, screenshot_slide)

        return f"""
## 📊 SLIDES ({len(slides)} total)

**Cover/Grid Text:** "{cover_text}"

**Screenshot Slide:** #{screenshot_slide}

---

{slides_md}

---

## 💡 WHY THIS WORKS

> {internal_notes.get("why_this_works", "N/A")}

---

## 🎨 DESIGN NOTES

- Use consistent color scheme throughout
- Slide 1 (Cover) should be bold and eye-catching
- Screenshot slide (#{screenshot_slide}) should stand alone as shareable
- Keep text readable: max 20 words per slide

"""

    def _render_slides(self, slides: List[Dict], screenshot_slide: int) -> str:
        """Render all slides as Markdown."""
        parts = []

        for slide in slides:
            num = slide.get("slide_number", 0)
            headline = slide.get("headline", "")
            body = slide.get("body", "")
            design_note = slide.get("design_note", "")

            # Mark cover and screenshot slides
            label = ""
            if num == 1:
                label = " — COVER"
            elif num == screenshot_slide:
                label = " — 📸 SCREENSHOT"

            slide_md = f"""### [SLIDE {num}{label}]

> **{headline}**
"""
            if body:
                slide_md += f"""
> {body}
"""
            if design_note:
                slide_md += f"""
*Design: {design_note}*
"""
            parts.append(slide_md)

        return "\n".join(parts)
