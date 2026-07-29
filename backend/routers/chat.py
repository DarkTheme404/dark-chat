"""Чат роутер с автообучением и авто-роутингом на генераторы"""
from fastapi import APIRouter
from pydantic import BaseModel
import httpx
import os
import uuid
import time
import re
import base64
import urllib.parse
import logging
from models import get_db, auto_collect_response, get_best_model

logger = logging.getLogger(__name__)
router = APIRouter()

OPENROUTER_TOKEN = os.getenv("OPENROUTER_TOKEN", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

FREE_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-nano-9b-v2:free",
]

FREE_CODE_MODELS = [
    "cohere/north-mini-code:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-nano-9b-v2:free",
]

# === Паттерны для определения намерения ===

IMAGE_KEYWORDS = [
    r"(?:сгенерируй|создай|нарисуй|покажи|сделай)\s+(?:фото|картинку|изображение|рисунок|иллюстрацию)",
    r"(?:фото|картинку|изображение|рисунок)\s+(?:кота|собаки|пейзажа|человека|горы|моря|космоса)",
    r"(?:generate|create|draw|make)\s+(?:an?\s+)?(?:image|picture|photo|illustration)",
    r"^(?:фото|картинка|изображение)\s+",
    r"(?:хочу|дай|покажи)\s+(?:фото|картинку|изображение)",
]

CODE_KEYWORDS = [
    r"(?:напиши|создай|сгенерируй|покажи)\s+(?:код|функцию|скрипт|программу|класс|модуль)",
    r"(?:код|функцию|скрипт|программу)\s+(?:на|для)\s+(?:python|javascript|typescript|java|go|rust|c\+\+|php|ruby|swift|kotlin)",
    r"(?:как\s+(?:написать|сделать|реализовать))\s+",
    r"(?:напиши|сделай)\s+(?:бота|парсер|爬虫|API|сервер|клиент)",
    r"(?:код|code)\s+",
    r"```",
]

VIDEO_KEYWORDS = [
    r"(?:сгенерируй|создай|сделай)\s+(?:видео|ролик|клип|анимацию)",
    r"(?:видео|ролик|клип|анимацию)\s+(?:про|из|с|о)\s+",
    r"(?:generate|create|make)\s+(?:a\s+)?(?:video|clip|animation)",
    r"(?:хочу|дай|покажи)\s+видео",
]

ANALYSIS_KEYWORDS = [
    r"проанализируй",
    r"(?:анализ|что\s+с\s+)(?:цена|курс|рынок|акции|биткоин|btc|eth|crypto)",
    r"(?:тренд|уровни|поддержк|сопротивл|сигнал|точк[ауи]\s+(?:входа|выхода))",
    r"(?:стоит\s+(?:покупать|продавать|входить))",
]


def detect_intent(message: str) -> str:
    """Определяет намерение пользователя по сообщению"""
    msg_lower = message.lower().strip()

    for pattern in IMAGE_KEYWORDS:
        if re.search(pattern, msg_lower):
            return "image"

    for pattern in CODE_KEYWORDS:
        if re.search(pattern, msg_lower):
            return "code"

    for pattern in VIDEO_KEYWORDS:
        if re.search(pattern, msg_lower):
            return "video"

    for pattern in ANALYSIS_KEYWORDS:
        if re.search(pattern, msg_lower):
            return "analysis"

    return "chat"


def extract_image_prompt(message: str) -> str:
    """Извлекает промпт для генерации изображения из сообщения"""
    # Убираем ключевые слова-маркеры
    cleaned = message
    for pattern in [
        r"(?:сгенерируй|создай|нарисуй|покажи|сделай)\s+",
        r"(?:фото|картинку|изображение|рисунок|иллюстрацию)\s+(?:кота|собаки|пейзажа|)?",
        r"(?:хочу|дай|покажи)\s+(?:фото|картинку|изображение)\s+",
    ]:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    cleaned = cleaned.strip()
    if len(cleaned) < 3:
        cleaned = message
    return cleaned


def extract_code_prompt(message: str) -> tuple[str, str]:
    """Извлекает промпт и язык программирования"""
    lang = "python"
    msg_lower = message.lower()

    lang_map = {
        "python": "python", "питон": "python", "пайтон": "python",
        "javascript": "javascript", "js": "javascript", "джаваскрипт": "javascript",
        "typescript": "typescript", "ts": "typescript",
        "java": "java", "джава": "java",
        "go": "go", "голанг": "go", "golang": "go",
        "rust": "rust", "раст": "rust",
        "c++": "c++", "c#": "c++", "си++": "c++",
        "php": "php", "пхп": "php",
        "ruby": "ruby", "руби": "ruby",
    }

    for key, val in lang_map.items():
        if key in msg_lower:
            lang = val
            break

    # Убираем ключевые слова
    cleaned = message
    for pattern in [
        r"(?:напиши|создай|сгенерируй|покажи)\s+(?:код|функцию|скрипт|программу|класс)?\s*",
        r"(?:на|для)\s+(?:python|javascript|typescript|java|go|rust|c\+\+|php|ruby)\s*",
    ]:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    cleaned = cleaned.strip()
    if len(cleaned) < 3:
        cleaned = message
    return cleaned, lang


def extract_video_prompt(message: str) -> str:
    """Извлекает промпт для видео"""
    cleaned = message
    for pattern in [
        r"(?:сгенерируй|создай|сделай)\s+(?:видео|ролик|клип|анимацию)\s+",
        r"(?:видео|ролик|клип)\s+(?:про|из|с|о)\s+",
        r"(?:хочу|дай|покажи)\s+видео\s+",
    ]:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    cleaned = cleaned.strip()
    if len(cleaned) < 3:
        cleaned = message
    return cleaned


async def call_ai(messages: list, model_list: list = None, max_tokens: int = 1024, temperature: float = 0.7) -> tuple[str, str]:
    """Вызывает AI модель, возвращает (reply, model_name)"""
    if not OPENROUTER_TOKEN:
        return "", "demo"

    models = model_list or FREE_MODELS
    headers = {
        "Authorization": f"Bearer {OPENROUTER_TOKEN}",
        "Content-Type": "application/json",
    }

    for model_id in models:
        try:
            payload = {
                "model": model_id,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(OPENROUTER_URL, json=payload, headers=headers)
                if response.status_code == 200:
                    result = response.json()
                    reply = result["choices"][0]["message"]["content"]
                    model_name = model_id.split("/")[-1].replace(":free", "")
                    return reply, model_name
        except Exception as e:
            logger.error("Model %s error: %s", model_id, e)
            continue
    return "", "demo"


async def generate_image(prompt: str) -> str:
    """Генерирует изображение через Pollinations.ai, возвращает base64 data URL"""
    try:
        encoded = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code == 200 and len(response.content) > 1000:
                b64 = base64.b64encode(response.content).decode()
                return f"data:image/png;base64,{b64}"
    except Exception as e:
        logger.error("Image gen error: %s", e)
    return ""


def extract_code(raw: str) -> str:
    """Извлекает код из markdown блоков"""
    match = re.search(r"```(?:\w+)?\s*\n(.*?)```", raw, re.DOTALL)
    if match:
        return match.group(1).strip()
    return raw.strip()


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str
    model: str = "AI"
    query_id: int = 0
    session_id: str = ""
    session_title: str = ""
    type: str = "text"
    image: str = ""
    code: str = ""
    language: str = ""
    redirect_url: str = ""
    generator: str = ""


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Универсальный чат: авто-роутинг на генераторы + AI ответ"""

    session_id = request.session_id
    is_new_session = False
    if not session_id:
        session_id = str(uuid.uuid4())[:8]
        is_new_session = True
        conn = get_db()
        cursor = conn.cursor()
        # Временное название — потом обновим через AI
        title = request.message[:30] + "..." if len(request.message) > 30 else request.message
        cursor.execute(
            "INSERT INTO sessions (session_id, title) VALUES (?, ?)",
            (session_id, title)
        )
        conn.commit()
        conn.close()

    intent = detect_intent(request.message)
    start_time = time.time()
    reply = ""
    model_name = "demo"
    resp_type = "text"
    image_data = ""
    code_data = ""
    lang_data = ""
    redirect_url = ""
    gen_name = ""

    if intent == "image":
        # Генерация изображения
        img_prompt = extract_image_prompt(request.message)
        reply = f"Генерирую изображение: {img_prompt}..."
        image_data = await generate_image(img_prompt)
        if image_data:
            reply = f"Вот изображение по запросу: {img_prompt}"
            resp_type = "image"
        else:
            reply = f"Не удалось сгенерировать изображение для: {img_prompt}. Попробуйте переформулировать."
        model_name = "Pollinations.ai"

    elif intent == "code":
        # Генерация кода
        code_prompt, lang = extract_code_prompt(request.message)
        messages = [
            {
                "role": "system",
                "content": (
                    f"Ты — профессиональный программист. Пиши код на {lang}.\n"
                    "Генерируй ТОЛЬКО код, без объяснений, без markdown обёрток.\n"
                    "Не пиши заголовков. Код должен быть рабочим с комментариями на русском."
                ),
            },
            {"role": "user", "content": code_prompt},
        ]
        raw_code, model_name = await call_ai(messages, FREE_CODE_MODELS, max_tokens=2048, temperature=0.3)
        if raw_code:
            code_data = extract_code(raw_code)
            reply = f"Вот код на {lang}:\n\n{code_data}"
            resp_type = "code"
            lang_data = lang
        else:
            reply = "Не удалось сгенерировать код. Попробуйте позже."

    elif intent == "video":
        # Видео-генерация (редирект)
        vid_prompt = extract_video_prompt(request.message)
        redirect_url = f"https://flatai.org/ai-video-generator/?prompt={urllib.parse.quote(vid_prompt)}"
        gen_name = "FlatAI"
        reply = (
            f"Для генерации видео перейдите на {gen_name}:\n"
            f"{redirect_url}\n\n"
            f"Промпт: {vid_prompt}\n"
            f"FlatAI — бесплатно, без регистрации, без водяного знака."
        )
        resp_type = "video"
        model_name = "FlatAI"

    elif intent == "analysis":
        # Торговый анализ
        messages = [
            {
                "role": "system",
                "content": (
                    "Ты — финансовый аналитик. Дай краткий анализ по запросу.\n"
                    "Укажи: тренд, уровни поддержки/сопротивления, рекомендацию.\n"
                    "Отвечай на русском, кратко и по делу."
                ),
            },
            {"role": "user", "content": request.message},
        ]
        reply, model_name = await call_ai(messages)
        if not reply:
            reply = "Не удалось выполнить анализ. Попробуйте позже."
        resp_type = "text"

    else:
        # Обычный чат — загружаем историю из БД
        messages = [
            {"role": "system", "content": "Ты — Dark Chat, умный AI-ассистент. Отвечай на русском языке кратко и по делу. Не используй markdown разметку. Ты помнишь всю предыдущую беседу в этой сессии."},
        ]

        # Загружаем историю из БД если есть session_id
        if session_id:
            try:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT user_message, bot_reply FROM queries WHERE session_id = ? ORDER BY created_at ASC LIMIT 20",
                    (session_id,)
                )
                for row in cursor.fetchall():
                    messages.append({"role": "user", "content": row[0]})
                    messages.append({"role": "assistant", "content": row[1]})
                conn.close()
            except Exception as e:
                logger.error("Failed to load history: %s", e)

        # Добавляем историю из фронтенда если есть
        for msg in request.history:
            messages.append(msg)

        messages.append({"role": "user", "content": request.message})

        reply, model_name = await call_ai(messages)
        if not reply:
            reply = f"[Dark Chat] {request.message}\n\nЭто демо-режим. Задай OPENROUTER_TOKEN для работы с AI."

    response_time_ms = int((time.time() - start_time) * 1000)

    query_id = auto_collect_response(
        user_message=request.message,
        bot_reply=reply,
        model_used=model_name,
        response_time_ms=response_time_ms,
        session_id=session_id,
    )

    # Автоназвание для новой сессии (короткое, по теме)
    final_title = ""
    if is_new_session:
        final_title = await _generate_session_title(request.message, reply)
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET title = ? WHERE session_id = ?",
                (final_title, session_id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Failed to update title: %s", e)

    return ChatResponse(
        reply=reply,
        model=model_name,
        query_id=query_id,
        session_id=session_id,
        session_title=final_title,
        type=resp_type,
        image=image_data,
        code=code_data,
        language=lang_data,
        redirect_url=redirect_url,
        generator=gen_name,
    )


async def _generate_session_title(user_msg: str, ai_reply: str) -> str:
    """Генерирует короткое название сессии (3-5 слов)"""
    msg = user_msg.strip()

    # Убираем стартовые слова
    cleaned = msg
    for prefix in ["помоги ", "объясни ", "расскажи ", "сгенерируй ", "создай ", "напиши ",
                    "нарисуй ", "покажи ", "сделай ", "проанализируй ", "что ", "как ",
                    "почему ", "можно ", "нужно ", "хочу ", "дай ", "вопрос: ", "задача: "]:
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break

    # Берём первые значимые слова
    words = cleaned.split()[:5]
    title = " ".join(words)
    if len(title) < 3:
        title = msg[:40]
    return title[:50]
