from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.db import get_engine, init_database


def test_init_database_seeds_business_tables(tmp_path):
    engine = get_engine(f"sqlite:///{tmp_path / 'demo.db'}")
    try:
        init_database(engine)

        assert {
            "house_price_monthly",
            "housing_transactions",
            "district_population",
            "commuting_metrics",
            "requirement_mappings",
        }.issubset(inspect(engine).get_table_names())
        with engine.connect() as connection:
            count = connection.execute(
                text("select count(*) from house_price_monthly")
            ).scalar_one()
            enriched = connection.execute(
                text(
                    "select rent_price, listing_count, vacancy_rate "
                    "from house_price_monthly limit 1"
                )
            ).mappings().one()
        assert count >= 24
        assert enriched["rent_price"] > 0
        assert enriched["listing_count"] > 0
        assert enriched["vacancy_rate"] > 0
    finally:
        engine.dispose()


def test_settings_default_to_offline_local_database():
    from app.config import Settings

    settings = Settings(_env_file=None)

    normalized_database_url = settings.database_url.replace("\\", "/")

    assert normalized_database_url.startswith("sqlite:///")
    assert normalized_database_url.endswith("/backend/runtime/daas_demo.db")
    assert settings.llm_mode == "offline"
    assert settings.query_row_limit == 500
    assert settings.cors_origin_list == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://geniusq-daas-platform.vercel.app",
    ]
    assert settings.cors_origin_regex == r"https://.*\.vercel\.app"


def test_settings_parse_cors_origins_from_comma_separated_env(monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("CORS_ORIGINS", "https://demo.vercel.app, https://preview.vercel.app ")
    settings = Settings(_env_file=None)

    assert settings.cors_origin_list == ["https://demo.vercel.app", "https://preview.vercel.app"]


def test_get_session_yields_sqlalchemy_session():
    from app.db import get_session

    sessions = get_session()
    session = next(sessions)
    try:
        assert isinstance(session, Session)
    finally:
        sessions.close()


def test_health_reports_offline_mode():
    from app.main import app

    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "offline"}


def test_cors_allows_default_local_frontend_origin():
    from app.main import app

    response = TestClient(app).options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
