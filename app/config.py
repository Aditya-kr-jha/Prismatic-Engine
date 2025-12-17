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
    ELEVENLABS_API_KEY: str = Field(
        default="",
        description="ElevenLabs API key for TTS",
    )

    class Config:
        env_file = os.path.join(_CONFIG_DIR, ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
