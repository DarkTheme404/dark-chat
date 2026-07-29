import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers import chat, code, image, video, feedback, sessions, upload, market
from models import init_db

load_dotenv()

# Инициализируем БД
init_db()

app = FastAPI(
    title="Dark Chat",
    description="AI-powered chat with code, image, and video generation. Self-learning system.",
    version="3.1.0"
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
app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(code.router, prefix="/api/code", tags=["Code"])
app.include_router(image.router, prefix="/api/image", tags=["Image"])
app.include_router(video.router, prefix="/api/video", tags=["Video"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback & Learning"])
app.include_router(upload.router, prefix="/api/files", tags=["File Upload & Analysis"])
app.include_router(market.router, prefix="/api/market", tags=["Market Data"])


@app.get("/")
async def root():
    return {
        "name": "Dark Chat API",
        "version": "3.0.0",
        "status": "running",
        "features": [
            "AI Chat (Mistral 7B)",
            "Code Generation (DeepSeek Coder)",
            "Image Generation (SDXL)",
            "Video Generation (CogVideoX)",
            "Self-Learning from Feedback",
            "Chat Sessions & History",
        ],
        "endpoints": {
            "sessions": "/api/sessions",
            "chat": "/api/chat",
            "code": "/api/code",
            "image": "/api/image",
            "video": "/api/video",
            "feedback": "/api/feedback",
            "docs": "/docs",
        }
    }


@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.1.0"}
