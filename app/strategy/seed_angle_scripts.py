#!/usr/bin/env python3
"""
Seed data for angle_matrix table.
Run once to populate the 20 core angles for Prismatic Engine.

Usage:
    # Seed all angles
    poetry run python scripts/strategy/seed_angles.py

    # Dry run (no DB writes)
    poetry run python scripts/strategy/seed_angles.py --dry-run

    # Verbose logging
    poetry run python scripts/strategy/seed_angles.py --verbose
"""

import argparse
import logging
import sys
from datetime import datetime, timezone

from app.db.db_models.classification import ContentAtom  # noqa: F401
from app.db.db_models.ingestion import RawIngest, RejectedContent  # noqa: F401
from app.db.db_models.strategy import AngleMatrix
from app.db.db_session import get_session

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# SEED DATA - 20 Core Angles for Prismatic Engine
# ═══════════════════════════════════════════════════════════════

SEED_ANGLES = [
    # ═══════════════════════════════════════════════════════════════
    # HIGH-ENGAGEMENT ANGLES (Virality Multiplier: 1.3-1.5)
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "contrarian",
        "name": "The Contrarian",
        "template": "Why {common_belief} is actually wrong",
        "description": "Challenges mainstream thinking.  Creates cognitive dissonance that demands resolution.",
        "best_for_pillars": [
            "PRODUCTIVITY",
            "NEUROSCIENCE",
            "DARK_PSYCHOLOGY",
            "PHILOSOPHY",
        ],
        "avoid_for_pillars": [
            "HEALING_GROWTH"
        ],  # Too aggressive for vulnerable audiences
        "best_for_formats": ["REEL", "CAROUSEL"],
        "avoid_for_formats": [],
        "constraints": {
            "complexity_range": [3, 5],
            "requires_proof": True,
            "tone": "Edgy",
        },
        "virality_multiplier": 1.5,
        "performance_data": {},
        "is_active": True,
        "example_content": "Why waking up at 5AM is actually destroying your productivity",
        "internal_notes": "Top performer.  Use sparingly (max 3x/week) to avoid audience fatigue.",
    },
    {
        "id": "dark_truth",
        "name": "The Dark Truth",
        "template": "The uncomfortable truth about {topic} no one talks about",
        "description": "Reveals hidden dynamics.  Triggers FEAR + CURIOSITY.  High save rate.",
        "best_for_pillars": ["DARK_PSYCHOLOGY", "RELATIONSHIPS", "SELF_WORTH"],
        "avoid_for_pillars": ["SELF_CARE"],
        "best_for_formats": ["REEL", "CAROUSEL"],
        "avoid_for_formats": ["QUOTE"],  # Needs space for nuance
        "constraints": {
            "complexity_range": [3, 5],
            "requires_proof": False,
            "tone": "Provocative",
        },
        "virality_multiplier": 1.45,
        "performance_data": {},
        "is_active": True,
        "example_content": "The uncomfortable truth about why people ghost you",
        "internal_notes": "Strong for DARK_PSYCHOLOGY pillar. Balance with hopeful content.",
    },
    {
        "id": "pattern_interrupt",
        "name": "Pattern Interrupt",
        "template": "Stop scrolling. This will change how you see {topic}.",
        "description": "Direct address that breaks passive scrolling.  High hook retention.",
        "best_for_pillars": [
            "PRODUCTIVITY",
            "NEUROSCIENCE",
            "SELF_WORTH",
            "HEALING_GROWTH",
        ],
        "avoid_for_pillars": [],
        "best_for_formats": ["REEL"],
        "avoid_for_formats": ["CAROUSEL"],  # Loses urgency in slide format
        "constraints": {
            "complexity_range": [2, 4],
            "requires_proof": False,
            "tone": "Direct",
        },
        "virality_multiplier": 1.4,
        "performance_data": {},
        "is_active": True,
        "example_content": "Stop scrolling. This 3-second test reveals your attachment style.",
        "internal_notes": "Best for Reels. First 3 seconds are critical.",
    },
    {
        "id": "myth_buster",
        "name": "Myth Buster",
        "template": "{Number} myths about {topic} that are ruining your life",
        "description": "Listicle format with contrarian energy. High save + share rate.",
        "best_for_pillars": [
            "NEUROSCIENCE",
            "PRODUCTIVITY",
            "RELATIONSHIPS",
            "SELF_CARE",
        ],
        "avoid_for_pillars": [],
        "best_for_formats": ["CAROUSEL", "REEL"],
        "avoid_for_formats": ["QUOTE"],
        "constraints": {
            "complexity_range": [2, 4],
            "requires_proof": True,
            "tone": "Educational",
        },
        "virality_multiplier": 1.35,
        "performance_data": {},
        "is_active": True,
        "example_content": "5 myths about dopamine that are ruining your motivation",
        "internal_notes": "Always back with sources. Great for NEUROSCIENCE pillar.",
    },
    {
        "id": "secret_weapon",
        "name": "The Secret Weapon",
        "template": "The {topic} technique top performers use (but never share)",
        "description": "Exclusivity trigger. Makes audience feel like insiders.",
        "best_for_pillars": ["PRODUCTIVITY", "DARK_PSYCHOLOGY", "SELF_WORTH"],
        "avoid_for_pillars": ["PHILOSOPHY"],  # Too tactical for philosophical content
        "best_for_formats": ["CAROUSEL", "REEL"],
        "avoid_for_formats": [],
        "constraints": {
            "complexity_range": [2, 4],
            "requires_proof": False,
            "tone": "Insider",
        },
        "virality_multiplier": 1.35,
        "performance_data": {},
        "is_active": True,
        "example_content": "The focus technique CEOs use but never share publicly",
        "internal_notes": "Works well with frameworks and mental models.",
    },
    # ═══════════════════════════════════════════════════════════════
    # TRUST-BUILDING ANGLES (Virality Multiplier: 1.15-1.3)
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "study_breakdown",
        "name": "Study Breakdown",
        "template": "A {year} study from {institution} found that {finding}",
        "description": "Authority-based framing. High trust, moderate virality.  Great for carousels.",
        "best_for_pillars": ["NEUROSCIENCE", "PRODUCTIVITY", "RELATIONSHIPS"],
        "avoid_for_pillars": [
            "DARK_PSYCHOLOGY"
        ],  # Studies feel too 'clean' for dark content
        "best_for_formats": ["CAROUSEL"],
        "avoid_for_formats": ["QUOTE"],  # Too much info for single frame
        "constraints": {
            "complexity_range": [3, 5],
            "requires_proof": True,
            "source_credibility_min": "HIGH",
            "tone": "Authoritative",
        },
        "virality_multiplier": 1.25,
        "performance_data": {},
        "is_active": True,
        "example_content": "A 2023 Stanford study found that multitasking reduces IQ by 15 points",
        "internal_notes": "Only use with HIGH credibility sources.  Fact-check mandatory.",
    },
    {
        "id": "simple_framework",
        "name": "Simple Framework",
        "template": "The {name} framework: {number} steps to {outcome}",
        "description": "Actionable structure. High save rate.  Great for educational content.",
        "best_for_pillars": [
            "PRODUCTIVITY",
            "HEALING_GROWTH",
            "SELF_CARE",
            "RELATIONSHIPS",
        ],
        "avoid_for_pillars": [],
        "best_for_formats": ["CAROUSEL"],
        "avoid_for_formats": ["QUOTE"],
        "constraints": {
            "complexity_range": [2, 4],
            "requires_proof": False,
            "tone": "Instructive",
        },
        "virality_multiplier": 1.2,
        "performance_data": {},
        "is_active": True,
        "example_content": "The STAR framework: 4 steps to handle any difficult conversation",
        "internal_notes": "Name the framework something memorable. Acronyms work well.",
    },
    {
        "id": "before_after",
        "name": "Before/After",
        "template": "Before I learned {insight}, I {old_behavior}. Now I {new_behavior}.",
        "description": "Transformation narrative. High relatability and aspiration trigger.",
        "best_for_pillars": [
            "HEALING_GROWTH",
            "SELF_WORTH",
            "PRODUCTIVITY",
            "RELATIONSHIPS",
        ],
        "avoid_for_pillars": ["NEUROSCIENCE"],  # Too personal for science content
        "best_for_formats": ["REEL", "CAROUSEL"],
        "avoid_for_formats": [],
        "constraints": {
            "complexity_range": [1, 3],
            "requires_proof": False,
            "tone": "Relatable",
        },
        "virality_multiplier": 1.2,
        "performance_data": {},
        "is_active": True,
        "example_content": "Before:  I chased validation. After: I became the validator.",
        "internal_notes": "Keep transformations specific and believable.",
    },
    {
        "id": "expert_quote",
        "name": "Expert Quote",
        "template": '"{quote}" — {expert_name}',
        "description": "Borrowed authority. Quick to produce. Good for quote posts.",
        "best_for_pillars": ["PHILOSOPHY", "NEUROSCIENCE", "PRODUCTIVITY"],
        "avoid_for_pillars": [],
        "best_for_formats": ["QUOTE"],
        "avoid_for_formats": ["REEL"],  # Feels static for video
        "constraints": {
            "complexity_range": [1, 3],
            "requires_proof": True,
            "tone": "Authoritative",
        },
        "virality_multiplier": 1.15,
        "performance_data": {},
        "is_active": True,
        "example_content": '"The chief task in life is simply this: to identify and separate matters." — Epictetus',
        "internal_notes": "Verify quote attribution. Misattributed quotes damage trust.",
    },
    # ═══════════════════════════════════════════════════════════════
    # EMOTIONAL RESONANCE ANGLES (Virality Multiplier: 1.2-1.4)
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "permission_slip",
        "name": "Permission Slip",
        "template": "Reminder: It's okay to {permission}",
        "description": "Validates audience feelings. High comment engagement.  Builds loyalty.",
        "best_for_pillars": ["HEALING_GROWTH", "SELF_CARE", "SELF_WORTH"],
        "avoid_for_pillars": ["DARK_PSYCHOLOGY", "PRODUCTIVITY"],  # Too soft
        "best_for_formats": ["QUOTE", "REEL"],
        "avoid_for_formats": [],
        "constraints": {
            "complexity_range": [1, 2],
            "requires_proof": False,
            "tone": "Gentle",
        },
        "virality_multiplier": 1.25,
        "performance_data": {},
        "is_active": True,
        "example_content": "Reminder: It's okay to outgrow people who no longer serve your peace.",
        "internal_notes": "Use sparingly. Can feel performative if overused.",
    },
    {
        "id": "hard_truth_love",
        "name": "Hard Truth (with Love)",
        "template": "Nobody wants to hear this, but:  {truth}",
        "description": "Tough love framing.  Balances honesty with care.  High save rate.",
        "best_for_pillars": ["SELF_WORTH", "RELATIONSHIPS", "HEALING_GROWTH"],
        "avoid_for_pillars": [],
        "best_for_formats": ["QUOTE", "REEL", "CAROUSEL"],
        "avoid_for_formats": [],
        "constraints": {
            "complexity_range": [2, 4],
            "requires_proof": False,
            "tone": "Compassionate-Direct",
        },
        "virality_multiplier": 1.35,
        "performance_data": {},
        "is_active": True,
        "example_content": "Nobody wants to hear this, but: You're not afraid of commitment.  You're afraid of choosing wrong again.",
        "internal_notes": "End with hope or actionable insight.  Don't leave audience in despair.",
    },
    {
        "id": "you_are_not_alone",
        "name": "You're Not Alone",
        "template": "If you've ever felt {feeling}, this is for you.",
        "description": "Community builder. High comment engagement. Creates belonging.",
        "best_for_pillars": [
            "HEALING_GROWTH",
            "SELF_WORTH",
            "RELATIONSHIPS",
            "SELF_CARE",
        ],
        "avoid_for_pillars": ["PRODUCTIVITY", "DARK_PSYCHOLOGY"],
        "best_for_formats": ["REEL", "QUOTE"],
        "avoid_for_formats": [],
        "constraints": {
            "complexity_range": [1, 3],
            "requires_proof": False,
            "tone": "Empathetic",
        },
        "virality_multiplier": 1.3,
        "performance_data": {},
        "is_active": True,
        "example_content": "If you've ever felt like you're too much and not enough at the same time, this is for you.",
        "internal_notes": "Drives comments. Great for community building weeks.",
    },
    {
        "id": "villain_reveal",
        "name": "Villain Reveal",
        "template": "The real reason you {struggle} isn't {assumed_cause}.  It's {real_cause}.",
        "description": "Reframes the problem. Creates 'aha' moment. High share rate.",
        "best_for_pillars": [
            "DARK_PSYCHOLOGY",
            "RELATIONSHIPS",
            "SELF_WORTH",
            "NEUROSCIENCE",
        ],
        "avoid_for_pillars": [],
        "best_for_formats": ["REEL", "CAROUSEL"],
        "avoid_for_formats": ["QUOTE"],  # Needs explanation space
        "constraints": {
            "complexity_range": [3, 5],
            "requires_proof": False,
            "tone": "Revelatory",
        },
        "virality_multiplier": 1.4,
        "performance_data": {},
        "is_active": True,
        "example_content": "The real reason you procrastinate isn't laziness. It's fear of judgment.",
        "internal_notes": "Powerful for DARK_PSYCHOLOGY.  Reveal must feel earned.",
    },
    # ═══════════════════════════════════════════════════════════════
    # UTILITY ANGLES (Virality Multiplier: 1.0-1.2)
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "how_to",
        "name": "How-To Guide",
        "template": "How to {achieve_outcome} in {timeframe}",
        "description": "Pure utility. High save rate. Moderate virality but strong for SEO/search.",
        "best_for_pillars": ["PRODUCTIVITY", "SELF_CARE", "RELATIONSHIPS"],
        "avoid_for_pillars": ["PHILOSOPHY"],  # Too practical for philosophical content
        "best_for_formats": ["CAROUSEL", "REEL"],
        "avoid_for_formats": ["QUOTE"],
        "constraints": {
            "complexity_range": [2, 4],
            "requires_proof": False,
            "tone": "Instructive",
        },
        "virality_multiplier": 1.1,
        "performance_data": {},
        "is_active": True,
        "example_content": "How to rebuild self-trust after a betrayal (5 steps)",
        "internal_notes": "Reliable workhorse angle. Use for consistent value delivery.",
    },
    {
        "id": "list_post",
        "name": "Listicle",
        "template": "{Number} {things} that will {outcome}",
        "description": "Classic format.  Predictable performance. Good for content consistency.",
        "best_for_pillars": [
            "PRODUCTIVITY",
            "SELF_CARE",
            "NEUROSCIENCE",
            "HEALING_GROWTH",
        ],
        "avoid_for_pillars": [],
        "best_for_formats": ["CAROUSEL"],
        "avoid_for_formats": ["QUOTE"],
        "constraints": {
            "complexity_range": [1, 3],
            "requires_proof": False,
            "tone": "Helpful",
        },
        "virality_multiplier": 1.05,
        "performance_data": {},
        "is_active": True,
        "example_content": "7 habits that will change your mornings forever",
        "internal_notes": "Odd numbers (5, 7, 9) typically outperform even numbers.",
    },
    {
        "id": "comparison",
        "name": "Comparison",
        "template": "{Thing A} vs {Thing B}:  Which actually works? ",
        "description": "Decision helper. High save rate from people researching options.",
        "best_for_pillars": ["PRODUCTIVITY", "NEUROSCIENCE", "SELF_CARE"],
        "avoid_for_pillars": ["HEALING_GROWTH"],  # Too analytical for emotional content
        "best_for_formats": ["CAROUSEL"],
        "avoid_for_formats": ["QUOTE", "REEL"],
        "constraints": {
            "complexity_range": [2, 4],
            "requires_proof": True,
            "tone": "Analytical",
        },
        "virality_multiplier": 1.15,
        "performance_data": {},
        "is_active": True,
        "example_content": "Cold showers vs warm showers: What science actually says",
        "internal_notes": "Must be balanced and evidence-based.  Avoid clickbait conclusions.",
    },
    # ═══════════════════════════════════════════════════════════════
    # STORYTELLING ANGLES (Virality Multiplier: 1.25-1.4)
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "micro_story",
        "name": "Micro Story",
        "template": "A {person} once {action}.  Here's what happened next.",
        "description": "Narrative hook. Creates curiosity loop. Best for Reels.",
        "best_for_pillars": [
            "RELATIONSHIPS",
            "HEALING_GROWTH",
            "PHILOSOPHY",
            "DARK_PSYCHOLOGY",
        ],
        "avoid_for_pillars": [],
        "best_for_formats": ["REEL"],
        "avoid_for_formats": ["QUOTE"],
        "constraints": {
            "complexity_range": [2, 4],
            "requires_proof": False,
            "tone": "Narrative",
        },
        "virality_multiplier": 1.35,
        "performance_data": {},
        "is_active": True,
        "example_content": "A therapist once asked me one question that changed everything. Here's what happened.",
        "internal_notes": "Story must have clear resolution. Don't leave audience hanging.",
    },
    {
        "id": "case_study",
        "name": "Case Study",
        "template": "How {person/company} achieved {result} by doing {method}",
        "description": "Proof-based storytelling. High credibility. Good for carousels.",
        "best_for_pillars": ["PRODUCTIVITY", "NEUROSCIENCE"],
        "avoid_for_pillars": ["SELF_CARE", "HEALING_GROWTH"],  # Too clinical
        "best_for_formats": ["CAROUSEL", "REEL"],
        "avoid_for_formats": ["QUOTE"],
        "constraints": {
            "complexity_range": [3, 5],
            "requires_proof": True,
            "source_credibility_min": "MEDIUM",
            "tone": "Documentary",
        },
        "virality_multiplier": 1.25,
        "performance_data": {},
        "is_active": True,
        "example_content": "How a Google engineer eliminated burnout using this one scheduling trick",
        "internal_notes": "Name real people/companies when possible. Anonymize if needed.",
    },
    # ═══════════════════════════════════════════════════════════════
    # PHILOSOPHICAL/DEEP ANGLES (Virality Multiplier: 1.15-1.3)
    # ═══════════════════════════════════════════════════════════════
    {
        "id": "reframe",
        "name": "The Reframe",
        "template": "What if {common_view} is actually {alternative_view}?",
        "description": "Perspective shift.  Encourages reflection. High comment engagement.",
        "best_for_pillars": [
            "PHILOSOPHY",
            "RELATIONSHIPS",
            "SELF_WORTH",
            "HEALING_GROWTH",
        ],
        "avoid_for_pillars": [],
        "best_for_formats": ["QUOTE", "REEL"],
        "avoid_for_formats": [],
        "constraints": {
            "complexity_range": [2, 5],
            "requires_proof": False,
            "tone": "Thoughtful",
        },
        "virality_multiplier": 1.25,
        "performance_data": {},
        "is_active": True,
        "example_content": "What if loneliness isn't the absence of people, but the absence of meaning?",
        "internal_notes": "Best for Sunday/reflective posting times.",
    },
    {
        "id": "paradox",
        "name": "The Paradox",
        "template": "The more you {action A}, the less you {outcome}.  Here's why.",
        "description": "Counterintuitive wisdom. Creates cognitive engagement. High save rate.",
        "best_for_pillars": [
            "PHILOSOPHY",
            "NEUROSCIENCE",
            "PRODUCTIVITY",
            "RELATIONSHIPS",
        ],
        "avoid_for_pillars": [],
        "best_for_formats": ["CAROUSEL", "REEL", "QUOTE"],
        "avoid_for_formats": [],
        "constraints": {
            "complexity_range": [3, 5],
            "requires_proof": False,
            "tone": "Philosophical",
        },
        "virality_multiplier": 1.3,
        "performance_data": {},
        "is_active": True,
        "example_content": "The more you chase happiness, the more it runs from you. Here's the paradox.",
        "internal_notes": "Must resolve the paradox. Don't leave it as a riddle.",
    },
]


def seed_angle_matrix(session, dry_run: bool = False) -> tuple[int, int]:
    """
    Insert seed angles into the angle_matrix table.
    Skips existing angles to allow safe re-runs.

    Returns:
        Tuple of (inserted_count, skipped_count)
    """
    inserted = 0
    skipped = 0

    for angle_data in SEED_ANGLES:
        existing = session.get(AngleMatrix, angle_data["id"])
        if existing:
            logger.debug(f"Skipping existing angle: {angle_data['id']}")
            skipped += 1
            continue

        if dry_run:
            logger.info(
                f"[DRY RUN] Would insert: {angle_data['id']} - {angle_data['name']}"
            )
            inserted += 1
            continue

        angle = AngleMatrix(
            id=angle_data["id"],
            name=angle_data["name"],
            template=angle_data["template"],
            description=angle_data["description"],
            best_for_pillars=angle_data["best_for_pillars"],
            avoid_for_pillars=angle_data["avoid_for_pillars"],
            best_for_formats=angle_data["best_for_formats"],
            avoid_for_formats=angle_data["avoid_for_formats"],
            constraints=angle_data["constraints"],
            virality_multiplier=angle_data["virality_multiplier"],
            performance_data=angle_data["performance_data"],
            is_active=angle_data["is_active"],
            example_content=angle_data["example_content"],
            internal_notes=angle_data["internal_notes"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(angle)
        logger.info(f"Inserted: {angle_data['id']} - {angle_data['name']}")
        inserted += 1

    return inserted, skipped


def print_summary(inserted: int, skipped: int, dry_run: bool) -> None:
    """Print seeding summary."""
    print("\n" + "=" * 60)
    print("ANGLE MATRIX SEEDING SUMMARY")
    print("=" * 60)
    if dry_run:
        print("MODE:            DRY RUN (no changes made)")
    print(f"Total angles:    {len(SEED_ANGLES)}")
    print(f"Inserted:        {inserted}")
    print(f"Skipped:         {skipped}")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Seed angle_matrix table with 20 core angles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be inserted without writing to DB",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("seed_angles").setLevel(logging.DEBUG)

    if args.dry_run:
        logger.info("DRY RUN MODE - No database writes")

    try:
        with next(get_session()) as session:
            inserted, skipped = seed_angle_matrix(session, dry_run=args.dry_run)

            if not args.dry_run:
                session.commit()
                logger.info("Changes committed to database")

            print_summary(inserted, skipped, args.dry_run)

    except Exception as e:
        logger.exception(f"Seeding failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
