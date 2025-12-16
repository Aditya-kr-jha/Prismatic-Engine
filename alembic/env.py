import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import settings

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context
from sqlmodel import SQLModel

# Import all models to register them with SQLModel.metadata


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def get_database_url() -> str:
    """Return database URL based on environment."""
    BASE_DIR = Path(__file__).resolve().parent.parent
    DB_PATH = BASE_DIR / "prismatic.db"

    SQLITE_URL = f"sqlite:///{DB_PATH}"
    RDS_URL = (
        f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.RDS_ENDPOINT}:{settings.DB_PORT}/{settings.DB_NAME}"
    )

    return RDS_URL if settings.APP_ENV.lower() in {"prod", "production"} else SQLITE_URL


def run_migrations_offline() -> None:
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
