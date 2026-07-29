"""Чат роутер с сохранением запросов для обучения"""
from fastapi import APIRouter
from pydantic import BaseModel
import httpx
import os
from models import get_db

router = APIRouter()

HF_TOKEN = os.getenv("HF_TOKEN", "")
API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str
    model: str = "Mistral-7B-Instruct"
    query_id: int = 0  # ID запроса для оценки


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Отправить сообщение в чат (Mistral 7B)"""

    reply = ""
    model = "demo"

    # Пробуем HF API
    if HF_TOKEN:
        try:
            messages = [{"role": "system", "content": "Ты — Dark Chat, умный AI-ассистент. Отвечай на русском языке кратко и по делу."}]
            for msg in request.history:
                messages.append(msg)
            messages.append({"role": "user", "content": request.message})

            headers = {"Authorization": f"Bearer {HF_TOKEN}"}
            payload = {
                "inputs": messages,
                "parameters": {"max_new_tokens": 1024, "temperature": 0.7, "top_p": 0.9}
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(API_URL, json=payload, headers=headers)
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        reply = result[0].get("generated_text", "")
                        model = "Mistral-7B-Instruct"
        except Exception:
            pass

    # Демо-ответ
    if not reply:
        reply = f"[Dark Chat] {request.message}\n\nЭто демо-режим. Подключите HF_TOKEN для работы с Mistral 7B."

    # Сохраняем запрос в БД для обучения
    query_id = 0
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO queries (user_message, bot_reply, model_used) VALUES (?, ?, ?)",
            (request.message, reply, model)
        )
        query_id = cursor.lastrowid
        conn.commit()
        conn.close()
    except Exception:
        pass

    return ChatResponse(reply=reply, model=model, query_id=query_id)
