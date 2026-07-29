"""Генерация изображений через Pollinations.ai (бесплатно, без токена)"""
from fastapi import APIRouter
from pydantic import BaseModel
import httpx
import base64
import urllib.parse
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class ImageRequest(BaseModel):
    prompt: str
    negative_prompt: str = "ugly, blurry, low quality"
    width: int = 1024
    height: int = 1024


@router.post("/generate")
async def generate_image(request: ImageRequest):
    """Сгенерировать изображение через Pollinations.ai (бесплатно)"""
    try:
        encoded_prompt = urllib.parse.quote(request.prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={request.width}&height={request.height}&nologo=true"

        logger.info("Generating image: %s", request.prompt[:50])

        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code == 200 and len(response.content) > 1000:
                image_b64 = base64.b64encode(response.content).decode()
                return {
                    "image": f"data:image/png;base64,{image_b64}",
                    "prompt": request.prompt,
                    "model": "Pollinations.ai"
                }
    except Exception as e:
        logger.error("Image generation error: %s", e)

    return {
        "image": "",
        "prompt": request.prompt,
        "model": "demo",
        "error": "Не удалось сгенерировать изображение. Попробуйте позже."
    }
