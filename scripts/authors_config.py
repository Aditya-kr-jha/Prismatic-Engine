"""
Blog Authors Configuration.

The Cognitive Supply Chain — Phase 1 (Ingestion)
------------------------------------------------
Curated list of 50 high-signal authors optimized for:
- Psychological virality
- Evergreen depth
- Scrape stability
- Pillar diversity

Each author is annotated with WHY they exist in the system.
"""

from typing import TypedDict, List

from app.db.enums import ContentPillar, BlogPlatform


class AuthorConfig(TypedDict):
    """Configuration for a blog author to scrape."""

    name: str
    platform: BlogPlatform
    blog_url: str
    max_articles: int
    content_pillars: List[ContentPillar]


# =============================================================================
# AUTHOR CONFIGURATIONS — ORGANIZED BY PRIMARY PILLAR
# =============================================================================

AUTHORS: List[AuthorConfig] = [
    # =====================================================================
    # PHILOSOPHY / METACOGNITION / SYSTEMS THINKING
    # =====================================================================
    # Existential visualization → scarcity panic → mass sharing
    {
        "name": "Tim Urban",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://waitbutwhy.com/archive",
        "max_articles": 50,
        "content_pillars": [ContentPillar.PHILOSOPHY, ContentPillar.PRODUCTIVITY],
    },
    # Rationalist culture, tribal cognition, high intellectual identity
    {
        "name": "Scott Alexander",
        "platform": BlogPlatform.SUBSTACK,
        "blog_url": "https://www.astralcodexten.com/archive",
        "max_articles": 50,
        "content_pillars": [ContentPillar.PHILOSOPHY, ContentPillar.NEUROSCIENCE],
    },
    # Long-form meaning, art, love, mortality — aesthetic depth
    {
        "name": "Maria Popova",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://www.themarginalian.org/archives",
        "max_articles": 50,
        "content_pillars": [
            ContentPillar.PHILOSOPHY,
            ContentPillar.HEALING_GROWTH,
            ContentPillar.RELATIONSHIPS,
        ],
    },
    # Culture, feminism, sex, power — high-friction opinion
    {
        "name": "Mary Harrington",
        "platform": BlogPlatform.SUBSTACK,
        "blog_url": "https://reactionaryfeminist.substack.com/archive",
        "max_articles": 50,
        "content_pillars": [ContentPillar.PHILOSOPHY, ContentPillar.RELATIONSHIPS],
    },
    # Cognitive biases, fashionable irrationality, elite signaling
    {
        "name": "Gurwinder Bhogal",
        "platform": BlogPlatform.SUBSTACK,
        "blog_url": "https://gurwinder.substack.com/archive",
        "max_articles": 50,
        "content_pillars": [ContentPillar.PHILOSOPHY, ContentPillar.DARK_PSYCHOLOGY],
    },
    # Systems, money psychology, fear & greed narratives
    {
        "name": "Morgan Housel",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://collabfund.com/blog/",
        "max_articles": 50,
        "content_pillars": [ContentPillar.PHILOSOPHY, ContentPillar.PRODUCTIVITY],
    },
    # Status signaling, evolutionary psychology, hidden motives
    {
        "name": "Kevin Simler",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://meltingasphalt.com/",
        "max_articles": 50,
        "content_pillars": [ContentPillar.PHILOSOPHY, ContentPillar.DARK_PSYCHOLOGY],
    },
    # Visual existential philosophy → highly shareable diagrams
    {
        "name": "Lawrence Yeo",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://moretothat.com/",
        "max_articles": 50,
        "content_pillars": [ContentPillar.PHILOSOPHY, ContentPillar.SELF_WORTH],
    },
    # =====================================================================
    # PRODUCTIVITY / HIGH AGENCY / WORK
    # =====================================================================
    # Mental models = high-status intellectual sharing
    {
        "name": "Shane Parrish",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://fs.blog/blog",
        "max_articles": 50,
        "content_pillars": [ContentPillar.PRODUCTIVITY, ContentPillar.PHILOSOPHY],
    },
    # Atomic habits → low friction, universal appeal
    {
        "name": "James Clear",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://jamesclear.com/articles",
        "max_articles": 50,
        "content_pillars": [ContentPillar.PRODUCTIVITY],
    },
    # Deep work, anti-distraction → saves > shares
    {
        "name": "Cal Newport",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://calnewport.com/blog/",
        "max_articles": 50,
        "content_pillars": [ContentPillar.PRODUCTIVITY, ContentPillar.PHILOSOPHY],
    },
    # Short aphorisms → perfect IG quote density
    {
        "name": "Derek Sivers",
        "platform": BlogPlatform.CUSTOM,
        "blog_url": "https://sive.rs/",
        "max_articles": 50,
        "content_pillars": [ContentPillar.PRODUCTIVITY, ContentPillar.PHILOSOPHY],
    },
    # Startup cognition, maker psychology
    {
        "name": "Paul Graham",
        "platform": BlogPlatform.CUSTOM,
        "blog_url": "http://paulgraham.com/articles.html",
        "max_articles": 50,
        "content_pillars": [ContentPillar.PRODUCTIVITY, ContentPillar.PHILOSOPHY],
    },
    # High-agency thinking, sharp one-liners
    {
        "name": "George Mack",
        "platform": BlogPlatform.CUSTOM,
        "blog_url": "https://www.george-mack.com/",
        "max_articles": 50,
        "content_pillars": [ContentPillar.PRODUCTIVITY, ContentPillar.PHILOSOPHY],
    },
    # =====================================================================
    # DARK PSYCHOLOGY / POWER / STATUS
    # =====================================================================
    # Applied power dynamics → insecurity-driven saves
    {
        "name": "Lucio Buffalmano",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://thepowermoves.com/blog/",
        "max_articles": 50,
        "content_pillars": [ContentPillar.DARK_PSYCHOLOGY, ContentPillar.RELATIONSHIPS],
    },
    # Red-pill hierarchy analysis → extreme polarization
    {
        "name": "Illimitable Man",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://illimitablemen.com/archives/",
        "max_articles": 50,
        "content_pillars": [ContentPillar.DARK_PSYCHOLOGY],
    },
    # Historical Machiavellianism → timeless power narratives
    {
        "name": "Robert Greene",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://powerseductionandwar.com/blog/",
        "max_articles": 50,
        "content_pillars": [ContentPillar.DARK_PSYCHOLOGY],
    },
    # Realist institutional critique → high arousal debate
    {
        "name": "Richard Hanania",
        "platform": BlogPlatform.SUBSTACK,
        "blog_url": "https://richardhanania.substack.com/archive",
        "max_articles": 50,
        "content_pillars": [ContentPillar.DARK_PSYCHOLOGY, ContentPillar.PHILOSOPHY],
    },
    # Stoicism + masculinity → identity validation
    {
        "name": "Ed Latimore",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://edlatimore.com/archives/",
        "max_articles": 50,
        "content_pillars": [ContentPillar.SELF_WORTH, ContentPillar.DARK_PSYCHOLOGY],
    },
    # =====================================================================
    # RELATIONSHIPS / EVOLUTIONARY PSYCHOLOGY
    # =====================================================================
    # Counter-intuitive emotional honesty → mass resonance
    {
        "name": "Mark Manson",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://markmanson.net/archive",
        "max_articles": 50,
        "content_pillars": [ContentPillar.SELF_WORTH, ContentPillar.RELATIONSHIPS],
    },
    # Intersexual dynamics → controversy engine
    {
        "name": "Rollo Tomassi",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://therationalmale.com/",
        "max_articles": 50,
        "content_pillars": [ContentPillar.RELATIONSHIPS, ContentPillar.DARK_PSYCHOLOGY],
    },
    # Relationship data science → fear-driven saves
    {
        "name": "John Gottman",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://www.gottman.com/blog/",
        "max_articles": 50,
        "content_pillars": [ContentPillar.RELATIONSHIPS],
    },
    # Desire, infidelity, attachment → emotional depth
    {
        "name": "Esther Perel",
        "platform": BlogPlatform.CUSTOM,
        "blog_url": "https://www.estherperel.com/blog",
        "max_articles": 50,
        "content_pillars": [ContentPillar.RELATIONSHIPS],
    },
    # Attachment theory simplified → mass emotional identification
    {
        "name": "Attached Blog",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://www.attachedthebook.com/blog/",
        "max_articles": 50,
        "content_pillars": [ContentPillar.RELATIONSHIPS, ContentPillar.HEALING_GROWTH],
    },
    # Dating psychology + power framing → high save/share
    {
        "name": "Mark Groves",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://markgroves.com/blog/",  # NEVER USE HIM AGAIN HE WRITE VERY SMALL ARTICLES.FEEL LIKE A TWITTER THREADS
        "max_articles": 50,
        "content_pillars": [ContentPillar.RELATIONSHIPS, ContentPillar.SELF_WORTH],
    },
    # Masculinity, polarity, commitment anxiety
    {
        "name": "David Deida",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://deida.info/blog/",
        "max_articles": 50,
        "content_pillars": [ContentPillar.RELATIONSHIPS],
    },
    # Blunt dating advice → polarizing, highly shareable
    {
        "name": "Evan Marc Katz",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://www.evanmarckatz.com/blog/",
        "max_articles": 50,
        "content_pillars": [ContentPillar.RELATIONSHIPS],
    },
    # Boundaries, self-respect → viral validation loops
    {
        "name": "Nedra Glover Tawwab",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://www.nedratawwab.com/blog",
        "max_articles": 50,
        "content_pillars": [ContentPillar.RELATIONSHIPS, ContentPillar.SELF_WORTH],
    },
    # Emotional availability, dating clarity → save-heavy
    {
        "name": "Matthew Hussey",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://www.matthewhussey.com/blog/",  # maybe skip him too
        "max_articles": 50,
        "content_pillars": [ContentPillar.RELATIONSHIPS],
    },
    # Female desire psychology → controversial, debate-heavy
    {
        "name": "Suzanne Venker",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://www.suzannevenker.com/blog/",
        "max_articles": 50,
        "content_pillars": [ContentPillar.RELATIONSHIPS, ContentPillar.PHILOSOPHY],
    },
    # Attachment wounds + childhood trauma framing
    {
        "name": "Brianna Wiest",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://briannawiest.com/blog/",
        "max_articles": 50,
        "content_pillars": [ContentPillar.RELATIONSHIPS, ContentPillar.HEALING_GROWTH],
    },
    # Emotional labor discourse → high identity projection
    {
        "name": "Clementine Ford",
        "platform": BlogPlatform.SUBSTACK,
        "blog_url": "https://clementineford.substack.com/archive",
        "max_articles": 50,
        "content_pillars": [ContentPillar.RELATIONSHIPS],
    },
    # Masculine self-respect, dating realism
    {
        "name": "The Attractive Man",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://attractiveman.com/blog/",
        "max_articles": 50,
        "content_pillars": [ContentPillar.RELATIONSHIPS, ContentPillar.SELF_WORTH],
    },
    # Commitment fear, modern dating collapse
    {
        "name": "Alain de Botton (Relationships)",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://www.theschooloflife.com/thebookoflife/relationships/",
        "max_articles": 50,
        "content_pillars": [ContentPillar.RELATIONSHIPS, ContentPillar.PHILOSOPHY],
    },
    # Marriage realism → triggers fear & hope simultaneously
    {
        "name": "Paul Byerly",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://www.happierhuman.com/blog/",
        "max_articles": 50,
        "content_pillars": [ContentPillar.RELATIONSHIPS],
    },
    # Female dating strategy discourse → extreme polarization
    {
        "name": "Female Dating Strategy",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://www.thefemaledatingstrategy.com/blog",
        "max_articles": 50,
        "content_pillars": [ContentPillar.RELATIONSHIPS, ContentPillar.DARK_PSYCHOLOGY],
    },
    # Emotional intelligence in love → mainstream viral
    {
        "name": "Psychology Today – Relationships",
        "platform": BlogPlatform.CUSTOM,
        "blog_url": "https://www.psychologytoday.com/us/basics/relationships",
        "max_articles": 50,
        "content_pillars": [ContentPillar.RELATIONSHIPS],
    },
    # =====================================================================
    # HEALING / TRAUMA / NEUROSCIENCE
    # =====================================================================
    # Trauma validation → viral checklists
    {
        "name": "Nicole LePera",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://theholisticpsychologist.com/blog/",  # SKIP
        "max_articles": 50,
        "content_pillars": [ContentPillar.HEALING_GROWTH],
    },
    # Nervous system regulation → practical relief
    {
        "name": "Irene Lyon",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://irenelyon.com/blog/",  # SKIP
        "max_articles": 50,
        "content_pillars": [ContentPillar.HEALING_GROWTH, ContentPillar.NEUROSCIENCE],
    },
    # Longevity, health optimization → elite biohacking
    {
        "name": "Peter Attia",
        "platform": BlogPlatform.WORDPRESS,
        "blog_url": "https://peterattiamd.com/category/blog/",  # SKIP
        "max_articles": 50,
        "content_pillars": [ContentPillar.NEUROSCIENCE, ContentPillar.SELF_CARE],
    },
    # Trauma theory foundation → authority anchor
    {
        "name": "Bessel van der Kolk",
        "platform": BlogPlatform.CUSTOM,
        "blog_url": "https://www.besselvanderkolk.com/resources",  # SKIP
        "max_articles": 50,
        "content_pillars": [ContentPillar.HEALING_GROWTH, ContentPillar.NEUROSCIENCE],
    },
]


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def get_authors_by_pillar(pillar: ContentPillar) -> List[AuthorConfig]:
    return [a for a in AUTHORS if pillar in a["content_pillars"]]


def get_authors_by_platform(platform: BlogPlatform) -> List[AuthorConfig]:
    return [a for a in AUTHORS if a["platform"] == platform]


def get_author_by_name(name: str) -> AuthorConfig | None:
    for a in AUTHORS:
        if a["name"].lower() == name.lower():
            return a
    return None


# =============================================================================
# STATISTICS
# =============================================================================

AUTHOR_COUNT = len(AUTHORS)
