from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db import get_engine, init_database
from app.services.retrieval import retrieve_relevant_knowledge


def test_retrieves_private_house_price_knowledge_first(tmp_path):
    engine = get_engine(f"sqlite:///{tmp_path / 'retrieval.db'}")
    init_database(engine)
    try:
        with Session(engine) as session:
            results = retrieve_relevant_knowledge(session, "分析2025年各区房价趋势")
    finally:
        engine.dispose()

    assert [item.id for item in results[:2]] == [
        "knowledge-private-house-price",
        "knowledge-sql-trend",
    ]
    assert results[0].scope == "private"
    assert "house_price_monthly" in results[0].linked_tables
    assert results[0].score > results[-1].score


def test_retrieval_excludes_unavailable_table_knowledge(tmp_path):
    engine = get_engine(f"sqlite:///{tmp_path / 'retrieval-unavailable.db'}")
    init_database(engine)
    try:
        with Session(engine) as session:
            session.execute(
                text(
                    "UPDATE data_tables SET status = 'unavailable' "
                    "WHERE name = 'house_price_monthly'"
                )
            )
            session.commit()

            results = retrieve_relevant_knowledge(session, "分析房价")
    finally:
        engine.dispose()

    assert results == []
