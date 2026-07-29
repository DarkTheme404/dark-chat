"""Видео-генерация — редирект на бесплатные генераторы"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class VideoRequest(BaseModel):
    prompt: str
    duration: int = 4


class VideoResponse(BaseModel):
    video_url: str
    redirect_url: str
    prompt: str
    generator: str
    status: str


GENERATORS = [
    {
        "name": "FlatAI",
        "url": "https://flatai.org/ai-video-generator/",
        "description": "Бесплатно, без регистрации, без водяного знака",
    },
    {
        "name": "Pixelbin",
        "url": "https://pixelbin.io/ai-video-generator",
        "description": "3 видео/мес бесплатно, до 1080p",
    },
    {
        "name": "Vider.ai",
        "url": "https://vider.ai",
        "description": "Бесплатно, image-to-video, с водяным знаком",
    },
]


@router.post("/generate", response_model=VideoResponse)
async def generate_video(request: VideoRequest):
    """Генерация видео — перенаправление на бесплатный генератор"""
    best = GENERATORS[0]

    prompt_encoded = request.prompt.replace(" ", "%20")
    redirect_url = f"{best['url']}?prompt={prompt_encoded}"

    return VideoResponse(
        video_url="",
        redirect_url=redirect_url,
        prompt=request.prompt,
        generator=best["name"],
        status=(
            f"🎬 Переходите на {best['name']} для генерации видео.\n"
            f"{best['description']}.\n\n"
            f"Промпт: {request.prompt}"
        ),
    )


@router.get("/generators")
async def list_generators():
    """Список доступных генераторов"""
    return {"generators": GENERATORS}
