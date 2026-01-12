"""
Phase 5 Creation Service (Orchestrator).

The ONLY entry point for Phase 5 creation logic.

This service:
- Fetches scheduled ContentSchedule records
- Runs Stage 1 analysis with async concurrency
- Runs Stage 2 targeting to produce GenerationContext
- Runs Stage 3 content generation (format-specific)
- Handles exit conditions (UNSUITABLE, NEEDS_WORK, READY)
- Updates ContentSchedule status and stores results

Execution model:
- Batch frequency: Once per week (after Phase 4 scheduling)
- Rows per run: 21 (one week's content)
- Concurrency: 3 parallel (matching classification pattern)
- Expected runtime: 5-10 min for all three stages
"""

import asyncio
import logging
import random
import re
import time
from typing import cast, List, Optional

from pydantic import BaseModel, Field, computed_field
from sqlmodel import Session

from app.creation import db_services
from app.creation.schemas import (
    GenerationContext,
    Stage1Analysis,
    Stage3Result,
    Stage4Result,
    Stage5Result,
)
from app.creation.stages.stage_1_analyze import Stage1Analyzer
from app.creation.stages.stage_2_target import Stage2Targeter
from app.creation.stages.stage_3_generate import Stage3Generator
from app.creation.stages.stage_4_critique import Stage4Critic
from app.creation.stages.stage_5_storage import Stage5Storage
from app.db.db_models.strategy import ContentSchedule
from app.db.db_session import get_session
from app.db.enums import ScheduleStatus

logger = logging.getLogger(__name__)


# ============================================================================
# RESULT MODELS
# ============================================================================


class SingleItemResult(BaseModel):
    """Result from processing a single ContentSchedule item through all stages."""

    schedule_id: str
    trace_id: str
    stage1_analysis: Optional[Stage1Analysis] = None
    stage2_context: Optional[GenerationContext] = None
    stage3_result: Optional[Stage3Result] = None
    stage4_result: Optional[Stage4Result] = None
    stage5_result: Optional[Stage5Result] = None
    is_unsuitable: bool = False
    unsuitable_reason: Optional[str] = None
    error: Optional[str] = None
    error_stage: Optional[str] = None  # "stage1", "stage2", "stage3", "stage4", "stage5"

    model_config = {"arbitrary_types_allowed": True}


class PipelineResult(BaseModel):
    """Result from running the full creation pipeline."""

    week_year: int
    week_number: int
    items: List[SingleItemResult] = Field(default_factory=list)
    duration_seconds: float = 0.0

    model_config = {"arbitrary_types_allowed": True}

    @computed_field
    @property
    def total_processed(self) -> int:
        return len(self.items)

    @computed_field
    @property
    def successful(self) -> int:
        return len([i for i in self.items if i.stage3_result and not i.error])

    @computed_field
    @property
    def unsuitable(self) -> int:
        return len([i for i in self.items if i.is_unsuitable])

    @computed_field
    @property
    def errors(self) -> int:
        return len([i for i in self.items if i.error])

    @property
    def stage1_results(self) -> List[Stage1Analysis]:
        return [i.stage1_analysis for i in self.items if i.stage1_analysis]

    @property
    def stage2_contexts(self) -> List[GenerationContext]:
        return [i.stage2_context for i in self.items if i.stage2_context]

    @property
    def stage3_results(self) -> List[Stage3Result]:
        return [i.stage3_result for i in self.items if i.stage3_result]


# ============================================================================
# CREATION SERVICE
# ============================================================================


class CreationService:
    """
    Orchestrates Phase 5 content creation workflow.

    This is the ONLY entry point for creation logic. It coordinates:
    - Stage1Analyzer (LLM analysis)
    - Stage2Targeter (Mode resolution + emotional targeting)
    - Stage3Generator (Format-specific content generation)
    - DB Services (data access)

    Usage:
        service = CreationService()

        # Full pipeline (recommended):
        result = await service.run_pipeline(2026, 2)

        # Access individual results:
        for item in result.items:
            print(item.stage1_analysis)
            print(item.stage2_context)
            print(item.stage3_result)

        # Or process a single item:
        item_result = await service.process_single_item(content_schedule_row)
    """

    MAX_CONCURRENCY = 3
    MAX_RETRIES = 5
    BASE_DELAY_SECONDS = 2.0
    MAX_DELAY_SECONDS = 60.0

    def __init__(
        self,
        analyzer: Optional[Stage1Analyzer] = None,
        targeter: Optional[Stage2Targeter] = None,
        generator: Optional[Stage3Generator] = None,
        critic: Optional[Stage4Critic] = None,
        storage: Optional[Stage5Storage] = None,
    ):
        """Initialize the creation service with optional custom stage handlers."""
        self.analyzer = analyzer or Stage1Analyzer()
        self.targeter = targeter or Stage2Targeter()
        self.generator = generator or Stage3Generator()
        self.critic = critic or Stage4Critic()
        self.storage = storage or Stage5Storage()

    # ========================================================================
    # MAIN ENTRY POINT
    # ========================================================================

    async def run_pipeline(
        self,
        week_year: int,
        week_number: int,
        limit: int = 21,
        dry_run: bool = False,
    ) -> PipelineResult:
        """
        Run the complete creation pipeline (Stages 1-3) for a week's content.

        This is the MAIN ENTRY POINT for Phase 5 processing.
        """
        start = time.time()
        result = PipelineResult(week_year=week_year, week_number=week_number)

        logger.info(
            "[CREATION:PIPELINE] start week=%d-%d limit=%d dry_run=%s",
            week_year,
            week_number,
            limit,
            dry_run,
        )

        session_gen = get_session()
        session = cast(Session, next(session_gen))

        try:
            pending_rows = db_services.get_pending_scheduled_content(
                session,
                week_year=week_year,
                week_number=week_number,
                limit=limit,
            )

            if not pending_rows:
                logger.info(
                    "[CREATION:PIPELINE] no_pending_rows week=%d-%d",
                    week_year,
                    week_number,
                )
                result.duration_seconds = time.time() - start
                return result

            logger.info("[CREATION:PIPELINE] fetched_rows count=%d", len(pending_rows))

            semaphore = asyncio.Semaphore(self.MAX_CONCURRENCY)
            tasks = [
                self._process_item_with_semaphore(session, row, semaphore, dry_run)
                for row in pending_rows
            ]
            item_results = await asyncio.gather(*tasks)
            result.items = list(item_results)

            if not dry_run:
                next(session_gen, None)

            result.duration_seconds = time.time() - start
            logger.info(
                "[CREATION:PIPELINE] done week=%d-%d duration=%.2fs success=%d unsuitable=%d errors=%d",
                week_year,
                week_number,
                result.duration_seconds,
                result.successful,
                result.unsuitable,
                result.errors,
            )

        except Exception:
            logger.exception(
                "[CREATION:PIPELINE] failed week=%d-%d", week_year, week_number
            )
            raise
        finally:
            try:
                next(session_gen, None)
            except Exception:
                pass

        return result

    async def _process_item_with_semaphore(
        self,
        session: Session,
        row: ContentSchedule,
        semaphore: asyncio.Semaphore,
        dry_run: bool,
    ) -> SingleItemResult:
        """Wrapper to process item with semaphore control."""
        async with semaphore:
            return await self.process_single_item(session, row, dry_run)

    # ========================================================================
    # SINGLE ITEM PROCESSING
    # ========================================================================

    async def process_single_item(
        self,
        session: Session,
        row: ContentSchedule,
        dry_run: bool = False,
    ) -> SingleItemResult:
        """Process a single ContentSchedule item through all three stages."""
        item_result = SingleItemResult(
            schedule_id=str(row.id),
            trace_id=str(row.trace_id),
        )

        stage1_analysis = await self.run_stage1(row)
        if stage1_analysis is None:
            item_result.error = "Stage 1 analysis failed"
            item_result.error_stage = "stage1"
            return item_result

        item_result.stage1_analysis = stage1_analysis

        if stage1_analysis.instagram_readiness == "UNSUITABLE":
            item_result.is_unsuitable = True
            item_result.unsuitable_reason = (
                stage1_analysis.unsuitable_reason or "Material unsuitable"
            )
            if not dry_run:
                db_services.flag_for_human_review(
                    session, schedule_id=row.id, reason=item_result.unsuitable_reason
                )
            logger.info("[CREATION:S1] unsuitable trace_id=%s", row.trace_id)
            return item_result

        if not dry_run:
            db_services.store_stage1_analysis(
                session, row.id, stage1_analysis.model_dump()
            )

        stage2_context = await self.run_stage2(row, stage1_analysis)
        if stage2_context is None:
            item_result.error = "Stage 2 targeting failed"
            item_result.error_stage = "stage2"
            return item_result

        item_result.stage2_context = stage2_context

        stage3_result = await self.run_stage3(stage2_context)
        if stage3_result is None or stage3_result.error:
            item_result.error = (
                stage3_result.error if stage3_result else "Stage 3 generation failed"
            )
            item_result.error_stage = "stage3"
            return item_result

        item_result.stage3_result = stage3_result

        # Run Stage 4 critique loop
        stage4_result = await self.run_stage4(stage3_result, stage2_context)
        if stage4_result is None or stage4_result.error:
            item_result.error = (
                stage4_result.error if stage4_result else "Stage 4 critique failed"
            )
            item_result.error_stage = "stage4"
            return item_result

        item_result.stage4_result = stage4_result

        # Handle Stage 4 outcomes
        if stage4_result.flagged_for_review:
            # Max attempts reached, flag for human review (no Stage 5 needed)
            if not dry_run:
                db_services.flag_for_human_review(
                    session,
                    schedule_id=row.id,
                    reason=f"Stage 4 failed after {stage4_result.attempts_used} attempts. Focus: {stage4_result.final_critique.rewrite_focus if stage4_result.final_critique else 'N/A'}",
                )
            logger.warning(
                "[CREATION:S4] flagged_for_review trace_id=%s attempts=%d",
                row.trace_id,
                stage4_result.attempts_used,
            )
            return item_result

        # Stage 4 passed - proceed to Stage 5: Hard Filters & Storage
        if not stage4_result.passed or not stage4_result.final_content:
            item_result.error = "Stage 4 completed but content not passed"
            item_result.error_stage = "stage4"
            return item_result

        # Run Stage 5
        stage5_result = self.run_stage5(
            session=session,
            content=stage4_result.final_content,
            context=stage2_context,
            critique=stage4_result.final_critique,
            generation_attempts=stage4_result.attempts_used,
            dry_run=dry_run,
        )

        if stage5_result.error:
            item_result.error = stage5_result.error
            item_result.error_stage = "stage5"
            return item_result

        item_result.stage5_result = stage5_result

        logger.info(
            "[CREATION:COMPLETE] trace_id=%s format=%s attempts=%d stored=%s status=%s",
            row.trace_id,
            stage2_context.required_format,
            stage4_result.attempts_used,
            stage5_result.stored,
            stage5_result.final_status,
        )

        return item_result

    # ========================================================================
    # STAGE 1: ANALYZE
    # ========================================================================

    async def run_stage1(self, row: ContentSchedule) -> Optional[Stage1Analysis]:
        """Run Stage 1 analysis on a ContentSchedule item."""
        last_error: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES):
            try:
                analysis = await self.analyzer.analyze(
                    brief=row.brief or {},
                    required_pillar=(
                        row.required_pillar.value if row.required_pillar else "UNKNOWN"
                    ),
                    required_format=(
                        row.required_format.value if row.required_format else "UNKNOWN"
                    ),
                )
                logger.debug(
                    "[CREATION:S1] success trace_id=%s readiness=%s",
                    row.trace_id,
                    analysis.instagram_readiness,
                )
                return analysis
            except Exception as e:
                last_error = e
                if self._is_rate_limit_error(e):
                    wait_time = self._calculate_retry_wait(str(e), attempt)
                    logger.info(
                        "[CREATION:S1] rate_limited trace_id=%s attempt=%d/%d",
                        row.trace_id,
                        attempt + 1,
                        self.MAX_RETRIES,
                    )
                    await asyncio.sleep(wait_time)
                    continue
                break

        logger.warning(
            "[CREATION:S1] failed trace_id=%s error=%s",
            row.trace_id,
            str(last_error)[:100] if last_error else "Unknown",
        )
        return None

    # ========================================================================
    # STAGE 2: TARGET
    # ========================================================================

    async def run_stage2(
        self, row: ContentSchedule, stage1_analysis: Stage1Analysis
    ) -> Optional[GenerationContext]:
        """Run Stage 2 targeting to produce a GenerationContext."""
        last_error: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES):
            try:
                context = await self.targeter.target(
                    schedule_id=str(row.id),
                    trace_id=str(row.trace_id),
                    required_format=(
                        row.required_format.value if row.required_format else "UNKNOWN"
                    ),
                    required_pillar=(
                        row.required_pillar.value if row.required_pillar else "UNKNOWN"
                    ),
                    brief=row.brief or {},
                    stage1_analysis=stage1_analysis,
                )
                logger.debug(
                    "[CREATION:S2] success trace_id=%s mode=%s",
                    row.trace_id,
                    context.resolved_mode,
                )
                return context
            except Exception as e:
                last_error = e
                if self._is_rate_limit_error(e):
                    wait_time = self._calculate_retry_wait(str(e), attempt)
                    logger.info(
                        "[CREATION:S2] rate_limited trace_id=%s attempt=%d/%d",
                        row.trace_id,
                        attempt + 1,
                        self.MAX_RETRIES,
                    )
                    await asyncio.sleep(wait_time)
                    continue
                break

        logger.warning(
            "[CREATION:S2] failed trace_id=%s error=%s",
            row.trace_id,
            str(last_error)[:100] if last_error else "Unknown",
        )
        return None

    # ========================================================================
    # STAGE 3: GENERATE
    # ========================================================================

    async def run_stage3(self, context: GenerationContext) -> Optional[Stage3Result]:
        """Run Stage 3 content generation."""
        last_error: Optional[Exception] = None
        stage3_result: Optional[Stage3Result] = None

        for attempt in range(self.MAX_RETRIES):
            try:
                stage3_result = await self.generator.generate(
                    context=context, attempt=attempt + 1
                )
                if stage3_result and not stage3_result.error:
                    logger.debug(
                        "[CREATION:S3] success trace_id=%s format=%s",
                        context.trace_id,
                        context.required_format,
                    )
                    return stage3_result
            except Exception as e:
                last_error = e
                if self._is_rate_limit_error(e):
                    wait_time = self._calculate_retry_wait(str(e), attempt)
                    logger.info(
                        "[CREATION:S3] rate_limited trace_id=%s attempt=%d/%d",
                        context.trace_id,
                        attempt + 1,
                        self.MAX_RETRIES,
                    )
                    await asyncio.sleep(wait_time)
                    continue
                break

        logger.warning("[CREATION:S3] failed trace_id=%s", context.trace_id)
        return stage3_result

    # ========================================================================
    # STAGE 4: CRITIQUE
    # ========================================================================

    async def run_stage4(
        self, stage3_result: Stage3Result, context: GenerationContext
    ) -> Optional[Stage4Result]:
        """
        Run Stage 4 critique loop with rewrites.

        Note: Unlike Stages 1-3, Stage 4 has its own internal retry logic
        in run_critique_loop (max 3 attempts with rewrites). We only handle
        rate limiting at this level, not retries.
        """
        try:
            stage4_result = await self.critic.run_critique_loop(
                generator=self.generator,
                initial_stage3_result=stage3_result,
                context=context,
                max_attempts=3,
            )
            logger.debug(
                "[CREATION:S4] complete trace_id=%s passed=%s attempts=%d",
                context.trace_id,
                stage4_result.passed,
                stage4_result.attempts_used,
            )
            return stage4_result
        except Exception as e:
            if self._is_rate_limit_error(e):
                # For rate limits, wait and retry once
                wait_time = self._calculate_retry_wait(str(e), 0)
                logger.info(
                    "[CREATION:S4] rate_limited trace_id=%s wait=%.2fs",
                    context.trace_id,
                    wait_time,
                )
                await asyncio.sleep(wait_time)
                try:
                    return await self.critic.run_critique_loop(
                        generator=self.generator,
                        initial_stage3_result=stage3_result,
                        context=context,
                        max_attempts=3,
                    )
                except Exception as retry_error:
                    logger.warning(
                        "[CREATION:S4] failed after rate_limit_retry trace_id=%s error=%s",
                        context.trace_id,
                        str(retry_error)[:100],
                    )
                    return None

            logger.warning(
                "[CREATION:S4] failed trace_id=%s error=%s",
                context.trace_id,
                str(e)[:100],
            )
            return None

    # ========================================================================
    # STAGE 5: HARD FILTERS & STORAGE
    # ========================================================================

    def run_stage5(
        self,
        session: Session,
        content,  # Union[ReelContent, CarouselContent, QuoteContent]
        context: GenerationContext,
        critique,  # CritiqueResult
        generation_attempts: int,
        dry_run: bool = False,
    ) -> Stage5Result:
        """
        Run Stage 5: Hard filters and storage.

        This is synchronous (no LLM calls).
        """
        from app.creation.schemas import CritiqueResult as CritiqueResultType

        # Ensure critique is the correct type
        if critique is None:
            from app.creation.schemas import CritiqueResult, CritiqueScores

            critique = CritiqueResult(
                scores=CritiqueScores(
                    scroll_stop_power=7,
                    ai_voice_risk=7,
                    share_impulse=7,
                    emotional_precision=7,
                    mode_fidelity=7,
                    format_execution=7,
                ),
                lowest_score_criterion="N/A",
                overall_pass=True,
                rewrite_required=False,
            )

        return self.storage.run(
            session=session,
            content=content,
            context=context,
            critique=critique,
            generation_attempts=generation_attempts,
            dry_run=dry_run,
        )

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _is_rate_limit_error(self, error: Exception) -> bool:
        error_str = str(error).lower()
        return "429" in error_str or "rate_limit" in error_str

    def _calculate_retry_wait(self, error_message: str, attempt: int) -> float:
        extracted_time = self._extract_retry_time(error_message)
        if extracted_time:
            return extracted_time
        return min(
            self.BASE_DELAY_SECONDS * (2**attempt) + random.uniform(0, 1),
            self.MAX_DELAY_SECONDS,
        )

    def _extract_retry_time(self, error_message: str) -> Optional[float]:
        patterns = [r"try again in (\d+\.?\d*)s", r"try again in (\d+)ms"]
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                if i == 1:
                    value = value / 1000.0
                return value + 0.5
        return None
