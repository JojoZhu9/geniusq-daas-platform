from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


def dashboard_name_exists(session: Session, name: str, exclude_dashboard_id: Optional[str] = None) -> bool:
    row = session.execute(
        text(
            "SELECT id FROM dashboards "
            "WHERE name = :name AND (:exclude_id IS NULL OR id != :exclude_id) "
            "LIMIT 1"
        ),
        {"name": name, "exclude_id": exclude_dashboard_id},
    ).mappings().first()
    return row is not None


def select_dashboard_row(session: Session, dashboard_id: str):
    return session.execute(
        text("SELECT * FROM dashboards WHERE id = :id"), {"id": dashboard_id}
    ).mappings().first()


def select_dashboard_id_by_share(session: Session, share_id: str):
    row = session.execute(
        text("SELECT id FROM dashboards WHERE share_id = :share_id"),
        {"share_id": share_id},
    ).mappings().first()
    return row["id"] if row else None


def select_dashboard_ids(session: Session) -> list[str]:
    return session.execute(
        text("SELECT id FROM dashboards ORDER BY updated_at DESC")
    ).scalars().all()
