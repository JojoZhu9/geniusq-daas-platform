from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas import QueryContext


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_conversation(session: Session) -> dict[str, Any]:
    conversation_id = str(uuid.uuid4())
    timestamp = utc_now()
    context = QueryContext()
    session.execute(
        text(
            "INSERT INTO conversations "
            "(id, context_json, created_at, updated_at) "
            "VALUES (:id, :context, :created_at, :updated_at)"
        ),
        {
            "id": conversation_id,
            "context": context.model_dump_json(),
            "created_at": timestamp,
            "updated_at": timestamp,
        },
    )
    session.commit()
    return {"id": conversation_id, "context": context.model_dump(), "created_at": timestamp}


def load_context(session: Session, conversation_id: str) -> QueryContext | None:
    row = session.execute(
        text("SELECT context_json FROM conversations WHERE id = :id"),
        {"id": conversation_id},
    ).mappings().first()
    if row is None:
        return None
    return QueryContext(**json.loads(row["context_json"]))


def get_analysis(session: Session, analysis_id: str) -> dict[str, Any] | None:
    row = session.execute(
        text("SELECT response_json FROM analysis_runs WHERE id = :id"),
        {"id": analysis_id},
    ).mappings().first()
    return json.loads(row["response_json"]) if row else None


def list_conversations(session: Session) -> list[dict[str, Any]]:
    rows = session.execute(
        text(
            """
            SELECT
                conversations.id,
                conversations.created_at,
                conversations.updated_at,
                first_run.question AS title,
                latest_run.question AS latest_question,
                latest_run.status AS latest_status,
                COALESCE(run_counts.analysis_count, 0) AS analysis_count
            FROM conversations
            LEFT JOIN analysis_runs AS first_run
                ON first_run.id = (
                    SELECT id FROM analysis_runs
                    WHERE conversation_id = conversations.id
                    ORDER BY created_at ASC
                    LIMIT 1
                )
            LEFT JOIN analysis_runs AS latest_run
                ON latest_run.id = (
                    SELECT id FROM analysis_runs
                    WHERE conversation_id = conversations.id
                    ORDER BY created_at DESC
                    LIMIT 1
                )
            LEFT JOIN (
                SELECT conversation_id, COUNT(*) AS analysis_count
                FROM analysis_runs
                GROUP BY conversation_id
            ) AS run_counts
                ON run_counts.conversation_id = conversations.id
            ORDER BY conversations.updated_at DESC
            """
        )
    ).mappings().all()
    return [
        {
            "id": row["id"],
            "title": row["title"] or "新建会话",
            "latest_question": row["latest_question"],
            "latest_status": row["latest_status"],
            "analysis_count": row["analysis_count"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def get_conversation_history(session: Session, conversation_id: str) -> dict[str, Any] | None:
    conversation = session.execute(
        text(
            "SELECT id, context_json, created_at, updated_at "
            "FROM conversations WHERE id = :id"
        ),
        {"id": conversation_id},
    ).mappings().first()
    if conversation is None:
        return None
    rows = session.execute(
        text(
            "SELECT question, response_json, created_at "
            "FROM analysis_runs "
            "WHERE conversation_id = :conversation_id "
            "ORDER BY created_at ASC"
        ),
        {"conversation_id": conversation_id},
    ).mappings().all()
    exchanges = [
        {
            "question": row["question"],
            "response": json.loads(row["response_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]
    return {
        "id": conversation["id"],
        "context": json.loads(conversation["context_json"]),
        "created_at": conversation["created_at"],
        "updated_at": conversation["updated_at"],
        "title": exchanges[0]["question"] if exchanges else "新建会话",
        "exchanges": exchanges,
    }

