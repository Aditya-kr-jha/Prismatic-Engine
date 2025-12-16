from pathlib import Path
from typing import Generator, Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlmodel import SQLModel

from app.config import settings

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "prismatic.db"

SQLITE_URL = f"sqlite:///{DB_PATH}"
RDS_URL = (
    f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}"
    f"@{settings.RDS_ENDPOINT}:{settings.DB_PORT}/{settings.DB_NAME}"
)

DATABASE_URL = RDS_URL if settings.APP_ENV.lower() in {"prod", "production"} else SQLITE_URL

engine = create_engine(
    DATABASE_URL,
    echo=settings.ECHO,
    connect_args=(
        {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else
        {"sslmode": "require", "options": "-c application_name=Lumina"}
    ),
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(bind=engine)


def get_session() -> Generator[Session, Any, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()