"""
Telegram bot exporter.

Sends delivery briefs via Telegram Bot API.
"""

import asyncio
import logging
import re
from typing import List, Optional, Tuple

import httpx

from app.config import settings
from app.delivery.schemas import DeliveryBrief, WeekPackage

logger = logging.getLogger(__name__)


def escape_markdown(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2.

    Telegram MarkdownV2 requires escaping these characters:
    _ * [ ] ( ) ~ ` > # + - = | { } . !
    """
    if not text:
        return ""
    # Characters that need escaping in MarkdownV2
    escape_chars = r"_*[]()~`>#+=|{}.!-"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)


def escape_markdown_v1(text: str) -> str:
    """
    Escape special characters for Telegram Markdown (v1).

    More limited escaping for legacy Markdown mode.
    """
    if not text:
        return ""
    # For Markdown v1, mainly escape _ and *
    text = text.replace("_", "\\_")
    text = text.replace("*", "\\*")
    text = text.replace("`", "\\`")
    text = text.replace("[", "\\[")
    return text


class TelegramExporter:
    """Send delivery briefs via Telegram Bot."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ):
        """
        Initialize Telegram exporter.

        Args:
            bot_token: Telegram bot token (from @BotFather)
            chat_id: Your Telegram chat ID
        """
        self.bot_token = bot_token or getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        self.chat_id = chat_id or getattr(settings, "TELEGRAM_CHAT_ID", None)
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    @property
    def is_configured(self) -> bool:
        """Check if Telegram is properly configured."""
        return bool(self.bot_token and self.chat_id)

    async def send_week(self, package: WeekPackage) -> Tuple[int, List[str]]:
        """
        Send all briefs for a week.

        Args:
            package: WeekPackage containing all briefs

        Returns:
            Tuple of (messages_sent, errors)
        """
        if not self.is_configured:
            logger.warning("Telegram not configured, skipping delivery")
            return 0, ["Telegram not configured"]

        messages_sent = 0
        errors: List[str] = []

        # Send week header
        header = self._format_week_header(package)
        success, error = await self._send_message(header)
        if success:
            messages_sent += 1
        else:
            errors.append(error)

        # Send each brief (with rate limiting)
        for brief in sorted(package.briefs, key=lambda b: b.slot_number):
            message = self._format_brief_message(brief)
            success, error = await self._send_message(message)

            if success:
                messages_sent += 1
            else:
                errors.append(f"Slot {brief.slot_number}: {error}")

            # Rate limit: 1 message per second
            await asyncio.sleep(1)

        logger.info(f"Telegram delivery: {messages_sent} sent, {len(errors)} errors")

        return messages_sent, errors

    async def _send_message(
        self,
        text: str,
        parse_mode: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Send a single message via Telegram API.

        Args:
            text: Message text (plain text, no formatting)
            parse_mode: Optional parse mode (None for plain text)

        Returns:
            Tuple of (success, error_message)
        """
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "chat_id": self.chat_id,
                    "text": text,
                    "disable_web_page_preview": True,
                }
                # Only add parse_mode if specified
                if parse_mode:
                    payload["parse_mode"] = parse_mode

                response = await client.post(
                    f"{self.base_url}/sendMessage",
                    json=payload,
                    timeout=30,
                )

                if response.status_code == 200:
                    return True, None
                else:
                    error = response.json().get("description", "Unknown error")
                    logger.error(f"Telegram API error: {error}")
                    return False, error

        except Exception as e:
            logger.exception("Telegram send failed")
            return False, str(e)

    def _format_week_header(self, package: WeekPackage) -> str:
        """Format week header message (plain text, no Markdown)."""
        return f"""📅 Week {package.week_number}, {package.week_year}

📊 {package.total_items} posts ready:
• 🎬 Reels: {package.reels_count}
• 📊 Carousels: {package.carousels_count}
• 💬 Quotes: {package.quotes_count}

⭐ Avg Quality: {package.avg_quality_score:.1f}/10
⚠️ Need Attention: {package.items_needing_attention}

Briefs incoming..."""

    def _format_brief_message(self, brief: DeliveryBrief) -> str:
        """Format a single brief for Telegram (plain text, no Markdown)."""
        emoji_map = {"REEL": "🎬", "CAROUSEL": "📊", "QUOTE": "💬"}
        emoji = emoji_map.get(brief.format_type, "📝")

        time_str = (
            brief.scheduled_time.strftime("%I:%M %p")
            if brief.scheduled_time
            else "TBD"
        )
        quality = brief.quality_scores.average
        quality_indicator = "✅" if brief.quality_scores.passed_all else "⚠️"

        # Extract key content based on format
        preview = self._extract_preview(brief)

        return f"""{emoji} {brief.format_type} #{brief.slot_number}
📅 {brief.day_of_week.title()} @ {time_str}
🏷️ {brief.pillar} | {brief.resolved_mode}
⭐ {quality:.1f}/10 {quality_indicator}

{preview}

File: {brief.filename}"""

    def _extract_preview(self, brief: DeliveryBrief) -> str:
        """Extract a preview snippet from the brief."""
        content = brief.content_markdown

        # Try to find the hook or quote
        if "HOOK" in content:
            start = content.find('> "')
            if start != -1:
                end = content.find('"', start + 3)
                if end != -1:
                    hook_text = content[start + 3 : end]
                    return f'🎯 "{hook_text}"'

        if "QUOTE TEXT" in content:
            start = content.find('> "')
            if start != -1:
                end = content.find('"', start + 3)
                if end != -1:
                    quote_text = content[start + 3 : end]
                    return f'💬 "{quote_text}"'

        # Fallback: first 150 chars, cleaned up
        preview = content[:150].replace("\n", " ").replace("#", "").strip()
        # Remove markdown syntax
        preview = re.sub(r"\*+", "", preview)
        preview = re.sub(r"_+", "", preview)
        preview = re.sub(r"\|", "", preview)
        return f"{preview}..."
