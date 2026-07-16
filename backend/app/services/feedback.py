from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.services.conversation import utc_now
from app.services.knowledge import create_knowledge


VALID_RATINGS = {"correct", "incorrect", "useful", "not_useful"}


def save_analysis_feedback(
    session: Session, analysis_id: str, payload: dict[str, Any]
) -> dict[str, Any]:
    rating = str(payload.get("rating") or "")
    if rating not in VALID_RATINGS:
        raise ApiError(422, "FEEDBACK_RATING_INVALID", "反馈类型无效", "请选择有效反馈类型")
    row = session.execute(
        text("SELECT question, response_json FROM analysis_runs WHERE id = :id"),
        {"id": analysis_id},
    ).mappings().first()
    if row is None:
        raise ApiError(404, "ANALYSIS_NOT_FOUND", "分析任务不存在", "请重新提交问题")

    response = json.loads(row["response_json"])
    saved_knowledge_id = None
    if payload.get("save_as_example"):
        sql = response["queries"][0]["sql"] if response.get("queries") else ""
        if not sql:
            raise ApiError(422, "FEEDBACK_SQL_MISSING", "当前分析没有可沉淀的 SQL", "请选择包含 SQL 的分析结果")
        item = create_knowledge(
            session,
            {
                "name": f"示例 SQL：{row['question']}",
                "kind": "sql",
                "scope": "private",
                "library": "个人知识库",
                "content": sql,
                "linked_tables": response["datasets"][0]["tables"] if response.get("datasets") else [],
                "tags": ["SQL", "反馈示例", "Text-to-SQL"],
            },
        )
        saved_knowledge_id = item["id"]

    feedback_id = str(uuid.uuid4())
    timestamp = utc_now()
    session.execute(
        text(
            """
            INSERT INTO analysis_feedback
                (id, analysis_id, rating, comment, save_as_example, saved_knowledge_id, created_at)
            VALUES
                (:id, :analysis_id, :rating, :comment, :save_as_example, :saved_knowledge_id, :created_at)
            """
        ),
        {
            "id": feedback_id,
            "analysis_id": analysis_id,
            "rating": rating,
            "comment": str(payload.get("comment") or ""),
            "save_as_example": 1 if payload.get("save_as_example") else 0,
            "saved_knowledge_id": saved_knowledge_id,
            "created_at": timestamp,
        },
    )
    session.commit()
    return {
        "id": feedback_id,
        "analysis_id": analysis_id,
        "rating": rating,
        "comment": str(payload.get("comment") or ""),
        "save_as_example": bool(payload.get("save_as_example")),
        "saved_knowledge_id": saved_knowledge_id,
        "created_at": timestamp,
    }
