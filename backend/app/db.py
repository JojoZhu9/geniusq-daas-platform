from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from .config import get_settings
from .seed import create_schema, seed_all


def get_engine(database_url: str) -> Engine:
    ensure_sqlite_parent(database_url)
    return create_engine(database_url, connect_args={"check_same_thread": False})


def ensure_sqlite_parent(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return

    sqlite_path = database_url.removeprefix("sqlite:///")
    if sqlite_path in {"", ":memory:"}:
        return

    Path(sqlite_path).expanduser().parent.mkdir(parents=True, exist_ok=True)


engine = get_engine(get_settings().database_url)


def init_database(target: Engine = engine) -> None:
    create_schema(target)
    seed_all(target)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
