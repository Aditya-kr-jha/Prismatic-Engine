from enum import Enum

class ContentPillar(str, Enum):
    PRODUCTIVITY = "productivity"
    DARK_PSYCHOLOGY = "dark_psychology"
    RELATIONSHIPS = "relationships"
    NEUROSCIENCE = "neuroscience"
    PHILOSOPHY = "philosophy"
    HEALING_GROWTH = "healing_growth"
    SELF_CARE = "self_care"
    SELF_WORTH = "self_worth"

class Format(str, Enum):
    REEL = "reel"
    CAROUSEL = "carousel"
    QUOTE = "quote"

class SourceType(str, Enum):
    REDDIT = "reddit"
    TWITTER = "twitter"
    PUBMED = "pubmed"
    GOOGLE_SCHOLAR = "google_scholar"
    YOUTUBE = "youtube"
    BOOK = "book"
    BLOG = "blog"
    MANUAL = "manual"
    COMPETITOR = "competitor"

class EmotionalTrigger(str, Enum):
    FEAR = "fear"
    VALIDATION = "validation"
    CURIOSITY = "curiosity"
    HOPE = "hope"
    ENVY = "envy"
    REBELLION = "rebellion"
    IDENTITY = "identity"
    EMPOWERMENT = "empowerment"
    NOSTALGIA = "nostalgia"

class IngestStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PASSED = "passed"
    REJECTED = "rejected"
    ERROR = "error"

class RejectionPhase(str, Enum):
    PRE_FILTER = "pre_filter"
    CLASSIFICATION = "classification"
    STRATEGY = "strategy"
    QA = "qa"

class SourceCredibility(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class LifecycleState(str, Enum):
    ACTIVE = "active"
    COOLING = "cooling"
    ARCHIVED = "archived"
    RETIRED = "retired"
    RESURRECTED = "resurrected"

class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    FLAGGED = "flagged"
    DISPUTED = "disputed"
    RETRACTED = "retracted"

class DayOfWeek(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"

class ScheduleStatus(str, Enum):
    SCHEDULED = "scheduled"
    CREATING = "creating"
    DRAFT = "draft"
    QA_PENDING = "qa_pending"
    QA_PASSED = "qa_passed"
    QA_FAILED = "qa_failed"
    PRODUCING = "producing"
    READY = "ready"
    DELIVERED = "delivered"
    PUBLISHED = "published"
    SKIPPED = "skipped"
    EMERGENCY = "emergency"

class EventType(str, Enum):
    HOLIDAY = "holiday"
    AWARENESS_DAY = "awareness_day"
    TRENDING_MOMENT = "trending_moment"
    BRAND_EVENT = "brand_event"
    CULTURAL = "cultural"
    SEASONAL = "seasonal"

class RemixType(str, Enum):
    CROSS_PILLAR = "cross_pillar"
    FORMAT_SHIFT = "format_shift"
    ANGLE_VARIATION = "angle_variation"
    SEASONAL = "seasonal"
    PERFORMANCE_BOOST = "performance_boost"

class QueueStatus(str, Enum):
    QUEUED = "queued"
    SELECTED = "selected"
    PUBLISHED = "published"
    SKIPPED = "skipped"
    EXPIRED = "expired"

class QAStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"

class Tone(str, Enum):
    EDGY = "edgy"
    GENTLE = "gentle"
    ACADEMIC = "academic"
    RELATABLE = "relatable"
    EMPOWERING = "empowering"

class SizeCategory(str, Enum):
    NICHE = "niche"
    MEDIUM = "medium"
    LARGE = "large"

class HashtagStatus(str, Enum):
    ACTIVE = "active"
    TESTING = "testing"
    BANNED = "banned"
    RETIRED = "retired"

class AssetType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    CAROUSEL_SET = "carousel_set"

class ProductionStatus(str, Enum):
    RENDERING = "rendering"
    READY = "ready"
    DELIVERED = "delivered"
    FAILED = "failed"

class PostingStatus(str, Enum):
    GENERATED = "generated"
    DELIVERED = "delivered"
    REVIEWED = "reviewed"
    POSTED = "posted"
    SKIPPED = "skipped"
    ARCHIVED = "archived"

class EmergencyStatus(str, Enum):
    AVAILABLE = "available"
    USED = "used"
    EXPIRED = "expired"

class SystemEventType(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    ALERT = "alert"
    RECOVERY = "recovery"

class SystemPhase(str, Enum):
    INGESTION = "ingestion"
    PRE_FILTER = "pre_filter"
    CLASSIFICATION = "classification"
    STRATEGY = "strategy"
    CREATION = "creation"
    QA = "qa"
    PRODUCTION = "production"
    DELIVERY = "delivery"
    LEARNING = "learning"
