import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from routers import chat, code, image, video, feedback, sessions, upload, market
from models import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

try:
    init_db()
except Exception as e:
    logger.error("DB init failed: %s", e)

app = FastAPI(
    title="Dark Chat",
    description="AI-powered chat with self-learning.",
    version="3.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled: %s %s -> %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": str(exc)[:200]})


app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(code.router, prefix="/api/code", tags=["Code"])
app.include_router(image.router, prefix="/api/image", tags=["Image"])
app.include_router(video.router, prefix="/api/video", tags=["Video"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])
app.include_router(upload.router, prefix="/api/files", tags=["Upload"])
app.include_router(market.router, prefix="/api/market", tags=["Market"])


@app.get("/")
async def root():
    return {"name": "Dark Chat API", "version": "3.2.0", "status": "running"}


@app.get("/health")
async def health():
    try:
        from models import get_db
        conn = get_db()
        conn.execute("SELECT 1")
        conn.close()
        return {"status": "ok", "version": "3.2.0", "db": "ok"}
    except Exception as e:
        return {"status": "degraded", "version": "3.2.0", "db": str(e)[:100]}
