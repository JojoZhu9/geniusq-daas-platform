from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_session
from app.errors import ApiError
from app.services.knowledge import (
    check_duplicate,
    create_knowledge,
    delete_data_table,
    delete_knowledge,
    get_knowledge,
    list_knowledge,
    list_sync_logs,
    run_sync,
)


router = APIRouter()


class KnowledgeInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: Literal["text", "sql", "rule"]
    scope: Literal["private", "public"]
    library: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=10_000)
    linked_tables: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class SyncInput(BaseModel):
    mode: Literal["manual", "scheduled_demo"] = "manual"


@router.get("/knowledge")
def knowledge_list(
    query: str = "",
    kind: str = "",
    scope: str = "",
    tag: str = "",
    session: Session = Depends(get_session),
):
    return list_knowledge(session, query=query, kind=kind, scope=scope, tag=tag)


@router.get("/knowledge/{item_id}")
def knowledge_detail(item_id: str, session: Session = Depends(get_session)):
    item = get_knowledge(session, item_id)
    if item is None:
        raise ApiError(404, "KNOWLEDGE_NOT_FOUND", "知识条目不存在", "请刷新知识列表")
    return item


@router.post("/knowledge", status_code=201)
def knowledge_create(payload: KnowledgeInput, session: Session = Depends(get_session)):
    return create_knowledge(session, payload.model_dump())


@router.post("/knowledge/deduplicate")
def knowledge_deduplicate(payload: KnowledgeInput, session: Session = Depends(get_session)):
    return check_duplicate(session, payload.model_dump())


@router.delete("/knowledge/{item_id}", status_code=204)
def knowledge_delete(item_id: str, session: Session = Depends(get_session)):
    if not delete_knowledge(session, item_id):
        raise ApiError(404, "KNOWLEDGE_NOT_FOUND", "知识条目不存在", "请刷新知识列表")
    return Response(status_code=204)


@router.post("/sync")
def sync(payload: SyncInput, session: Session = Depends(get_session)):
    return run_sync(payload.mode, session)


@router.get("/sync/logs")
def sync_logs(session: Session = Depends(get_session)):
    return list_sync_logs(session)


@router.delete("/data-tables/{table_name}")
def data_table_delete(
    table_name: str,
    confirm: bool = Query(False),
    session: Session = Depends(get_session),
):
    return delete_data_table(session, table_name, confirm)
