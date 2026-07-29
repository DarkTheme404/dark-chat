"""Видео-генерация (демо-режим — нет бесплатного API)"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class VideoRequest(BaseModel):
    prompt: str
    duration: int = 4


class VideoResponse(BaseModel):
    video_url: str
    prompt: str
    model: str = "demo"
    status: str = ""


@router.post("/generate", response_model=VideoResponse)
async def generate_video(request: VideoRequest):
    """Видео-генерация (скоро)"""
    return VideoResponse(
        video_url="",
        prompt=request.prompt,
        model="demo",
        status="Видео-генерация в разработке. Скоро будет доступна через CogVideoX."
    )
