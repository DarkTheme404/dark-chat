"""API для управления сессиями чата"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
import logging
from models import get_db, init_db, SessionCreate, SessionUpdate

logger = logging.getLogger(__name__)
router = APIRouter()

init_db()


@router.get("/")
async def list_sessions():
    """Получить список всех сессий"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT s.session_id, s.title, s.created_at, s.updated_at,
                   COUNT(q.id) as message_count,
                   MAX(q.created_at) as last_message
            FROM sessions s
            LEFT JOIN queries q ON s.session_id = q.session_id
            GROUP BY s.session_id
            ORDER BY s.updated_at DESC
        """)

        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                "session_id": row["session_id"],
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "message_count": row["message_count"],
                "last_message": row["last_message"],
            })

        conn.close()
        return {"sessions": sessions}
    except Exception as e:
        logger.error("list_sessions error: %s", e)
        init_db()
        return {"sessions": []}


@router.post("/")
async def create_session(session: SessionCreate):
    """Создать новую сессию"""
    try:
        session_id = str(uuid.uuid4())[:8]
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (session_id, title) VALUES (?, ?)",
            (session_id, session.title)
        )
        conn.commit()
        conn.close()
        return {"session_id": session_id, "title": session.title, "message": "Сессия создана"}
    except Exception as e:
        logger.error("create_session error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Получить сессию с сообщениями"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        session = cursor.fetchone()

        if not session:
            conn.close()
            raise HTTPException(status_code=404, detail="Сессия не найдена")

        cursor.execute("""
            SELECT id, user_message, bot_reply, model_used, created_at
            FROM queries
            WHERE session_id = ?
            ORDER BY created_at ASC
        """, (session_id,))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                "id": row["id"],
                "user_message": row["user_message"],
                "bot_reply": row["bot_reply"],
                "model_used": row["model_used"],
                "created_at": row["created_at"],
            })

        conn.close()
        return {
            "session_id": session["session_id"],
            "title": session["title"],
            "created_at": session["created_at"],
            "updated_at": session["updated_at"],
            "messages": messages,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_session error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{session_id}")
async def update_session(session_id: str, update: SessionUpdate):
    """Обновить название сессии"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
            (update.title, session_id)
        )
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Сессия не найдена")
        conn.commit()
        conn.close()
        return {"status": "ok", "message": "Сессия обновлена"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_session error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Удалить сессию и все её сообщения"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM queries WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Сессия не найдена")
        conn.commit()
        conn.close()
        return {"status": "ok", "message": "Сессия удалена"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_session error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
