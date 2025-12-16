import os
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
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
    APP_ENV : str = Field(
        default="development",
        description="Application environment (development, staging, production)")
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


    class Config:
        env_file = os.path.join(_CONFIG_DIR, ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
