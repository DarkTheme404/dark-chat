from fastapi import APIRouter
from pydantic import BaseModel
import httpx
import os
import random

router = APIRouter()

HF_TOKEN = os.getenv("HF_TOKEN", "")
API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"

# Заглушки для демо без API
DEMO_REPLIES = [
    "Я — Dark Chat, ваш AI-ассистент. Чем могу помочь?",
    "Интересный вопрос! Позвольте подумать... Вот мой ответ.",
    "Отличная тема! Вот что я думаю по этому поводу.",
    "Спасибо за вопрос. Вот краткий ответ на ваш запрос.",
]


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str
    model: str = "Mistral-7B-Instruct"


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Отправить сообщение в чат (Mistral 7B)"""

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
                        return ChatResponse(reply=result[0].get("generated_text", ""))
        except Exception:
            pass  # fallback на демо-ответ

    # Демо-ответ когда API недоступен
    reply = f"[Dark Chat Demo] {request.message}\n\nЭто демо-режим. Подключите HF_TOKEN для работы с реальной моделью Mistral 7B."
    return ChatResponse(reply=reply, model="demo")
