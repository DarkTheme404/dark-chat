from fastapi import APIRouter
from pydantic import BaseModel
import httpx
import os
import base64

router = APIRouter()

HF_TOKEN = os.getenv("HF_TOKEN", "")
API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"


class ImageRequest(BaseModel):
    prompt: str
    negative_prompt: str = "ugly, blurry, low quality"
    width: int = 1024
    height: int = 1024


def generate_svg_placeholder(prompt: str, color: str = "#7c7cff") -> str:
    """Генерирует SVG-картинку как заглушку"""
    short_prompt = prompt[:60] + "..." if len(prompt) > 60 else prompt
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a2e"/>
      <stop offset="100%" style="stop-color:#16213e"/>
    </linearGradient>
  </defs>
  <rect width="512" height="512" fill="url(#bg)" rx="16"/>
  <circle cx="400" cy="100" r="60" fill="{color}" opacity="0.3"/>
  <circle cx="120" cy="400" r="80" fill="#4CAF50" opacity="0.2"/>
  <text x="256" y="220" text-anchor="middle" fill="{color}" font-size="28" font-family="Arial" font-weight="bold">Dark Chat</text>
  <text x="256" y="270" text-anchor="middle" fill="#aaa" font-size="16" font-family="Arial">{short_prompt}</text>
  <text x="256" y="320" text-anchor="middle" fill="#555" font-size="14" font-family="Arial">Демо-режим • Подключите HF_TOKEN</text>
  <rect x="180" y="350" width="152" height="40" rx="20" fill="{color}" opacity="0.8"/>
  <text x="256" y="376" text-anchor="middle" fill="#fff" font-size="14" font-family="Arial">Сгенерировано</text>
</svg>'''
    return base64.b64encode(svg.encode()).decode()


@router.post("/generate")
async def generate_image(request: ImageRequest):
    """Сгенерировать изображение по описанию"""

    # Пробуем HF API
    if HF_TOKEN:
        try:
            headers = {"Authorization": f"Bearer {HF_TOKEN}"}
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
                    image_b64 = base64.b64encode(response.content).decode()
                    return {
                        "image": f"data:image/png;base64,{image_b64}",
                        "prompt": request.prompt,
                        "model": "Stable-Diffusion-XL"
                    }
        except Exception:
            pass

    # Демо-заглушка
    svg_b64 = generate_svg_placeholder(request.prompt)
    return {
        "image": f"data:image/svg+xml;base64,{svg_b64}",
        "prompt": request.prompt,
        "model": "demo"
    }
