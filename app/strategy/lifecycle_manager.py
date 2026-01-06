"""
Lifecycle Manager for Content Atoms.
Handles state transitions based on usage patterns.
"""

from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session, select, and_

from app.db.db_models.classification import ContentAtom
from app.db.db_session import get_session
from app.db.enums import LifecycleState


class LifecycleConfig(BaseModel):
    """Configuration for lifecycle transitions."""

    # ACTIVE → COOLING: After being scheduled
    enable_cooling: bool = True  # Set to True if you want a cooling period
    cooling_duration_days: int = 30  # How long before COOLING → ACTIVE

    # ACTIVE → ARCHIVED: After N uses
    max_uses_before_archive: int = 5

    # ARCHIVED → RESURRECTED: After N weeks of rest
    min_rest_weeks_for_resurrection: int = 40

    # Auto-retire: Content older than N months with poor performance
    auto_retire_after_months: int = 12
    min_performance_for_survival: float = 0.3  # Bottom 30% gets retired


# ════════════════════════════════════════════════════════════════════════════
# STATE TRANSITIONS
# ════════════════════════════════════════════════════════════════════════════


def transition_to_cooling(session: Session, atom: ContentAtom) -> ContentAtom:
    """
    Transition atom to COOLING state after being scheduled.

    Use this if you want a mandatory "rest period" after each use.
    For MVP, you might skip this and just use anti-repetition queries.
    """
    atom.lifecycle_state = LifecycleState.COOLING
    session.add(atom)
    return atom


def transition_to_archived(
    session: Session, atom: ContentAtom, reason: str = "max_uses_reached"
) -> ContentAtom:
    """
    Transition atom to ARCHIVED state.

    Called when atom has been used too many times and needs extended rest.
    """
    atom.lifecycle_state = LifecycleState.ARCHIVED
    session.add(atom)
    return atom


def transition_to_retired(
    session: Session, atom: ContentAtom, reason: str = "manual"
) -> ContentAtom:
    """
    Transition atom to RETIRED state (permanent exclusion).

    Called for outdated content or manual retirement.
    """
    atom.lifecycle_state = LifecycleState.RETIRED
    session.add(atom)
    return atom


def transition_to_resurrected(
    session: Session, atom: ContentAtom, reason: str = "manual"
) -> ContentAtom:
    """
    Bring an archived/retired atom back to active use.

    Resets usage count and marks as resurrected.
    """
    atom.lifecycle_state = LifecycleState.RESURRECTED
    atom.times_used = 0  # Reset usage count
    atom.last_used_at = None  # Reset last used
    session.add(atom)
    return atom


def transition_to_active(session: Session, atom: ContentAtom) -> ContentAtom:
    """
    Transition atom back to ACTIVE state.

    Called after cooling period ends, or after resurrection.
    """
    atom.lifecycle_state = LifecycleState.ACTIVE
    session.add(atom)
    return atom


# ════════════════════════════════════════════════════════════════════════════
# BATCH LIFECYCLE UPDATES (Run periodically)
# ════════════════════════════════════════════════════════════════════════════


def process_cooling_atoms(
    session: Session, config: LifecycleConfig = LifecycleConfig()
) -> int:
    """
    Process atoms in COOLING state.
    Transition back to ACTIVE if cooling period has elapsed.

    Returns: Number of atoms transitioned
    """
    if not config.enable_cooling:
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=config.cooling_duration_days)

    # Find atoms that have been cooling long enough (based on last_used_at)
    statement = select(ContentAtom).where(
        and_(
            ContentAtom.lifecycle_state == LifecycleState.COOLING,
            ContentAtom.last_used_at < cutoff,
            ContentAtom.deleted_at.is_(None),
        )
    )

    atoms = session.exec(statement).all()
    transitioned = 0

    for atom in atoms:
        transition_to_active(session, atom)
        transitioned += 1

    session.commit()
    return transitioned


def process_overused_atoms(
    session: Session, config: LifecycleConfig = LifecycleConfig()
) -> int:
    """
    Find atoms that have been used too many times and archive them.

    Returns: Number of atoms archived
    """
    statement = select(ContentAtom).where(
        and_(
            ContentAtom.lifecycle_state == LifecycleState.ACTIVE,
            ContentAtom.times_used >= config.max_uses_before_archive,
            ContentAtom.deleted_at.is_(None),
        )
    )

    atoms = session.exec(statement).all()

    for atom in atoms:
        transition_to_archived(session, atom, reason="max_uses_reached")

    session.commit()
    return len(atoms)


def process_resurrection_candidates(
    session: Session, config: LifecycleConfig = LifecycleConfig()
) -> List[ContentAtom]:
    """
    Find archived atoms that are eligible for resurrection.

    Does NOT automatically resurrect — returns candidates for review.

    Returns: List of atoms eligible for resurrection
    """
    cutoff = datetime.now(timezone.utc) - timedelta(
        weeks=config.min_rest_weeks_for_resurrection
    )

    # Atoms archived long enough (based on updated_at as proxy for archive time)
    statement = select(ContentAtom).where(
        and_(
            ContentAtom.lifecycle_state == LifecycleState.ARCHIVED,
            ContentAtom.updated_at < cutoff,
            ContentAtom.deleted_at.is_(None),
        )
    )

    return list(session.exec(statement).all())


def get_atom_by_id(session: Session, atom_id: UUID) -> ContentAtom | None:
    """
    Fetch a ContentAtom by its ID.

    Returns: ContentAtom or None if not found
    """
    statement = select(ContentAtom).where(ContentAtom.id == atom_id)
    return session.exec(statement).first()


# ════════════════════════════════════════════════════════════════════════════
# INTEGRATION WITH SCHEDULE GENERATOR
# ════════════════════════════════════════════════════════════════════════════


def update_atom_after_scheduling(
    session: Session, atom: ContentAtom, config: LifecycleConfig = LifecycleConfig()
) -> ContentAtom:
    """
    Update atom state after it's been scheduled.

    Call this in fill_single_slot() after selecting an atom.
    Note: Caller is responsible for committing the session.
    """
    # Update usage tracking
    atom.times_used = (atom.times_used or 0) + 1
    atom.last_used_at = datetime.now(timezone.utc)

    # Check if should transition to COOLING
    if config.enable_cooling:
        transition_to_cooling(session, atom)

    # Check if should archive (too many uses)
    elif atom.times_used >= config.max_uses_before_archive:
        transition_to_archived(session, atom, reason="max_uses_reached")

    else:
        session.add(atom)

    return atom
