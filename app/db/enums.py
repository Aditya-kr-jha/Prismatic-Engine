from enum import Enum


class ContentPillar(str, Enum):
    PRODUCTIVITY = "PRODUCTIVITY"
    DARK_PSYCHOLOGY = "DARK_PSYCHOLOGY"
    RELATIONSHIPS = "RELATIONSHIPS"
    NEUROSCIENCE = "NEUROSCIENCE"
    PHILOSOPHY = "PHILOSOPHY"
    HEALING_GROWTH = "HEALING_GROWTH"
    SELF_CARE = "SELF_CARE"
    SELF_WORTH = "SELF_WORTH"


PILLAR_SUBREDDITS: dict[ContentPillar, list[str]] = {
    ContentPillar.PRODUCTIVITY: ["productivity", "getdisciplined"],
    ContentPillar.DARK_PSYCHOLOGY: ["DarkPsychology101", "socialengineering"],
    ContentPillar.RELATIONSHIPS: ["relationships", "relationship_advice"],
    ContentPillar.NEUROSCIENCE: ["neuroscience", "neuro"],
    ContentPillar.PHILOSOPHY: ["philosophy", "askphilosophy"],
    ContentPillar.HEALING_GROWTH: ["selfimprovement", "DecidingToBeBetter"],
    ContentPillar.SELF_CARE: ["selfcare", "Mindfulness"],
    ContentPillar.SELF_WORTH: ["confidence", "selfesteem"],
}

# Reverse mapping: subreddit name (lowercase) -> ContentPillar
SUBREDDIT_TO_PILLAR: dict[str, ContentPillar] = {
    subreddit.lower(): pillar
    for pillar, subreddits in PILLAR_SUBREDDITS.items()
    for subreddit in subreddits
}


class Format(str, Enum):
    REEL = "REEL"
    CAROUSEL = "CAROUSEL"
    QUOTE = "QUOTE"


class SourceType(str, Enum):
    REDDIT = "REDDIT"
    TWITTER = "TWITTER"
    PUBMED = "PUBMED"
    GOOGLE_SCHOLAR = "GOOGLE_SCHOLAR"
    YOUTUBE = "YOUTUBE"
    BOOK = "BOOK"
    BLOG = "BLOG"
    MANUAL = "MANUAL"
    COMPETITOR = "COMPETITOR"


class EmotionalTrigger(str, Enum):
    FEAR = "FEAR"
    VALIDATION = "VALIDATION"
    CURIOSITY = "CURIOSITY"
    HOPE = "HOPE"
    ENVY = "ENVY"
    REBELLION = "REBELLION"
    IDENTITY = "IDENTITY"
    EMPOWERMENT = "EMPOWERMENT"
    NOSTALGIA = "NOSTALGIA"


class IngestStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PASSED = "PASSED"
    REJECTED = "REJECTED"
    ERROR = "ERROR"


class RejectionPhase(str, Enum):
    PRE_FILTER = "PRE_FILTER"
    CLASSIFICATION = "CLASSIFICATION"
    STRATEGY = "STRATEGY"
    QA = "QA"


class SourceCredibility(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class LifecycleState(str, Enum):
    ACTIVE = "ACTIVE"
    COOLING = "COOLING"
    ARCHIVED = "ARCHIVED"
    RETIRED = "RETIRED"
    RESURRECTED = "RESURRECTED"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    FLAGGED = "FLAGGED"
    DISPUTED = "DISPUTED"
    RETRACTED = "RETRACTED"


class ProofType(str, Enum):
    """Type of proof/evidence used in content."""

    ANECDOTE = "ANECDOTE"
    RESEARCH = "RESEARCH"
    STATISTIC = "STATISTIC"
    METAPHOR = "METAPHOR"
    QUOTE = "QUOTE"
    PERSONAL = "PERSONAL"
    SCIENTIFIC = "SCIENTIFIC"


class HookMechanism(str, Enum):
    """Type of hook used to capture attention."""

    CONTRARIAN = "CONTRARIAN"
    QUESTION = "QUESTION"
    STATISTIC = "STATISTIC"
    STORY = "STORY"
    CHALLENGE = "CHALLENGE"
    REVELATION = "REVELATION"


class DayOfWeek(str, Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


class ScheduleStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    CREATING = "CREATING"
    DRAFT = "DRAFT"
    DELIVERED = "DELIVERED"
    PUBLISHED = "PUBLISHED"
    SKIPPED = "SKIPPED"


class RemixType(str, Enum):
    CROSS_PILLAR = "CROSS_PILLAR"
    FORMAT_SHIFT = "FORMAT_SHIFT"
    ANGLE_VARIATION = "ANGLE_VARIATION"
    SEASONAL = "SEASONAL"
    PERFORMANCE_BOOST = "PERFORMANCE_BOOST"


class QueueStatus(str, Enum):
    QUEUED = "QUEUED"
    SELECTED = "SELECTED"
    PUBLISHED = "PUBLISHED"
    SKIPPED = "SKIPPED"
    EXPIRED = "EXPIRED"


class Tone(str, Enum):
    EDGY = "EDGY"
    GENTLE = "GENTLE"
    ACADEMIC = "ACADEMIC"
    RELATABLE = "RELATABLE"
    EMPOWERING = "EMPOWERING"


class GeneratedContentStatus(str, Enum):
    APPROVED = "APPROVED"
    FLAGGED_FOR_REVIEW = "FLAGGED_FOR_REVIEW"
    REJECTED = "REJECTED"


class EmergencyStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    USED = "USED"
    EXPIRED = "EXPIRED"


class SystemEventType(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    ALERT = "ALERT"
    RECOVERY = "RECOVERY"


class SystemPhase(str, Enum):
    INGESTION = "INGESTION"
    PRE_FILTER = "PRE_FILTER"
    CLASSIFICATION = "CLASSIFICATION"
    STRATEGY = "STRATEGY"
    CREATION = "CREATION"
    QA = "QA"
    PRODUCTION = "PRODUCTION"
    DELIVERY = "DELIVERY"
    LEARNING = "LEARNING"


# ============================================================================
# Pre-Ingestion Enums (Evergreen Content Reservoir)
# ============================================================================


class EvergreenSourceType(str, Enum):
    BOOK = "BOOK"
    BLOG = "BLOG"
    PODCAST = "PODCAST"


class FileType(str, Enum):
    PDF = "PDF"
    EPUB = "EPUB"


class EvergreenSourceStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReservoirStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    QUEUED = "QUEUED"
    USED = "USED"
    COOLDOWN = "COOLDOWN"


# ============================================================================
# Blog Scrape Tracker Enums
# ============================================================================


class ScrapeStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class BlogPlatform(str, Enum):
    WORDPRESS = "WORDPRESS"
    SUBSTACK = "SUBSTACK"
    GHOST = "GHOST"
    CUSTOM = "CUSTOM"


class DiscoveryMethod(str, Enum):
    SITEMAP = "SITEMAP"
    RSS = "RSS"
    CRAWL = "CRAWL"
    ARCHIVE = "ARCHIVE"
