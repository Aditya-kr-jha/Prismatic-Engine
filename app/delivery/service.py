"""
Delivery Service - Main orchestrator for Phase 5 Delivery.

Transforms GeneratedContent into human-readable briefs
and delivers via files + Telegram.
"""

import asyncio
import logging
import time
import uuid
from typing import cast, List, Optional, TYPE_CHECKING

from sqlmodel import Session

from app.db.db_session import get_session
from app.delivery import db_services
from app.delivery.schemas import (
    DeliveryBrief,
    DeliveryResult,
    WeekPackage,
)
from app.delivery.transformers import get_transformer
from app.delivery.exporters.markdown_exporter import MarkdownExporter
from app.delivery.exporters.telegram_exporter import TelegramExporter

if TYPE_CHECKING:
    from app.db.db_models.creation import GeneratedContent
    from app.db.db_models.strategy import ContentSchedule

logger = logging.getLogger(__name__)


class DeliveryService:
    """
    Main orchestrator for the Delivery phase.

    Usage:
        service = DeliveryService()
        result = await service.deliver_week(week_year=2026, week_number=3)
    """

    def __init__(
        self,
        enable_telegram: bool = True,
        enable_file_export: bool = True,
        update_status: bool = True,
    ):
        """
        Initialize delivery service.

        Args:
            enable_telegram: Whether to send Telegram notifications
            enable_file_export: Whether to export Markdown files
            update_status: Whether to update DB status to DELIVERED
        """
        self.enable_telegram = enable_telegram
        self.enable_file_export = enable_file_export
        self.update_status = update_status

        self.markdown_exporter = MarkdownExporter()
        self.telegram_exporter = TelegramExporter()

    async def deliver_week(
        self,
        week_year: int,
        week_number: int,
    ) -> DeliveryResult:
        """
        Deliver all approved content for a week.

        Args:
            week_year: Year (e.g., 2026)
            week_number: ISO week number (1-53)

        Returns:
            DeliveryResult with details of the delivery
        """
        start_time = time.time()

        result = DeliveryResult(
            week_year=week_year,
            week_number=week_number,
            output_directory="",
            telegram_enabled=self.enable_telegram
            and self.telegram_exporter.is_configured,
        )

        logger.info(f"[DELIVERY] Starting delivery for week {week_year}-W{week_number}")

        # Get database session
        session_gen = get_session()
        session = cast(Session, next(session_gen))

        try:
            # Step 1: Fetch ALL content for file export (includes flagged/rejected)
            all_content_items = db_services.get_all_content_for_week(
                session=session,
                week_year=week_year,
                week_number=week_number,
            )

            if not all_content_items:
                logger.warning(
                    f"[DELIVERY] No content found for week {week_year}-W{week_number}"
                )
                result.duration_seconds = time.time() - start_time
                return result

            # Step 2: Get week date range
            start_date, end_date = db_services.get_week_date_range(
                session=session,
                week_year=week_year,
                week_number=week_number,
            )

            # Step 3: Transform ALL content to delivery briefs (for file export)
            briefs: List[DeliveryBrief] = []
            approved_briefs: List[DeliveryBrief] = []  # For Telegram (approved only)
            schedule_ids: List[uuid.UUID] = []

            for generated_content, schedule in all_content_items:
                try:
                    brief = self._transform_to_brief(generated_content, schedule)
                    briefs.append(brief)
                    
                    # Track approved content for Telegram and status updates
                    if generated_content.status.value == "APPROVED":
                        approved_briefs.append(brief)
                        schedule_ids.append(schedule.id)
                    
                    result.successful += 1
                except Exception as e:
                    logger.exception(
                        f"[DELIVERY] Transform failed for schedule {schedule.id}"
                    )
                    result.failed += 1

            result.total_processed = len(all_content_items)

            # Step 4: Build week package
            package = self._build_week_package(
                week_year=week_year,
                week_number=week_number,
                start_date=start_date,
                end_date=end_date,
                briefs=briefs,
            )

            # Step 5: Export to files
            if self.enable_file_export:
                created_files = self.markdown_exporter.export_week(package)
                result.files_created = created_files
                result.output_directory = str(
                    self.markdown_exporter.base_dir
                    / f"week_{week_number:02d}_{week_year}"
                )

            # Step 6: Send via Telegram (APPROVED content only)
            if self.enable_telegram and self.telegram_exporter.is_configured:
                # Build package with only approved briefs for Telegram
                approved_package = self._build_week_package(
                    week_year=week_year,
                    week_number=week_number,
                    start_date=start_date,
                    end_date=end_date,
                    briefs=approved_briefs,
                )
                messages_sent, telegram_errors = await self.telegram_exporter.send_week(
                    approved_package
                )
                result.telegram_messages_sent = messages_sent
                result.telegram_errors = telegram_errors

            # Step 7: Update status to DELIVERED
            if self.update_status and schedule_ids:
                db_services.batch_update_to_delivered(session, schedule_ids)

            # Commit all changes
            try:
                next(session_gen, None)
            except StopIteration:
                pass

        except Exception as e:
            logger.exception("[DELIVERY] Delivery failed")
            raise

        finally:
            try:
                next(session_gen, None)
            except Exception:
                pass

        result.duration_seconds = time.time() - start_time

        logger.info(
            f"[DELIVERY] Complete: {result.successful}/{result.total_processed} delivered, "
            f"{len(result.files_created)} files, {result.telegram_messages_sent} Telegram messages, "
            f"{result.duration_seconds:.2f}s"
        )

        return result

    def _transform_to_brief(
        self,
        content: "GeneratedContent",
        schedule: "ContentSchedule",
    ) -> DeliveryBrief:
        """Transform a GeneratedContent + ContentSchedule into a DeliveryBrief."""
        from app.delivery.schemas import EmotionalArcSummary
        
        # Get format type
        format_type = (
            content.format_type.value
            if hasattr(content.format_type, "value")
            else str(content.format_type)
        )

        # Get the appropriate transformer
        transformer = get_transformer(format_type)

        # Build quality scores
        quality_scores = transformer.build_quality_summary(
            content.critique_scores or {}
        )

        # Build emotional arc (new) or journey (deprecated fallback)
        emotional_arc = None
        emotional_journey = None
        arc_section = ""
        
        if content.emotional_arc and format_type in ("REEL", "CAROUSEL"):
            # Use new EmotionalArc for Reels/Carousels
            arc_data = content.emotional_arc
            emotional_arc = EmotionalArcSummary(
                entry_state=arc_data.get("entry_state", "Unknown"),
                destabilization_trigger=arc_data.get("destabilization_trigger", "Unknown"),
                resistance_point=arc_data.get("resistance_point", "Unknown"),
                breakthrough_moment=arc_data.get("breakthrough_moment", "Unknown"),
                landing_state=arc_data.get("landing_state", "Unknown"),
                pacing_note=arc_data.get("pacing_note", ""),
            )
            arc_section = transformer.render_emotional_arc(emotional_arc)
        else:
            # Fallback to deprecated emotional_journey for Quotes or missing data
            emotional_journey = transformer.build_emotional_journey(
                content.emotional_journey or {}
            )
            arc_section = transformer.render_emotional_journey(emotional_journey)

        # Transform content to Markdown
        content_markdown = transformer.transform_content(content.content_json or {})

        # Add header
        pillar = (
            schedule.required_pillar.value
            if hasattr(schedule.required_pillar, "value")
            else str(schedule.required_pillar)
        )

        time_str = (
            schedule.scheduled_time.strftime("%I:%M %p")
            if schedule.scheduled_time
            else "TBD"
        )
        date_str = schedule.scheduled_date.strftime("%b %d, %Y")

        # Extract status and flag_reasons
        status = (
            content.status.value
            if hasattr(content.status, "value")
            else str(content.status)
        )
        flag_reasons = content.flag_reasons or []

        header = transformer.render_header(
            format_type=format_type,
            slot_number=schedule.slot_number,
            day_of_week=schedule.day_of_week,
            scheduled_date=date_str,
            scheduled_time=time_str,
            pillar=pillar,
            resolved_mode=content.resolved_mode,
            quality_avg=quality_scores.average,
            status=status,
            flag_reasons=flag_reasons,
        )

        # Add quality scores section
        quality_section = transformer.render_quality_scores(quality_scores)

        # Add metadata footer
        brief_data = schedule.brief or {}
        footer = transformer.render_metadata_footer(
            generated_content_id=str(content.id),
            schedule_id=str(schedule.id),
            atom_id=brief_data.get("atom_id", "N/A"),
            angle_name=brief_data.get("angle_name", "N/A"),
            trace_id=str(content.trace_id),
            generated_at=content.generated_at.strftime("%Y-%m-%d %H:%M UTC"),
            attempts=content.generation_attempts,
        )

        # Combine all sections
        full_markdown = header + content_markdown + arc_section + quality_section + footer

        return DeliveryBrief(
            generated_content_id=str(content.id),
            schedule_id=str(schedule.id),
            trace_id=str(content.trace_id),
            slot_number=schedule.slot_number,
            scheduled_date=schedule.scheduled_date,
            scheduled_time=schedule.scheduled_time,
            day_of_week=schedule.day_of_week,
            format_type=format_type,
            pillar=pillar,
            resolved_mode=content.resolved_mode,
            quality_scores=quality_scores,
            emotional_arc=emotional_arc,
            emotional_journey=emotional_journey,
            generation_attempts=content.generation_attempts,
            content_markdown=full_markdown,
            atom_id=brief_data.get("atom_id"),
            angle_id=brief_data.get("angle_id"),
            angle_name=brief_data.get("angle_name"),
            generated_at=content.generated_at,
            status=status,
            flag_reasons=flag_reasons,
        )

    def _build_week_package(
        self,
        week_year: int,
        week_number: int,
        start_date,
        end_date,
        briefs: List[DeliveryBrief],
    ) -> WeekPackage:
        """Build a WeekPackage from briefs."""
        package = WeekPackage(
            week_year=week_year,
            week_number=week_number,
            start_date=start_date,
            end_date=end_date,
            briefs=briefs,
            total_items=len(briefs),
        )

        # Count by format
        package.reels_count = sum(1 for b in briefs if b.format_type == "REEL")
        package.carousels_count = sum(1 for b in briefs if b.format_type == "CAROUSEL")
        package.quotes_count = sum(1 for b in briefs if b.format_type == "QUOTE")

        # Calculate average quality
        if briefs:
            total_quality = sum(b.quality_scores.average for b in briefs)
            package.avg_quality_score = total_quality / len(briefs)

        # Count items needing attention
        package.items_needing_attention = sum(
            1 for b in briefs if not b.quality_scores.passed_all
        )

        return package


# CLI entry point
async def main():
    """CLI entry point for delivery service."""
    import argparse

    parser = argparse.ArgumentParser(description="Prismatic Engine Delivery Agent")
    parser.add_argument(
        "--week-year", type=int, required=True, help="Year (e.g., 2026)"
    )
    parser.add_argument(
        "--week-number", type=int, required=True, help="Week number (1-53)"
    )
    parser.add_argument(
        "--no-telegram", action="store_true", help="Disable Telegram delivery"
    )
    parser.add_argument(
        "--no-files", action="store_true", help="Disable file export"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Don't update DB status"
    )

    args = parser.parse_args()

    service = DeliveryService(
        enable_telegram=not args.no_telegram,
        enable_file_export=not args.no_files,
        update_status=not args.dry_run,
    )

    result = await service.deliver_week(
        week_year=args.week_year,
        week_number=args.week_number,
    )

    print("\n✅ Delivery complete!")
    print(f"   Processed: {result.total_processed}")
    print(f"   Successful: {result.successful}")
    print(f"   Files created: {len(result.files_created)}")
    print(f"   Telegram messages: {result.telegram_messages_sent}")
    print(f"   Duration: {result.duration_seconds:.2f}s")
    print(f"   Output: {result.output_directory}")


if __name__ == "__main__":
    asyncio.run(main())
