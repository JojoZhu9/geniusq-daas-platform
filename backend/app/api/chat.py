from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db import get_session
from app.errors import ApiError
from app.schemas import ChatRequest
from app.services.conversation import (
    clear_conversations,
    create_conversation,
    delete_conversation,
    get_analysis,
    get_conversation_history,
    list_conversations,
    run_chat,
)
from app.services.feedback import save_analysis_feedback


router = APIRouter()


def _not_found(code: str, message: str, action: str) -> ApiError:
    return ApiError(404, code, message, action)


@router.post("/conversations", status_code=201)
def new_conversation(session: Session = Depends(get_session)):
    return create_conversation(session)


@router.get("/conversations")
def conversations(session: Session = Depends(get_session)):
    return list_conversations(session)


@router.delete("/conversations", status_code=204)
def conversations_clear(session: Session = Depends(get_session)):
    clear_conversations(session)
    return Response(status_code=204)


@router.get("/conversations/{conversation_id}")
def conversation_detail(conversation_id: str, session: Session = Depends(get_session)):
    conversation = get_conversation_history(session, conversation_id)
    if conversation is None:
        raise _not_found(
            "CONVERSATION_NOT_FOUND",
            "会话不存在或已失效",
            "请新建会话后重试",
        )
    return conversation


@router.delete("/conversations/{conversation_id}", status_code=204)
def conversation_delete(conversation_id: str, session: Session = Depends(get_session)):
    if not delete_conversation(session, conversation_id):
        raise _not_found(
            "CONVERSATION_NOT_FOUND",
            "会话不存在或已失效",
            "请刷新历史会话列表",
        )
    return Response(status_code=204)


@router.post("/chat")
def chat(payload: ChatRequest, session: Session = Depends(get_session)):
    response = run_chat(session, payload.conversation_id, payload.question.strip())
    if response is None:
        raise _not_found(
            "CONVERSATION_NOT_FOUND",
            "会话不存在或已失效",
            "请新建会话后重试",
        )
    return response


@router.get("/analysis/{analysis_id}")
def analysis(analysis_id: str, session: Session = Depends(get_session)):
    response = get_analysis(session, analysis_id)
    if response is None:
        raise _not_found(
            "ANALYSIS_NOT_FOUND",
            "分析任务不存在",
            "请重新提交问题",
        )
    return response


@router.post("/analysis/{analysis_id}/feedback", status_code=201)
def analysis_feedback(
    analysis_id: str, payload: dict, session: Session = Depends(get_session)
):
    return save_analysis_feedback(session, analysis_id, payload)
