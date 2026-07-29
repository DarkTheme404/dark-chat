from fastapi import APIRouter
from pydantic import BaseModel
import httpx
import os

router = APIRouter()

HF_TOKEN = os.getenv("HF_TOKEN", "")

# CogVideoX через Hugging Face
API_URL = "https://api-inference.huggingface.co/models/THUDM/CogVideoX-5b"


class VideoRequest(BaseModel):
    prompt: str
    duration: int = 4  # секунды


class VideoResponse(BaseModel):
    video_url: str
    prompt: str
    model: str = "CogVideoX-5b"
    status: str = "generated"


@router.post("/generate", response_model=VideoResponse)
async def generate_video(request: VideoRequest):
    """Сгенерировать видео по описанию"""

    headers = {}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    payload = {
        "inputs": request.prompt,
        "parameters": {
            "num_frames": request.duration * 8,  # 8 fps
        }
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(API_URL, json=payload, headers=headers)

        if response.status_code == 200:
            # Возвращаем видео как base64
            import base64
            video_data = response.content
            video_b64 = base64.b64encode(video_data).decode()
            return VideoResponse(
                video_url=f"data:video/mp4;base64,{video_b64}",
                prompt=request.prompt,
                model="CogVideoX-5b"
            )
        else:
            # Fallback: сообщение что API недоступно
            return VideoResponse(
                video_url="",
                prompt=request.prompt,
                model="placeholder",
                status="API недоступно. Попробуйте позже."
            )
