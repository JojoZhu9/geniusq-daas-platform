from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize_card(row: Any) -> dict[str, Any]:
    item = dict(row)
    analysis_response = item.pop("analysis_response_json", None)
    item["chart"] = json.loads(item.pop("chart_json"))
    item["datasets"] = (
        json.loads(analysis_response).get("datasets", []) if analysis_response else []
    )
    item["layout"] = {
        "x": item.pop("x"),
        "y": item.pop("y"),
        "w": item.pop("w"),
        "h": item.pop("h"),
    }
    item["requirement_ids"] = ["2.4-a", "2.6"]
    return item


def get_dashboard(session: Session, dashboard_id: str) -> dict[str, Any] | None:
    row = session.execute(
        text("SELECT * FROM dashboards WHERE id = :id"), {"id": dashboard_id}
    ).mappings().first()
    if row is None:
        return None
    dashboard = dict(row)
    cards = session.execute(
        text(
            "SELECT dashboard_cards.*, "
            "analysis_runs.response_json AS analysis_response_json "
            "FROM dashboard_cards "
            "LEFT JOIN analysis_runs ON analysis_runs.id = dashboard_cards.analysis_id "
            "WHERE dashboard_cards.dashboard_id = :dashboard_id "
            "ORDER BY dashboard_cards.y, dashboard_cards.x, dashboard_cards.created_at"
        ),
        {"dashboard_id": dashboard_id},
    ).mappings().all()
    dashboard["cards"] = [_serialize_card(card) for card in cards]
    dashboard["share_url"] = f"/share/{dashboard['share_id']}"
    dashboard["requirement_ids"] = ["2.6"]
    return dashboard


def get_dashboard_by_share(session: Session, share_id: str) -> dict[str, Any] | None:
    row = session.execute(
        text("SELECT id FROM dashboards WHERE share_id = :share_id"),
        {"share_id": share_id},
    ).mappings().first()
    return get_dashboard(session, row["id"]) if row else None


def list_dashboards(session: Session) -> list[dict[str, Any]]:
    ids = session.execute(
        text("SELECT id FROM dashboards ORDER BY updated_at DESC")
    ).scalars().all()
    return [get_dashboard(session, dashboard_id) for dashboard_id in ids]


def create_dashboard(session: Session, name: str) -> dict[str, Any]:
    dashboard_id = str(uuid.uuid4())
    timestamp = _now()
    session.execute(
        text(
            "INSERT INTO dashboards (id, name, share_id, created_at, updated_at) "
            "VALUES (:id, :name, :share_id, :created_at, :updated_at)"
        ),
        {
            "id": dashboard_id,
            "name": name,
            "share_id": str(uuid.uuid4()),
            "created_at": timestamp,
            "updated_at": timestamp,
        },
    )
    session.commit()
    return get_dashboard(session, dashboard_id)


def rename_dashboard(session: Session, dashboard_id: str, name: str) -> dict[str, Any] | None:
    if get_dashboard(session, dashboard_id) is None:
        return None
    timestamp = _now()
    session.execute(
        text("UPDATE dashboards SET name = :name, updated_at = :updated_at WHERE id = :id"),
        {"name": name, "updated_at": timestamp, "id": dashboard_id},
    )
    session.commit()
    return get_dashboard(session, dashboard_id)


def add_card(
    session: Session,
    dashboard_id: str,
    title: str,
    analysis_id: str,
    chart: dict[str, Any],
    layout: dict[str, int],
) -> dict[str, Any] | None:
    if get_dashboard(session, dashboard_id) is None:
        return None
    card_id = str(uuid.uuid4())
    timestamp = _now()
    session.execute(
        text(
            """
            INSERT INTO dashboard_cards
                (id, dashboard_id, title, analysis_id, chart_json,
                 x, y, w, h, created_at, updated_at)
            VALUES
                (:id, :dashboard_id, :title, :analysis_id, :chart,
                 :x, :y, :w, :h, :created_at, :updated_at)
            """
        ),
        {
            "id": card_id,
            "dashboard_id": dashboard_id,
            "title": title,
            "analysis_id": analysis_id,
            "chart": json.dumps(chart, ensure_ascii=False),
            **layout,
            "created_at": timestamp,
            "updated_at": timestamp,
        },
    )
    session.execute(
        text("UPDATE dashboards SET updated_at = :now WHERE id = :id"),
        {"now": timestamp, "id": dashboard_id},
    )
    session.commit()
    row = session.execute(
        text(
            "SELECT dashboard_cards.*, "
            "analysis_runs.response_json AS analysis_response_json "
            "FROM dashboard_cards "
            "LEFT JOIN analysis_runs ON analysis_runs.id = dashboard_cards.analysis_id "
            "WHERE dashboard_cards.id = :id"
        ),
        {"id": card_id},
    ).mappings().one()
    return _serialize_card(row)


def update_layout(
    session: Session, dashboard_id: str, cards: list[dict[str, Any]]
) -> dict[str, Any] | None:
    if get_dashboard(session, dashboard_id) is None:
        return None
    timestamp = _now()
    for card in cards:
        session.execute(
            text(
                """
                UPDATE dashboard_cards
                SET x = :x, y = :y, w = :w, h = :h, updated_at = :updated_at
                WHERE id = :id AND dashboard_id = :dashboard_id
                """
            ),
            {**card, "dashboard_id": dashboard_id, "updated_at": timestamp},
        )
    session.execute(
        text("UPDATE dashboards SET updated_at = :now WHERE id = :id"),
        {"now": timestamp, "id": dashboard_id},
    )
    session.commit()
    return get_dashboard(session, dashboard_id)


def remove_card(session: Session, dashboard_id: str, card_id: str) -> bool:
    result = session.execute(
        text(
            "DELETE FROM dashboard_cards WHERE id = :id AND dashboard_id = :dashboard_id"
        ),
        {"id": card_id, "dashboard_id": dashboard_id},
    )
    session.commit()
    return bool(result.rowcount)
