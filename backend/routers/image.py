from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import io
import os

router = APIRouter()

HF_TOKEN = os.getenv("HF_TOKEN", "")

# Stable Diffusion XL через Hugging Face
API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"


class ImageRequest(BaseModel):
    prompt: str
    negative_prompt: str = "ugly, blurry, low quality, distorted"
    width: int = 1024
    height: int = 1024


class ImageResponse(BaseModel):
    image_url: str
    prompt: str
    model: str = "Stable-Diffusion-XL"


@router.post("/generate")
async def generate_image(request: ImageRequest):
    """Сгенерировать изображение по описанию"""

    headers = {}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    payload = {
        "inputs": request.prompt,
        "parameters": {
            "negative_prompt": request.negative_prompt,
            "width": request.width,
            "height": request.height,
        }
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(API_URL, json=payload, headers=headers)

        if response.status_code == 200:
            # Возвращаем изображение как base64
            import base64
            image_data = response.content
            image_b64 = base64.b64encode(image_data).decode()
            return {
                "image": f"data:image/png;base64,{image_b64}",
                "prompt": request.prompt,
                "model": "Stable-Diffusion-XL"
            }
        else:
            # Fallback: генерируем заглушку
            return generate_placeholder(request.prompt)


def generate_placeholder(prompt: str) -> dict:
    """Генерирует SVG-заглушку когда API недоступен"""
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <rect width="512" height="512" fill="#1a1a2e"/>
  <text x="256" y="240" text-anchor="middle" fill="#7c7cff" font-size="24" font-family="Arial">Dark Chat</text>
  <text x="256" y="280" text-anchor="middle" fill="#888" font-size="16" font-family="Arial">{prompt[:50]}...</text>
  <text x="256" y="320" text-anchor="middle" fill="#555" font-size="14" font-family="Arial">API недоступно</text>
</svg>'''

    import base64
    svg_b64 = base64.b64encode(svg.encode()).decode()
    return {
        "image": f"data:image/svg+xml;base64,{svg_b64}",
        "prompt": prompt,
        "model": "placeholder"
    }
