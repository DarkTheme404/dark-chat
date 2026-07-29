from fastapi import APIRouter
from pydantic import BaseModel
import httpx
import os

router = APIRouter()

HF_TOKEN = os.getenv("HF_TOKEN", "")

# Mistral 7B через Hugging Face Inference API
API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str
    model: str = "Mistral-7B-Instruct"


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Отправить сообщение в чат (Mistral 7B)"""

    # Формируем историю для модели
    messages = [{"role": "system", "content": "Ты — Dark Chat, умный AI-ассистент. Отвечай на русском языке кратко и по делу."}]

    for msg in request.history:
        messages.append(msg)

    messages.append({"role": "user", "content": request.message})

    # Запрос к Hugging Face
    headers = {}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    payload = {
        "inputs": messages,
        "parameters": {
            "max_new_tokens": 1024,
            "temperature": 0.7,
            "top_p": 0.9,
        }
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(API_URL, json=payload, headers=headers)

        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                reply = result[0].get("generated_text", "Не удалось получить ответ")
            else:
                reply = str(result)
        else:
            # Fallback: возвращаем эхо если API недоступен
            reply = f"[Dark Chat] Получен запрос: {request.message}. API временно недоступен, попробуйте позже."

    return ChatResponse(reply=reply)
