from typing import Generator, Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session

from app.config import settings

# Construct the PostgreSQL URL directly
DATABASE_URL = (
    f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}"
    f"@{settings.RDS_ENDPOINT}:{settings.DB_PORT}/{settings.DB_NAME}"
)

engine = create_engine(
    DATABASE_URL,
    echo=settings.ECHO,
    connect_args={
        "sslmode": "require",
        "options": "-c application_name=PrismaticEngine",
    },
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine, class_=Session, autoflush=False, autocommit=False
)


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
