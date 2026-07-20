from sqlalchemy import text
from sqlalchemy.orm import Session


def conversation_exists(session: Session, conversation_id: str) -> bool:
    row = session.execute(
        text("SELECT id FROM conversations WHERE id = :id"),
        {"id": conversation_id},
    ).mappings().first()
    return row is not None


def delete_conversation_tree(session: Session, conversation_id: str) -> None:
    session.execute(
        text("DELETE FROM analysis_runs WHERE conversation_id = :conversation_id"),
        {"conversation_id": conversation_id},
    )
    session.execute(
        text("DELETE FROM messages WHERE conversation_id = :conversation_id"),
        {"conversation_id": conversation_id},
    )
    session.execute(text("DELETE FROM conversations WHERE id = :id"), {"id": conversation_id})


def clear_conversation_tree(session: Session) -> None:
    session.execute(text("DELETE FROM analysis_runs"))
    session.execute(text("DELETE FROM messages"))
    session.execute(text("DELETE FROM conversations"))
