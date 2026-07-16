"""Shared pytest fixtures for isolated API tests."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_engine, get_session, init_database
from app.main import app


@pytest.fixture(autouse=True)
def default_offline_mode(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "offline")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    engine = get_engine(f"sqlite:///{tmp_path / 'api-test.db'}")
    init_database(engine)

    def override_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
