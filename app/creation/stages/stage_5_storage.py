"""
Stage 5: Storage Handler.

Runs hard filters and stores approved content in GeneratedContent table.
Updates ContentSchedule status to DRAFT (content ready) or SKIPPED (needs review).
"""

import logging
from typing import Optional, Union
from uuid import UUID

from sqlmodel import Session

from app.creation import db_services
from app.creation.schemas import (
    CarouselContent,
    CritiqueResult,
    GenerationContext,
    HardFilterResult,
    QuoteContent,
    ReelContent,
    Stage5Result,
)
from app.creation.stages.stage_5_filters import run_hard_filters
from app.db.enums import ScheduleStatus

logger = logging.getLogger(__name__)

# Type alias for content
GeneratedContent = Union[ReelContent, CarouselContent, QuoteContent]


class Stage5Storage:
    """
    Handles Stage 5: Hard Filters & Storage.

    Responsibilities:
    1. Run automated hard filters on approved content
    2. Store content in GeneratedContent table
    3. Update ContentSchedule status
    """

    def run(
        self,
        session: Session,
        content: GeneratedContent,
        context: GenerationContext,
        critique: CritiqueResult,
        generation_attempts: int,
        dry_run: bool = False,
    ) -> Stage5Result:
        """
        Run Stage 5: Hard filters and storage.

        Args:
            session: Database session
            content: Final approved content from Stage 4
            context: GenerationContext with all metadata
            critique: Final CritiqueResult from Stage 4
            generation_attempts: Number of generation attempts used
            dry_run: If True, don't store to database

        Returns:
            Stage5Result with filter results and storage status
        """
        result = Stage5Result(
            schedule_id=context.schedule_id,
            trace_id=context.trace_id,
            filter_result=HardFilterResult(passed=True),  # Will be updated
        )

        format_type = context.required_format.upper()

        # Run hard filters
        filter_result = run_hard_filters(content, format_type)
        result.filter_result = filter_result

        logger.debug(
            "[CREATION:S5] filters complete trace_id=%s passed=%s failures=%d",
            context.trace_id,
            filter_result.passed,
            len(filter_result.failures),
        )

        # Determine final status and flagging
        is_flagged = not filter_result.passed
        final_status = "CONTENT_READY" if filter_result.passed else "NEEDS_REVIEW"
        result.final_status = final_status

        if dry_run:
            result.stored = False
            logger.info(
                "[CREATION:S5] dry_run=True trace_id=%s status=%s",
                context.trace_id,
                final_status,
            )
            return result

        try:
            # Store in GeneratedContent table
            schedule_uuid = UUID(context.schedule_id)
            trace_uuid = UUID(context.trace_id)

            generated_content_id = db_services.store_generated_content(
                session=session,
                schedule_id=schedule_uuid,
                trace_id=trace_uuid,
                format_type=format_type,
                content_json=content.model_dump(),
                generation_context=context.model_dump(),
                resolved_mode=context.resolved_mode,
                # Keep emotional_journey for backward compatibility
                emotional_journey=(
                    context.emotional_journey.model_dump()
                    if context.emotional_journey
                    else {}
                ),
                # New fields
                emotional_arc=context.emotional_arc.model_dump(),
                mode_sequence=context.mode_sequence.model_dump(),
                critique_scores=critique.scores.model_dump(),
                generation_attempts=generation_attempts,
                flag_reasons=filter_result.failures,
                is_flagged=is_flagged,
            )

            result.stored = True
            result.generated_content_id = str(generated_content_id)

            # Update ContentSchedule status
            new_schedule_status = (
                ScheduleStatus.DRAFT if filter_result.passed else ScheduleStatus.SKIPPED
            )
            db_services.update_schedule_status(
                session, schedule_uuid, new_schedule_status
            )

            logger.info(
                "[CREATION:S5] stored trace_id=%s content_id=%s schedule_status=%s",
                context.trace_id,
                generated_content_id,
                new_schedule_status.value,
            )

        except Exception as e:
            result.error = str(e)
            result.stored = False
            logger.error(
                "[CREATION:S5] storage_failed trace_id=%s error=%s",
                context.trace_id,
                str(e)[:100],
            )

        return result
