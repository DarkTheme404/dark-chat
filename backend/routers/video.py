from fastapi import APIRouter
from pydantic import BaseModel
import httpx
import os

router = APIRouter()

HF_TOKEN = os.getenv("HF_TOKEN", "")
API_URL = "https://api-inference.huggingface.co/models/THUDM/CogVideoX-5b"


class VideoRequest(BaseModel):
    prompt: str
    duration: int = 4


class VideoResponse(BaseModel):
    video_url: str
    prompt: str
    model: str = "CogVideoX-5b"
    status: str = "generated"


@router.post("/generate", response_model=VideoResponse)
async def generate_video(request: VideoRequest):
    """Сгенерировать видео по описанию"""

    # Пробуем HF API
    if HF_TOKEN:
        try:
            headers = {"Authorization": f"Bearer {HF_TOKEN}"}
            payload = {
                "inputs": request.prompt,
                "parameters": {"num_frames": request.duration * 8}
            }

            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(API_URL, json=payload, headers=headers)
                if response.status_code == 200:
                    import base64
                    video_b64 = base64.b64encode(response.content).decode()
                    return VideoResponse(
                        video_url=f"data:video/mp4;base64,{video_b64}",
                        prompt=request.prompt
                    )
        except Exception:
            pass

    # Демо-ответ
    return VideoResponse(
        video_url="",
        prompt=request.prompt,
        model="demo",
        status="Демо-режим. Видео генерируется через CogVideoX. Подключите HF_TOKEN для работы."
    )
