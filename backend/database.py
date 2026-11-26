from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import get_settings

settings = get_settings()

_database_url = settings.database_url
if _database_url.startswith("postgresql://"):
    _database_url = _database_url.replace("postgresql://", "postgresql+psycopg2://", 1)

engine_kwargs: dict[str, object] = {"pool_pre_ping": True}
if _database_url.startswith("sqlite:"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(_database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from seed import seed_demo_data

    Base.metadata.create_all(bind=engine)
    if settings.demo_mode:
        seed_demo_data()
