from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base
from app.settings import get_settings

settings = get_settings()
if settings.metadata_database_url.startswith("sqlite:///./"):
    Path("data").mkdir(parents=True, exist_ok=True)

connect_args = (
    {"check_same_thread": False}
    if settings.metadata_database_url.startswith("sqlite")
    else {}
)
engine = create_engine(settings.metadata_database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_db() -> Generator[Session, None, None]:
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()
