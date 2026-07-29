"""Загрузка файлов: фото, видео, аудио, документы с AI-анализом"""
from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
import httpx
import os
import base64
import json
import logging
import tempfile
import subprocess

logger = logging.getLogger(__name__)
router = APIRouter()

OPENROUTER_TOKEN = os.getenv("OPENROUTER_TOKEN", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

VISION_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "google/gemma-4-31b-it:free",
]


class AnalyzeResponse(BaseModel):
    reply: str
    file_type: str
    model: str = "AI"
    file_url: str = ""


@router.post("/upload", response_model=AnalyzeResponse)
async def upload_and_analyze(
    file: UploadFile = File(...),
    message: str = Form(""),
):
    """Загрузить файл и получить AI-анализ"""

    content = await file.read()
    filename = file.filename or "unknown"
    mime = file.content_type or ""

    # Определяем тип файла
    if mime.startswith("image/"):
        return await _analyze_image(content, filename, message)
    elif mime.startswith("audio/"):
        return await _analyze_audio(content, filename, message)
    elif mime.startswith("video/"):
        return await _analyze_video(content, filename, message)
    elif mime in ("application/pdf", "text/plain", "text/csv",
                   "application/json", "text/markdown",
                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
        return await _analyze_document(content, filename, mime, message)
    else:
        return AnalyzeResponse(
            reply=f"Файл {filename} ({mime}) загружен. Тип пока не поддерживается для анализа.",
            file_type="unknown",
        )


async def _analyze_image(content: bytes, filename: str, message: str) -> AnalyzeResponse:
    """Анализ изображения через vision модель"""
    b64 = base64.b64encode(content).decode()
    mime = "image/png" if filename.endswith(".png") else "image/jpeg"
    data_url = f"data:{mime};base64,{b64}"

    prompt = message or "Опиши подробно что изображено на этой картинке. Если есть текст — прочитай его."

    if OPENROUTER_TOKEN:
        messages = [
            {"role": "system", "content": (
                "Ты — AI-ассистент с vision. Анализируй изображения подробно на русском языке.\n"
                "Описывай: объекты, текст, цвета, композицию, настроение.\n"
                "Если просят перевести текст — переводи."
            )},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ]

        for model_id in VISION_MODELS:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        OPENROUTER_URL,
                        json={"model": model_id, "messages": messages, "max_tokens": 1024, "temperature": 0.7},
                        headers={"Authorization": f"Bearer {OPENROUTER_TOKEN}", "Content-Type": "application/json"},
                    )
                    if resp.status_code == 200:
                        result = resp.json()
                        reply = result["choices"][0]["message"]["content"]
                        model_name = model_id.split("/")[-1].replace(":free", "")
                        return AnalyzeResponse(reply=reply, file_type="image", model=model_name, file_url=data_url)
            except Exception as e:
                logger.error("Vision model %s error: %s", model_id, e)

    return AnalyzeResponse(
        reply=f"Изображение {filename} загружено ({len(content)//1024}KB). Добавьте OPENROUTER_TOKEN для AI-анализа.",
        file_type="image",
        file_url=data_url,
    )


async def _analyze_audio(content: bytes, filename: str, message: str) -> AnalyzeResponse:
    """Анализ аудио: STT + описание"""
    size_kb = len(content) // 1024

    # Пытаемся распознать речь через OpenAI Whisper (через OpenRouter или напрямую)
    transcript = ""
    if OPENROUTER_TOKEN:
        try:
            # Используем Free STT API
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Пробуем через Groq Whisper (бесплатно)
                files = {"file": (filename, content, "audio/mpeg")}
                data = {"model": "whisper-large-v3", "language": "ru"}
                resp = await client.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    files=files,
                    data=data,
                    headers={"Authorization": f"Bearer {OPENROUTER_TOKEN}"},
                )
                if resp.status_code == 200:
                    transcript = resp.json().get("text", "")
        except Exception as e:
            logger.error("STT error: %s", e)

    if not transcript:
        transcript = f"[Аудио файл {filename}, {size_kb}KB]"

    prompt = message or f"Прослушай аудио и ответь на вопросы по нему. Транскрипт: {transcript}"
    reply = transcript

    if OPENROUTER_TOKEN and transcript != f"[Аудио файл {filename}, {size_kb}KB]":
        messages = [
            {"role": "system", "content": "Ты — AI-ассистент. Проанализируй транскрипт аудио и ответь на вопрос."},
            {"role": "user", "content": f"Транскрипт аудио:\n{transcript}\n\nВопрос: {prompt}"},
        ]
        for model_id in VISION_MODELS:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        OPENROUTER_URL,
                        json={"model": model_id, "messages": messages, "max_tokens": 1024},
                        headers={"Authorization": f"Bearer {OPENROUTER_TOKEN}", "Content-Type": "application/json"},
                    )
                    if resp.status_code == 200:
                        result = resp.json()
                        reply = result["choices"][0]["message"]["content"]
                        model_name = model_id.split("/")[-1].replace(":free", "")
                        return AnalyzeResponse(reply=reply, file_type="audio", model=model_name)
            except Exception as e:
                logger.error("Audio analysis error: %s", e)

    return AnalyzeResponse(reply=reply, file_type="audio")


async def _analyze_video(content: bytes, filename: str, message: str) -> AnalyzeResponse:
    """Анализ видео: извлечение кадров + описание"""
    size_mb = len(content) / (1024 * 1024)

    # Сохраняем во временный файл, извлекаем кадр
    frame_b64 = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # Извлекаем первый кадр через ffmpeg
        frame_path = tmp_path + ".jpg"
        subprocess.run(
            ["ffmpeg", "-i", tmp_path, "-vframes", "1", "-q:v", "2", frame_path, "-y"],
            capture_output=True, timeout=10,
        )

        if os.path.exists(frame_path):
            with open(frame_path, "rb") as f:
                frame_b64 = base64.b64encode(f.read()).decode()
            os.remove(frame_path)
        os.remove(tmp_path)
    except Exception as e:
        logger.error("Frame extraction error: %s", e)

    prompt = message or "Проанализируй это видео. Опиши что происходит."

    if frame_b64 and OPENROUTER_TOKEN:
        data_url = f"data:image/jpeg;base64,{frame_b64}"
        messages = [
            {"role": "system", "content": "Ты — AI-ассистент. Проанализируй кадр из видео и опиши что происходит."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ]
        for model_id in VISION_MODELS:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        OPENROUTER_URL,
                        json={"model": model_id, "messages": messages, "max_tokens": 1024},
                        headers={"Authorization": f"Bearer {OPENROUTER_TOKEN}", "Content-Type": "application/json"},
                    )
                    if resp.status_code == 200:
                        result = resp.json()
                        reply = result["choices"][0]["message"]["content"]
                        model_name = model_id.split("/")[-1].replace(":free", "")
                        return AnalyzeResponse(reply=reply, file_type="video", model=model_name)
            except Exception as e:
                logger.error("Video analysis error: %s", e)

    return AnalyzeResponse(
        reply=f"Видео {filename} ({size_mb:.1f}MB) загружено. Кадр извлечён для анализа.",
        file_type="video",
    )


async def _analyze_document(content: bytes, filename: str, mime: str, message: str) -> AnalyzeResponse:
    """Анализ документа: текст + AI"""
    text = ""

    if mime == "text/plain" or mime == "text/markdown" or mime == "text/csv":
        text = content.decode("utf-8", errors="replace")[:8000]
    elif mime == "application/json":
        try:
            data = json.loads(content)
            text = json.dumps(data, ensure_ascii=False, indent=2)[:8000]
        except:
            text = content.decode("utf-8", errors="replace")[:8000]
    elif mime == "application/pdf":
        text = f"[PDF документ {filename}, {len(content)//1024}KB] Текстовое содержимое пока не извлечено."

    prompt = message or f"Проанализируй этот документ и кратко опиши его содержимое."
    reply = text

    if OPENROUTER_TOKEN and text and not text.startswith("["):
        messages = [
            {"role": "system", "content": "Ты — AI-ассистент. Проанализируй документ на русском языке."},
            {"role": "user", "content": f"Документ {filename}:\n\n{text[:4000]}\n\n{prompt}"},
        ]
        for model_id in VISION_MODELS:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        OPENROUTER_URL,
                        json={"model": model_id, "messages": messages, "max_tokens": 1024},
                        headers={"Authorization": f"Bearer {OPENROUTER_TOKEN}", "Content-Type": "application/json"},
                    )
                    if resp.status_code == 200:
                        result = resp.json()
                        reply = result["choices"][0]["message"]["content"]
                        model_name = model_id.split("/")[-1].replace(":free", "")
                        return AnalyzeResponse(reply=reply, file_type="document", model=model_name)
            except Exception as e:
                logger.error("Document analysis error: %s", e)

    return AnalyzeResponse(reply=reply, file_type="document")
