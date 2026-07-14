from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_session


router = APIRouter()


@router.get("/requirements")
def requirements(
    module: str = "",
    priority: str = "",
    session: Session = Depends(get_session),
):
    clauses = []
    params = {}
    if module:
        clauses.append("module = :module")
        params["module"] = module
    if priority:
        clauses.append("priority = :priority")
        params["priority"] = priority
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = session.execute(
        text(f"SELECT * FROM requirement_mappings{where} ORDER BY id"), params
    ).mappings().all()
    return [{**dict(row), "title": row["original"]} for row in rows]
