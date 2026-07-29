"""API для управления сессиями чата"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
from models import get_db, init_db, SessionCreate, SessionUpdate

router = APIRouter()

# Инициализируем БД при старте
init_db()


@router.get("/")
async def list_sessions():
    """Получить список всех сессий"""
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
            "session_id": row[0],
            "title": row[1],
            "created_at": row[2],
            "updated_at": row[3],
            "message_count": row[4],
            "last_message": row[5],
        })

    conn.close()
    return {"sessions": sessions}


@router.post("/")
async def create_session(session: SessionCreate):
    """Создать новую сессию"""
    session_id = str(uuid.uuid4())[:8]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO sessions (session_id, title) VALUES (?, ?)",
        (session_id, session.title)
    )

    conn.commit()
    conn.close()

    return {
        "session_id": session_id,
        "title": session.title,
        "message": "Сессия создана"
    }


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Получить сессию с сообщениями"""
    conn = get_db()
    cursor = conn.cursor()

    # Получаем информацию о сессии
    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    session = cursor.fetchone()

    if not session:
        conn.close()
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    # Получаем сообщения сессии
    cursor.execute("""
        SELECT id, user_message, bot_reply, model_used, created_at
        FROM queries
        WHERE session_id = ?
        ORDER BY created_at ASC
    """, (session_id,))

    messages = []
    for row in cursor.fetchall():
        messages.append({
            "id": row[0],
            "user_message": row[1],
            "bot_reply": row[2],
            "model_used": row[3],
            "created_at": row[4],
        })

    conn.close()

    return {
        "session_id": session[1],
        "title": session[2],
        "created_at": session[3],
        "updated_at": session[4],
        "messages": messages,
    }


@router.put("/{session_id}")
async def update_session(session_id: str, update: SessionUpdate):
    """Обновить название сессии"""
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


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Удалить сессию и все её сообщения"""
    conn = get_db()
    cursor = conn.cursor()

    # Удаляем сообщения
    cursor.execute("DELETE FROM queries WHERE session_id = ?", (session_id,))

    # Удаляем сессию
    cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    conn.commit()
    conn.close()

    return {"status": "ok", "message": "Сессия удалена"}
