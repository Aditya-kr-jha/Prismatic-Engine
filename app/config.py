import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

_CONFIG_DIR = Path(__file__).parent


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.

    All settings can be overridden via environment variables or a .env file
    located in the same directory as this config file.
    """

    # Database Configuration
    ECHO: bool = Field(
        default=True,
        description="Enable SQL query logging",
    )
    DB_USER: str = Field(default="fn7n48dr", description="Database username")
    DB_PASSWORD: str = Field(default="fn7n48dr", description="Database password")
    RDS_ENDPOINT: str = Field(default="fn7n48dr", description="RDS endpoint URL")
    DB_PORT: int = Field(default=5432, description="Database port")
    DB_NAME: str = Field(default="fn7n48dr", description="Database name")

    # AWS Configuration
    AWS_ACCESS_KEY_ID: str = Field(
        default="fhefhedfuefyeudnbfhefhuefuefuygeruf",
        description="AWS access key ID",
    )
    AWS_SECRET_ACCESS_KEY: str = Field(
        default="hefeyfrhiwdhefiheyfhienhyfhefy",
        description="AWS secret access key",
    )

    AWS_DEFAULT_REGION: str = Field(
        default="us-east-1",
        description="AWS region",
    )

    # HTTP Client Configuration
    HTTP_TIMEOUT_DEFAULT: float = Field(
        default=30.0,
        description="Default timeout for HTTP requests (seconds)",
    )
    HTTP_TIMEOUT_LLM: float = Field(
        default=120.0,
        description="Timeout for LLM API requests (seconds)",
    )

    # API Keys
    ANTHROPIC_API_KEY: str = Field(
        default="",
        description="Anthropic API key for Claude LLM",
    )
    OPENAI_API_KEY: str = Field(
        default="fjhfgryf765jhgryfrjnfjrghurgringr8u84urgjrgur784thr",
        description="OpenAI API key for GPT models",
    )
    LLM_MODEL: str = Field(
        default="gpt-5-mini",
        description="OpenAI LLM model name",
    )

    # Phase 5 Creation LLM Settings
    CREATION_LLM_MODEL: str = Field(
        default="gpt-5.2",
        description="LLM model for Phase 5 content creation",
    )
    CREATION_ANALYTICAL_MODEL: str = Field(
        default="gpt-5-mini",
        description="Cheaper LLM model for analytical stages (3.5 coherence, 4 critique)",
    )
    ELEVENLABS_API_KEY: str = Field(
        default="",
        description="ElevenLabs API key for TTS",
    )
    FIRECRAWL_API_KEY: str = Field(
        default="hurghrugrugjryfghurfrufgurfuruhfurh",
        description="Firecrawl API key for web scraping",
    )
    YOUTUBE_API_KEY: str = Field(
        default="",
        description="YouTube Data API v3 key for video metadata extraction",
    )

    # Scraping Settings
    SCRAPE_BATCH_SIZE: int = Field(
        default=50,
        description="Number of URLs to process per scraping batch",
    )
    MONTHLY_PAGE_LIMIT: int = Field(
        default=500,
        description="Maximum pages to scrape per month",
    )
    REQUEST_TIMEOUT: int = Field(
        default=15,
        description="Timeout for scraping requests (seconds)",
    )
    REQUEST_DELAY: float = Field(
        default=1.0,
        description="Delay between scraping requests (seconds)",
    )

    # Content Settings
    MIN_ARTICLE_WORDS: int = Field(
        default=200,
        description="Minimum word count for valid articles",
    )
    MAX_CHUNK_WORDS: int = Field(
        default=2000,
        description="Maximum word count per content chunk",
    )

    # ============================================================================
    # DELIVERY SETTINGS
    # ============================================================================

    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: str = Field(
        default="irjguriekjfeiefkjnrugut84u",
        description="Telegram bot token from @BotFather",
    )
    TELEGRAM_CHAT_ID: str = Field(
        default="6859695945949549",
        description="Your Telegram chat ID for notifications",
    )

    # Output directory
    DELIVERY_OUTPUT_DIR: str = Field(
        default="content_output",
        description="Directory for Markdown output files",
    )

    class Config:
        env_file = os.path.join(_CONFIG_DIR, ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
