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
import asyncio
from models import get_db, auto_collect_response

logger = logging.getLogger(__name__)
router = APIRouter()

OPENROUTER_TOKEN = os.getenv("OPENROUTER_TOKEN", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Быстрые маленькие модели ПЕРВЫМИ
FREE_MODELS = [
    "nvidia/nemotron-nano-9b-v2:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
]

FREE_CODE_MODELS = [
    "nvidia/nemotron-nano-9b-v2:free",
    "cohere/north-mini-code:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
]

# Один HTTP-клиент на весь процесс (reuse connections)
_http: httpx.AsyncClient | None = None


def _get_http() -> httpx.AsyncClient:
    global _http
    if _http is None or _http.is_closed:
        _http = httpx.AsyncClient(timeout=20.0, limits=httpx.Limits(max_connections=10))
    return _http


# === Паттерны ===
IMAGE_KEYWORDS = [
    r"(?:сгенерируй|создай|нарисуй|покажи|сделай)\s+(?:фото|картинку|изображение|рисунок)",
    r"(?:фото|картинку|изображение)\s+(?:кота|собаки|пейзажа|человека)",
    r"(?:хочу|дай|покажи)\s+(?:фото|картинку|изображение)",
]

CODE_KEYWORDS = [
    r"(?:напиши|создай|сгенерируй)\s+(?:код|функцию|скрипт|программу|класс)",
    r"(?:код|функцию|скрипт)\s+(?:на|для)\s+(?:python|javascript|typescript|java|go|rust|c\+\+|php|ruby)",
    r"```",
]

VIDEO_KEYWORDS = [
    r"(?:сгенерируй|создай|сделай)\s+(?:видео|ролик|клип)",
    r"(?:видео|ролик)\s+(?:про|из|с|о)\s+",
]

ANALYSIS_KEYWORDS = [
    r"проанализируй",
    r"(?:анализ|что\s+с\s+)(?:цена|курс|рынок|акции|биткоин|btc|eth|crypto)",
]


def detect_intent(message: str) -> str:
    msg_lower = message.lower().strip()
    for kw, intent in [
        (IMAGE_KEYWORDS, "image"),
        (CODE_KEYWORDS, "code"),
        (VIDEO_KEYWORDS, "video"),
        (ANALYSIS_KEYWORDS, "analysis"),
    ]:
        for pattern in kw:
            if re.search(pattern, msg_lower):
                return intent
    return "chat"


def extract_image_prompt(message: str) -> str:
    cleaned = re.sub(
        r"(?:сгенерируй|создай|нарисуй|покажи|сделай)\s+(?:фото|картинку|изображение|рисунок)?\s*",
        "", message, flags=re.IGNORECASE
    ).strip()
    return cleaned if len(cleaned) > 3 else message


def extract_code_prompt(message: str) -> tuple[str, str]:
    lang = "python"
    msg_lower = message.lower()
    for key, val in {"python": "python", "javascript": "javascript", "js": "javascript",
                     "typescript": "typescript", "java": "java", "go": "go",
                     "rust": "rust", "c++": "c++", "php": "php", "ruby": "ruby"}.items():
        if key in msg_lower:
            lang = val
            break
    cleaned = re.sub(
        r"(?:напиши|создай|сгенерируй)\s+(?:код|функцию|скрипт|программу)?\s*(?:на|для)?\s*(?:python|javascript|typescript|java|go|rust|c\+\+|php|ruby)?\s*",
        "", message, flags=re.IGNORECASE
    ).strip()
    return (cleaned if len(cleaned) > 3 else message), lang


def extract_video_prompt(message: str) -> str:
    cleaned = re.sub(
        r"(?:сгенерируй|создай|сделай)\s+(?:видео|ролик|клип)\s+",
        "", message, flags=re.IGNORECASE
    ).strip()
    return cleaned if len(cleaned) > 3 else message


async def _call_one_model(model_id: str, messages: list, max_tokens: int, temperature: float, timeout: float = 20.0) -> tuple[str, str] | None:
    """Вызывает одну модель, возвращает (reply, model_name) или None"""
    try:
        payload = {
            "model": model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        http = _get_http()
        response = await http.post(
            OPENROUTER_URL, json=payload,
            headers={"Authorization": f"Bearer {OPENROUTER_TOKEN}", "Content-Type": "application/json"},
            timeout=timeout,
        )
        if response.status_code == 200:
            result = response.json()
            reply = result["choices"][0]["message"]["content"]
            name = model_id.split("/")[-1].replace(":free", "")
            return reply, name
    except Exception as e:
        logger.debug("Model %s failed: %s", model_id, e)
    return None


async def call_ai(messages: list, model_list: list = None, max_tokens: int = 512, temperature: float = 0.7, timeout: float = 20.0) -> tuple[str, str]:
    """Параллельно пробует 2 модели, возвращает первый ответ"""
    if not OPENROUTER_TOKEN:
        return "", "demo"

    models = model_list or FREE_MODELS

    # Пробуем первые 2 модели параллельно
    batch = models[:2]
    tasks = [asyncio.ensure_future(_call_one_model(m, messages, max_tokens, temperature, timeout)) for m in batch]
    done, _ = await asyncio.wait(tasks, timeout=timeout, return_when=asyncio.FIRST_COMPLETED)

    for task in done:
        result = task.result()
        if result:
            return result

    # Если первые 2 не ответили — третья
    if len(models) > 2:
        result = await _call_one_model(models[2], messages, max_tokens, temperature, timeout)
        if result:
            return result

    return "", "demo"


async def generate_image(prompt: str) -> str:
    try:
        encoded = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true"
        http = _get_http()
        response = await http.get(url, follow_redirects=True)
        if response.status_code == 200 and len(response.content) > 1000:
            b64 = base64.b64encode(response.content).decode()
            return f"data:image/png;base64,{b64}"
    except Exception as e:
        logger.error("Image gen error: %s", e)
    return ""


def extract_code(raw: str) -> str:
    match = re.search(r"```(?:\w+)?\s*\n(.*?)```", raw, re.DOTALL)
    return match.group(1).strip() if match else raw.strip()


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""
    history: list[dict] = []
    thinking: bool = False


# Умные модели для глубокого мышления
THINKING_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-31b-it:free",
]

THINKING_CODE_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "cohere/north-mini-code:free",
]


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
    session_id = request.session_id
    is_new_session = False
    if not session_id:
        session_id = str(uuid.uuid4())[:8]
        is_new_session = True
        try:
            conn = get_db()
            title = request.message[:30] + "..." if len(request.message) > 30 else request.message
            conn.execute("INSERT INTO sessions (session_id, title) VALUES (?, ?)", (session_id, title))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("create session: %s", e)

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

    thinking = getattr(request, 'thinking', False)
    chat_models = THINKING_MODELS if thinking else FREE_MODELS
    code_models = THINKING_CODE_MODELS if thinking else FREE_CODE_MODELS
    chat_tokens = 1024 if thinking else 512
    code_tokens = 2048 if thinking else 1024
    chat_timeout = 45.0 if thinking else 20.0

    if intent == "image":
        img_prompt = extract_image_prompt(request.message)
        reply = f"Генерирую: {img_prompt}..."
        try:
            image_data = await generate_image(img_prompt)
        except Exception as e:
            logger.error("Image: %s", e)
            image_data = ""
        reply = f"Изображение: {img_prompt}" if image_data else f"Не удалось: {img_prompt}"
        resp_type = "image" if image_data else "text"
        model_name = "Pollinations.ai"

    elif intent == "code":
        code_prompt, lang = extract_code_prompt(request.message)
        messages = [
            {"role": "system", "content": f"Пиши код на {lang}. Только код с комментариями на русском. Без markdown."},
            {"role": "user", "content": code_prompt},
        ]
        try:
            raw_code, model_name = await call_ai(messages, code_models, max_tokens=code_tokens, temperature=0.3, timeout=chat_timeout)
        except Exception as e:
            logger.error("Code: %s", e)
            raw_code = ""
        if raw_code:
            code_data = extract_code(raw_code)
            reply = f"Код на {lang}:\n\n{code_data}"
            resp_type = "code"
            lang_data = lang
        else:
            reply = "Не удалось сгенерировать код."

    elif intent == "video":
        vid_prompt = extract_video_prompt(request.message)
        redirect_url = f"https://flatai.org/ai-video-generator/?prompt={urllib.parse.quote(vid_prompt)}"
        gen_name = "FlatAI"
        reply = f"Видео генератор: {redirect_url}\nПромпт: {vid_prompt}\nБесплатно, без регистрации."
        resp_type = "video"
        model_name = "FlatAI"

    elif intent == "analysis":
        messages = [
            {"role": "system", "content": "Финансовый аналитик. Тренд, уровни, рекомендация. Кратко, на русском."},
            {"role": "user", "content": request.message},
        ]
        reply, model_name = await call_ai(messages, chat_models, max_tokens=chat_tokens, timeout=chat_timeout)
        if not reply:
            reply = "Не удалось выполнить анализ."
        resp_type = "text"

    else:
        messages = [
            {"role": "system", "content": "Ты — Dark Chat. Отвечай на русском кратко и по делу. Помнишь беседу."},
        ]
        if session_id:
            try:
                conn = get_db()
                rows = conn.execute(
                    "SELECT user_message, bot_reply FROM queries WHERE session_id = ? ORDER BY created_at DESC LIMIT 10",
                    (session_id,)
                ).fetchall()
                conn.close()
                for row in reversed(rows):
                    messages.insert(1, {"role": "user", "content": row[0]})
                    messages.insert(2, {"role": "assistant", "content": row[1]})
            except Exception as e:
                logger.error("History: %s", e)

        for msg in request.history[-6:]:
            messages.append(msg)
        messages.append({"role": "user", "content": request.message})
        reply, model_name = await call_ai(messages, chat_models, max_tokens=chat_tokens, timeout=chat_timeout)
        if not reply:
            reply = "Это демо-режим. Задай OPENROUTER_TOKEN."

    response_time_ms = int((time.time() - start_time) * 1000)

    try:
        query_id = auto_collect_response(
            user_message=request.message, bot_reply=reply,
            model_used=model_name, response_time_ms=response_time_ms, session_id=session_id,
        )
    except Exception:
        query_id = 0

    final_title = ""
    if is_new_session:
        final_title = _generate_session_title(request.message, reply)
        try:
            conn = get_db()
            conn.execute("UPDATE sessions SET title = ? WHERE session_id = ?", (final_title, session_id))
            conn.commit()
            conn.close()
        except Exception:
            pass

    return ChatResponse(
        reply=reply, model=model_name, query_id=query_id,
        session_id=session_id, session_title=final_title,
        type=resp_type, image=image_data, code=code_data,
        language=lang_data, redirect_url=redirect_url, generator=gen_name,
    )


def _generate_session_title(user_msg: str, ai_reply: str) -> str:
    msg = user_msg.strip()
    cleaned = msg.lower()
    for prefix in ["помоги мне ", "помоги ", "объясни ", "расскажи ", "сгенерируй ",
                    "создай ", "напиши ", "нарисуй ", "покажи ", "сделай ",
                    "проанализируй ", "что такое ", "как ", "почему ", "хочу ", "дай "]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    title = " ".join(cleaned.split()[:5])
    return title[:50] if len(title) >= 3 else msg[:40]
