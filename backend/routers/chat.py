"""Чат роутер с поддержкой сессий и OpenRouter"""
from fastapi import APIRouter
from pydantic import BaseModel
import httpx
import os
import uuid
import logging
from models import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

OPENROUTER_TOKEN = os.getenv("OPENROUTER_TOKEN", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Бесплатные модели (ранжированы по качеству)
FREE_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-nano-9b-v2:free",
]


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str
    model: str = "AI"
    query_id: int = 0
    session_id: str = ""


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Отправить сообщение в чат (OpenRouter free models)"""

    session_id = request.session_id
    if not session_id:
        session_id = str(uuid.uuid4())[:8]
        conn = get_db()
        cursor = conn.cursor()
        title = request.message[:50] + "..." if len(request.message) > 50 else request.message
        cursor.execute(
            "INSERT INTO sessions (session_id, title) VALUES (?, ?)",
            (session_id, title)
        )
        conn.commit()
        conn.close()

    reply = ""
    model_name = "demo"

    logger.info("OPENROUTER_TOKEN set: %s", bool(OPENROUTER_TOKEN))

    if OPENROUTER_TOKEN:
        messages = [
            {"role": "system", "content": "Ты — Dark Chat, умный AI-ассистент. Отвечай на русском языке кратко и по делу. Не используй markdown разметку."},
        ]
        for msg in request.history:
            messages.append(msg)
        messages.append({"role": "user", "content": request.message})

        headers = {
            "Authorization": f"Bearer {OPENROUTER_TOKEN}",
            "Content-Type": "application/json",
        }

        for model_id in FREE_MODELS:
            try:
                payload = {
                    "model": model_id,
                    "messages": messages,
                    "max_tokens": 1024,
                    "temperature": 0.7,
                }

                logger.info("Trying model: %s", model_id)

                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(OPENROUTER_URL, json=payload, headers=headers)
                    logger.info("Response %s: %s", model_id, response.status_code)

                    if response.status_code == 200:
                        result = response.json()
                        reply = result["choices"][0]["message"]["content"]
                        model_name = model_id.split("/")[-1].replace(":free", "")
                        logger.info("Got reply from %s, length: %d", model_id, len(reply))
                        break
                    else:
                        logger.error("Model %s error: %s", model_id, response.text[:200])
            except Exception as e:
                logger.error("Model %s exception: %s", model_id, e)
                continue

    if not reply:
        reply = f"[Dark Chat] {request.message}\n\nЭто демо-режим. Задай OPENROUTER_TOKEN для работы с AI."

    query_id = 0
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO queries (session_id, user_message, bot_reply, model_used) VALUES (?, ?, ?, ?)",
            (session_id, request.message, reply, model_name)
        )
        query_id = cursor.lastrowid
        cursor.execute(
            "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
            (session_id,)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

    return ChatResponse(reply=reply, model=model_name, query_id=query_id, session_id=session_id)
