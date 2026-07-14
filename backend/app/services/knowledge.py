from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.services.sql_guard import TABLE_REF


def normalize_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip().lower()).rstrip(";")


def knowledge_fingerprint(kind: str, content: str, linked_tables: list[str]) -> str:
    canonical = {
        "kind": kind,
        "content": normalize_sql(content) if kind == "sql" else " ".join(content.split()),
        "linked_tables": sorted(set(linked_tables)),
    }
    raw = json.dumps(canonical, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize(row: Any) -> dict[str, Any]:
    item = dict(row)
    item["linked_tables"] = json.loads(item.pop("linked_tables_json"))
    item["tags"] = json.loads(item.pop("tags_json"))
    item["conflict"] = (
        {
            "message": "私有知识优先，公开条目被覆盖",
            "overrides_id": item["overrides_id"],
        }
        if item["overrides_id"]
        else None
    )
    item["requirement_ids"] = ["3.2", "3.4-a", "3.4-b"]
    if item["kind"] == "sql":
        item["requirement_ids"].append("3.4-c")
    return item


def _normalized_payload(payload: dict[str, Any]) -> dict[str, Any]:
    linked_tables = sorted(set(payload.get("linked_tables", [])))
    if payload["kind"] == "sql":
        linked_tables = sorted(set(linked_tables) | set(TABLE_REF.findall(payload["content"])))
    return {
        **payload,
        "linked_tables": linked_tables,
        "tags": sorted(set(payload.get("tags", []))),
        "fingerprint": knowledge_fingerprint(
            payload["kind"], payload["content"], linked_tables
        ),
    }


def check_duplicate(session: Session, payload: dict[str, Any]) -> dict[str, Any]:
    data = _normalized_payload(payload)
    rows = session.execute(
        text("SELECT * FROM knowledge_items WHERE fingerprint = :fingerprint"),
        {"fingerprint": data["fingerprint"]},
    ).mappings().all()
    same_library = next((row for row in rows if row["library"] == data["library"]), None)
    if same_library:
        return {
            "duplicate": True,
            "existing_id": same_library["id"],
            "priority": "same_library_duplicate",
            "overrides_id": None,
        }
    public_match = next((row for row in rows if row["scope"] == "public"), None)
    private_match = next((row for row in rows if row["scope"] == "private"), None)
    if data["scope"] == "private" and public_match:
        return {
            "duplicate": False,
            "existing_id": public_match["id"],
            "priority": "private_over_public",
            "overrides_id": public_match["id"],
        }
    if data["scope"] == "public" and private_match:
        return {
            "duplicate": False,
            "existing_id": private_match["id"],
            "priority": "public_covered_by_private",
            "overrides_id": None,
        }
    return {
        "duplicate": False,
        "existing_id": None,
        "priority": "independent",
        "overrides_id": None,
    }


def create_knowledge(session: Session, payload: dict[str, Any]) -> dict[str, Any]:
    data = _normalized_payload(payload)
    duplicate = check_duplicate(session, data)
    if duplicate["duplicate"]:
        raise ApiError(
            409,
            "KNOWLEDGE_DUPLICATE",
            "同一知识库中已存在相同内容",
            "请打开已有条目进行编辑",
            existing_id=duplicate["existing_id"],
        )
    item_id = str(uuid.uuid4())
    session.execute(
        text(
            """
            INSERT INTO knowledge_items
                (id, name, kind, scope, library, content, fingerprint,
                 linked_tables_json, tags_json, schema_status, overrides_id, created_at)
            VALUES
                (:id, :name, :kind, :scope, :library, :content, :fingerprint,
                 :linked_tables, :tags, 'valid', :overrides_id, :created_at)
            """
        ),
        {
            "id": item_id,
            "name": data["name"],
            "kind": data["kind"],
            "scope": data["scope"],
            "library": data["library"],
            "content": data["content"],
            "fingerprint": data["fingerprint"],
            "linked_tables": json.dumps(data["linked_tables"], ensure_ascii=False),
            "tags": json.dumps(data["tags"], ensure_ascii=False),
            "overrides_id": duplicate["overrides_id"],
            "created_at": _now(),
        },
    )
    session.commit()
    return get_knowledge(session, item_id)


def get_knowledge(session: Session, item_id: str) -> dict[str, Any] | None:
    row = session.execute(
        text("SELECT * FROM knowledge_items WHERE id = :id"), {"id": item_id}
    ).mappings().first()
    return _serialize(row) if row else None


def list_knowledge(
    session: Session,
    query: str = "",
    kind: str = "",
    scope: str = "",
    tag: str = "",
) -> list[dict[str, Any]]:
    rows = session.execute(
        text(
            "SELECT * FROM knowledge_items "
            "ORDER BY CASE scope WHEN 'private' THEN 0 ELSE 1 END, created_at DESC"
        )
    ).mappings().all()
    items = [_serialize(row) for row in rows]
    normalized_query = query.strip().lower()
    return [
        item
        for item in items
        if (not normalized_query or normalized_query in f"{item['name']} {item['content']}".lower())
        and (not kind or item["kind"] == kind)
        and (not scope or item["scope"] == scope)
        and (not tag or tag in item["tags"])
    ]


def delete_knowledge(session: Session, item_id: str) -> bool:
    result = session.execute(
        text("DELETE FROM knowledge_items WHERE id = :id"), {"id": item_id}
    )
    session.commit()
    return bool(result.rowcount)


def run_sync(mode: str, session: Session) -> dict[str, Any]:
    if mode not in {"manual", "scheduled_demo"}:
        raise ApiError(422, "SYNC_MODE_INVALID", "同步模式无效", "请选择手动或模拟定时同步")
    log_id = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    timestamp = _now()
    tables = [
        row["name"]
        for row in session.execute(
            text("SELECT name FROM data_tables WHERE status = 'active' ORDER BY name")
        ).mappings()
    ]
    session.execute(
        text(
            """
            INSERT INTO sync_logs
                (id, request_id, mode, status, message, changed_tables_json, created_at)
            VALUES (:id, :request_id, :mode, 'completed', :message, :tables, :created_at)
            """
        ),
        {
            "id": log_id,
            "request_id": request_id,
            "mode": mode,
            "message": f"已完成 {len(tables)} 张演示数据表的元数据同步",
            "tables": json.dumps(tables, ensure_ascii=False),
            "created_at": timestamp,
        },
    )
    session.commit()
    return {
        "id": log_id,
        "request_id": request_id,
        "mode": mode,
        "status": "completed",
        "message": f"已完成 {len(tables)} 张演示数据表的元数据同步",
        "changed_tables": tables,
        "created_at": timestamp,
        "requirement_ids": ["3.3"],
    }


def list_sync_logs(session: Session) -> list[dict[str, Any]]:
    rows = session.execute(
        text("SELECT * FROM sync_logs ORDER BY created_at DESC")
    ).mappings().all()
    result = []
    for row in rows:
        item = dict(row)
        item["changed_tables"] = json.loads(item.pop("changed_tables_json"))
        result.append(item)
    return result


def delete_data_table(session: Session, table_name: str, confirm: bool) -> dict[str, Any]:
    table = session.execute(
        text("SELECT * FROM data_tables WHERE name = :name"), {"name": table_name}
    ).mappings().first()
    if table is None:
        raise ApiError(404, "DATA_TABLE_NOT_FOUND", "数据表不存在", "请刷新数据表列表")
    affected = [
        item
        for item in list_knowledge(session)
        if table_name in item["linked_tables"]
    ]
    if not confirm:
        raise ApiError(
            409,
            "TABLE_DELETE_CONFIRMATION_REQUIRED",
            "删除数据表会联动移除关联知识",
            "确认影响范围后再次提交删除",
            affected_knowledge_count=len(affected),
            affected_knowledge=[{"id": item["id"], "name": item["name"]} for item in affected],
        )
    for item in affected:
        session.execute(text("DELETE FROM knowledge_items WHERE id = :id"), {"id": item["id"]})
    session.execute(
        text("UPDATE data_tables SET status = 'unavailable', updated_at = :now WHERE name = :name"),
        {"name": table_name, "now": _now()},
    )
    session.commit()
    return {
        "table": table_name,
        "table_status": "unavailable",
        "linked_items_removed": len(affected),
        "requirement_ids": ["3.3"],
    }
