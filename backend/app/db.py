from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from .config import get_settings
from .seed import create_schema, seed_all


def get_engine(database_url: str) -> Engine:
    return create_engine(database_url, connect_args={"check_same_thread": False})


engine = get_engine(get_settings().database_url)


def init_database(target: Engine = engine) -> None:
    create_schema(target)
    seed_all(target)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
