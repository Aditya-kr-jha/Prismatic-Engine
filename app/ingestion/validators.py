"""
Ingestion Validators.

Pure validation functions for Phase 1 ingestion.

Rules:
- Pure functions with no side effects
- Return structured rejection reasons
- Do NOT talk to database
- Do NOT log

Designed for future learning/analytics use.
"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass(frozen=True)
class ValidationResult:
    """Result of a validation check."""

    is_valid: bool
    reason_code: Optional[str] = None
    reason_message: Optional[str] = None
    metadata: Optional[dict] = None


@dataclass(frozen=True)
class RejectionReason:
    """Structured rejection reason for analytics."""

    code: str
    message: str
    phase: str = "ingestion"
    validator: str = ""
    details: Optional[dict] = None


def validate_content_length(
    content: str,
    min_length: int = 300,
    max_length: int = 50000,
) -> ValidationResult:
    """
    Validate content length is within acceptable bounds.

    Args:
        content: Raw content string
        min_length: Minimum required length
        max_length: Maximum allowed length

    Returns:
        ValidationResult with validity and reason if invalid
    """
    if not content:
        return ValidationResult(
            is_valid=False,
            reason_code="content_empty",
            reason_message="Content is empty or None",
            metadata={"length": 0, "min_required": min_length},
        )

    length = len(content)

    if length < min_length:
        return ValidationResult(
            is_valid=False,
            reason_code="content_too_short",
            reason_message=f"Content length {length} is below minimum {min_length}",
            metadata={"length": length, "min_required": min_length},
        )

    if length > max_length:
        return ValidationResult(
            is_valid=False,
            reason_code="content_too_long",
            reason_message=f"Content length {length} exceeds maximum {max_length}",
            metadata={"length": length, "max_allowed": max_length},
        )

    return ValidationResult(is_valid=True)


def validate_score(
    score: int,
    min_score: int = 10,
) -> ValidationResult:
    """
    Validate content score meets minimum threshold.

    Args:
        score: Engagement score (e.g., Reddit upvotes)
        min_score: Minimum required score

    Returns:
        ValidationResult with validity and reason if invalid
    """
    if score < min_score:
        return ValidationResult(
            is_valid=False,
            reason_code="score_too_low",
            reason_message=f"Score {score} is below minimum {min_score}",
            metadata={"score": score, "min_required": min_score},
        )

    return ValidationResult(is_valid=True)


def validate_not_deleted(
    content: str,
) -> ValidationResult:
    """
    Validate content is not a deleted/removed placeholder.

    Args:
        content: Raw content string

    Returns:
        ValidationResult with validity and reason if invalid
    """
    deleted_markers = {"[removed]", "[deleted]", ""}

    if content in deleted_markers:
        return ValidationResult(
            is_valid=False,
            reason_code="content_deleted",
            reason_message="Content has been deleted or removed",
            metadata={"content": content},
        )

    return ValidationResult(is_valid=True)


def validate_is_text_post(
    is_self: bool,
) -> ValidationResult:
    """
    Validate this is a text post (not a link post).

    Args:
        is_self: Whether this is a self/text post

    Returns:
        ValidationResult with validity and reason if invalid
    """
    if not is_self:
        return ValidationResult(
            is_valid=False,
            reason_code="not_text_post",
            reason_message="Post is a link post, not a text post",
            metadata={"is_self": is_self},
        )

    return ValidationResult(is_valid=True)


def validate_reddit_post(
    data: dict,
    min_score: int = 10,
    min_content_length: int = 300,
) -> tuple[bool, List[RejectionReason]]:
    """
    Run all Reddit post validations and collect rejection reasons.

    Args:
        data: Raw Reddit post data dict
        min_score: Minimum required score
        min_content_length: Minimum content length

    Returns:
        Tuple of (is_valid, list of rejection reasons)
    """
    reasons: List[RejectionReason] = []

    # Check if it's a self post
    is_self = bool(data.get("is_self", False))
    result = validate_is_text_post(is_self)
    if not result.is_valid:
        reasons.append(
            RejectionReason(
                code=result.reason_code or "unknown",
                message=result.reason_message or "Validation failed",
                validator="validate_is_text_post",
                details=result.metadata,
            )
        )

    # Check content is not deleted
    selftext = data.get("selftext", "")
    result = validate_not_deleted(selftext)
    if not result.is_valid:
        reasons.append(
            RejectionReason(
                code=result.reason_code or "unknown",
                message=result.reason_message or "Validation failed",
                validator="validate_not_deleted",
                details=result.metadata,
            )
        )

    # Check score
    score = int(data.get("score", 0))
    result = validate_score(score, min_score)
    if not result.is_valid:
        reasons.append(
            RejectionReason(
                code=result.reason_code or "unknown",
                message=result.reason_message or "Validation failed",
                validator="validate_score",
                details=result.metadata,
            )
        )

    # Check content length (only if we have selftext)
    if selftext and selftext not in ("[removed]", "[deleted]"):
        result = validate_content_length(selftext, min_content_length)
        if not result.is_valid:
            reasons.append(
                RejectionReason(
                    code=result.reason_code or "unknown",
                    message=result.reason_message or "Validation failed",
                    validator="validate_content_length",
                    details=result.metadata,
                )
            )

    return len(reasons) == 0, reasons
