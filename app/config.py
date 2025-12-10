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


    class Config:
        env_file = os.path.join(_CONFIG_DIR, ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
