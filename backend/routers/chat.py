"""Чат роутер с поддержкой сессий и сохранением для обучения"""
from fastapi import APIRouter
from pydantic import BaseModel
import httpx
import os
import uuid
import logging
from models import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

HF_TOKEN = os.getenv("HF_TOKEN", "")
API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str
    model: str = "Mistral-7B-Instruct"
    query_id: int = 0
    session_id: str = ""


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Отправить сообщение в чат (Mistral 7B)"""

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
    model = "demo"

    logger.info("HF_TOKEN set: %s", bool(HF_TOKEN))

    if HF_TOKEN:
        try:
            prompt = f"<s>[INST] Ты — Dark Chat, умный AI-ассистент. Отвечай на русском языке кратко и по делу.\n\n{request.message} [/INST]"

            headers = {"Authorization": f"Bearer {HF_TOKEN}"}
            payload = {
                "inputs": prompt,
                "parameters": {"max_new_tokens": 1024, "temperature": 0.7, "top_p": 0.9},
                "options": {"wait_for_model": True}
            }

            logger.info("Calling HF API: %s", API_URL)

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(API_URL, json=payload, headers=headers)
                logger.info("HF response status: %s", response.status_code)

                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        reply = result[0].get("generated_text", "")
                        model = "Mistral-7B-Instruct"
                        logger.info("Got reply from Mistral, length: %d", len(reply))
                else:
                    logger.error("HF API error %s: %s", response.status_code, response.text[:500])
        except Exception as e:
            logger.exception("HF API exception: %s", e)

    if not reply:
        reply = f"[Dark Chat] {request.message}\n\nЭто демо-режим. Подключите HF_TOKEN для работы с Mistral 7B."

    query_id = 0
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO queries (session_id, user_message, bot_reply, model_used) VALUES (?, ?, ?, ?)",
            (session_id, request.message, reply, model)
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

    return ChatResponse(reply=reply, model=model, query_id=query_id, session_id=session_id)
