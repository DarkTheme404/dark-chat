import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers import chat, code, image, video

load_dotenv()

app = FastAPI(
    title="Dark Chat",
    description="AI-powered chat with code, image, and video generation",
    version="1.0.0"
)

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(code.router, prefix="/api/code", tags=["Code"])
app.include_router(image.router, prefix="/api/image", tags=["Image"])
app.include_router(video.router, prefix="/api/video", tags=["Video"])


@app.get("/")
async def root():
    return {
        "name": "Dark Chat API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "chat": "/api/chat",
            "code": "/api/code",
            "image": "/api/image",
            "video": "/api/video",
        }
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
