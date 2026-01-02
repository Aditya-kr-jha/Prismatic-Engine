"""
Phase 3 Classification Module.

This module handles content classification using LLM-based atomic extraction
and multi-dimensional classification.
"""

from app.classification.schemas import (
    AtomicComponents,
    ClassificationOutput,
    ClassificationDimensions,
)
from app.classification.classifier import ContentClassifier
from app.classification.services import ClassificationService, ClassificationResult

__all__ = [
    "AtomicComponents",
    "ClassificationOutput",
    "ClassificationDimensions",
    "ContentClassifier",
    "ClassificationService",
    "ClassificationResult",
]
