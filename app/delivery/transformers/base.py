"""
Base transformer for converting GeneratedContent to Markdown.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

from app.delivery.schemas import (
    QualityScoreSummary,
    EmotionalJourneySummary,
    EmotionalArcSummary,
)


class BaseBriefTransformer(ABC):
    """
    Abstract base class for format-specific transformers.

    Each format (Reel, Carousel, Quote) has its own transformer
    that knows how to render that format's content_json into Markdown.
    """

    @abstractmethod
    def transform_content(self, content_json: Dict[str, Any]) -> str:
        """
        Transform format-specific content_json into Markdown.

        Args:
            content_json: The content_json from GeneratedContent

        Returns:
            Markdown string for the content section
        """
        pass

    def build_quality_summary(
        self, critique_scores: Dict[str, int]
    ) -> QualityScoreSummary:
        """Build QualityScoreSummary from critique_scores dict."""
        return QualityScoreSummary(
            scroll_stop_power=critique_scores.get("scroll_stop_power", 0),
            ai_voice_risk=critique_scores.get("ai_voice_risk", 0),
            share_impulse=critique_scores.get("share_impulse", 0),
            emotional_precision=critique_scores.get("emotional_precision", 0),
            mode_progression=critique_scores.get("mode_progression", 0),
            pacing_breath=critique_scores.get("pacing_breath", 0),
            format_execution=critique_scores.get("format_execution", 0),
        )

    def build_emotional_journey(
        self, journey: Dict[str, str]
    ) -> EmotionalJourneySummary:
        """Build EmotionalJourneySummary from emotional_journey dict."""
        return EmotionalJourneySummary(
            state_1=journey.get("state_1", "Unknown"),
            state_2=journey.get("state_2", "Unknown"),
            state_3=journey.get("state_3", "Unknown"),
        )

    def render_header(
        self,
        format_type: str,
        slot_number: int,
        day_of_week: str,
        scheduled_date: str,
        scheduled_time: str,
        pillar: str,
        resolved_mode: str,
        quality_avg: float,
    ) -> str:
        """Render the common header section."""
        emoji_map = {
            "REEL": "🎬",
            "CAROUSEL": "📊",
            "QUOTE": "💬",
        }
        emoji = emoji_map.get(format_type, "📝")

        return f"""# {emoji} {format_type} #{slot_number} — {day_of_week.title()}, {scheduled_date} @ {scheduled_time}

| Pillar | Mode | Quality |
|--------|------|---------|
| {pillar} | {resolved_mode} | ⭐ {quality_avg:.1f}/10 |

---
"""

    def render_emotional_journey(self, journey: EmotionalJourneySummary) -> str:
        """Render the emotional journey section. DEPRECATED: Use render_emotional_arc."""
        return f"""
## 🎭 EMOTIONAL JOURNEY (DEPRECATED)

| State | Description |
|-------|-------------|
| **Start** | {journey.state_1} |
| **Middle** | {journey.state_2} |
| **End** | {journey.state_3} |

---
"""

    def render_emotional_arc(self, arc: "EmotionalArcSummary") -> str:
        """Render the 5-stage emotional arc section for Reels/Carousels."""
        return f"""
## 🎭 EMOTIONAL ARC

| Stage | Description |
|-------|-------------|
| **Entry State** | {arc.entry_state} |
| **Destabilization** | {arc.destabilization_trigger} |
| **Resistance Point** | {arc.resistance_point} |
| **Breakthrough** | {arc.breakthrough_moment} |
| **Landing** | {arc.landing_state} |

**Pacing Note:** {arc.pacing_note if arc.pacing_note else "N/A"}

---
"""

    def render_quality_scores(self, scores: QualityScoreSummary) -> str:
        """Render the quality scores section."""

        def score_indicator(score: int, threshold: int = 6) -> str:
            return "✅" if score >= threshold else "⚠️"

        ai_indicator = score_indicator(scores.ai_voice_risk, 7)  # Higher threshold

        return f"""
## ✅ QUALITY SCORES

| Metric | Score |
|--------|-------|
| Scroll Stop Power | {scores.scroll_stop_power}/10 {score_indicator(scores.scroll_stop_power)} |
| AI Voice Risk | {scores.ai_voice_risk}/10 {ai_indicator} |
| Share Impulse | {scores.share_impulse}/10 {score_indicator(scores.share_impulse)} |
| Emotional Precision | {scores.emotional_precision}/10 {score_indicator(scores.emotional_precision)} |
| Mode Progression | {scores.mode_progression}/10 {score_indicator(scores.mode_progression)} |
| Pacing & Breath | {scores.pacing_breath}/10 {score_indicator(scores.pacing_breath)} |
| Format Execution | {scores.format_execution}/10 {score_indicator(scores.format_execution)} |

---
"""

    def render_metadata_footer(
        self,
        generated_content_id: str,
        schedule_id: str,
        atom_id: str,
        angle_name: str,
        trace_id: str,
        generated_at: str,
        attempts: int,
    ) -> str:
        """Render the collapsible metadata footer with traceability IDs."""
        return f"""
<details>
<summary>📊 Source Metadata (click to expand)</summary>

- **Generated Content ID:** `{generated_content_id}`
- **Schedule ID:** `{schedule_id}`
- **Atom ID:** `{atom_id}`
- **Angle:** {angle_name}
- **Trace ID:** `{trace_id}`
- **Generated:** {generated_at}
- **Attempts:** {attempts}

</details>
"""
