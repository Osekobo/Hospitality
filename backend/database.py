import logging
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import get_settings

logger = logging.getLogger(__name__)

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


def _ensure_column(table_name: str, column_name: str, ddl: str) -> None:
    columns = {column["name"] for column in inspect(engine).get_columns(table_name)}
    if column_name in columns:
        return
    with engine.begin() as connection:
        connection.execute(text(ddl))


def _ensure_unique_index(table_name: str, index_name: str, columns: list[str], where: str = "") -> None:
    column_list = ", ".join(columns)
    duplicate_query = f"SELECT 1 FROM {table_name}"
    if where:
        duplicate_query += f" WHERE {where}"
    duplicate_query += f" GROUP BY {column_list} HAVING COUNT(*) > 1 LIMIT 1"

    with engine.connect() as connection:
        if connection.execute(text(duplicate_query)).first() is not None:
            logger.warning("Skipping unique index %s because duplicate rows exist", index_name)
            return

    predicate = f" WHERE {where}" if where else ""
    with engine.begin() as connection:
        connection.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} ON {table_name} ({column_list}){predicate}"))


def migrate_db() -> None:
    _ensure_column(
        "users",
        "reward_granted",
        "ALTER TABLE users ADD COLUMN reward_granted BOOLEAN NOT NULL DEFAULT false",
    )
    _ensure_column(
        "chat_messages",
        "external_id",
        "ALTER TABLE chat_messages ADD COLUMN external_id VARCHAR(120)",
    )
    with engine.begin() as connection:
        connection.execute(text("UPDATE users SET reward_granted = false WHERE reward_granted IS NULL"))
    _ensure_unique_index("users", "uq_user_platform_phone", ["platform", "phone_number"])
    _ensure_unique_index("chat_messages", "uq_chat_external_id", ["external_id"], "external_id IS NOT NULL")


def init_db() -> None:
    from seed import seed_demo_data

    Base.metadata.create_all(bind=engine)
    migrate_db()
    if settings.demo_mode:
        seed_demo_data()
