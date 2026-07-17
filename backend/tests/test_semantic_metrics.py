from sqlalchemy.orm import Session

from app.db import get_engine, init_database
from app.services.semantic import retrieve_semantic_metrics


def test_retrieves_semantic_metrics_by_aliases(tmp_path):
    engine = get_engine(f"sqlite:///{tmp_path / 'semantic.db'}")
    try:
        init_database(engine)
        with Session(engine) as session:
            metrics = retrieve_semantic_metrics(session, "分析2025年各区库存压力和租售比")

        ids = [metric.id for metric in metrics]
        assert "inventory_pressure" in ids
        assert "rent_to_price_ratio" in ids
        inventory = next(metric for metric in metrics if metric.id == "inventory_pressure")
        assert inventory.formula == "listing_count / transaction_count"
        assert inventory.fields == ["listing_count", "transaction_count"]
        assert inventory.tables == ["house_price_monthly", "housing_transactions"]
    finally:
        engine.dispose()
