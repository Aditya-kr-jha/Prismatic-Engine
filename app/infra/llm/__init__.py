"""
LLM Prompts for Content Validation.

This module contains prompt definitions for LLM-based chunk validation.
Only prompt constants are defined here - no execution logic.
"""

from infra.llm.pre_injection_prompts import (
    CONTENT_VALIDATOR_SYSTEM_PROMPT,
    CONTENT_VALIDATOR_USER_PROMPT,
)

__all__ = [
    "CONTENT_VALIDATOR_SYSTEM_PROMPT",
    "CONTENT_VALIDATOR_USER_PROMPT",
]
