"""Генерация кода через OpenRouter"""
from fastapi import APIRouter
from pydantic import BaseModel
import httpx
import os
import re
import logging
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()

OPENROUTER_TOKEN = os.getenv("OPENROUTER_TOKEN", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
FREE_CODE_MODELS = [
    "nvidia/nemotron-nano-9b-v2:free",
    "cohere/north-mini-code:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
]

_http: httpx.AsyncClient | None = None


def _get_http() -> httpx.AsyncClient:
    global _http
    if _http is None or _http.is_closed:
        _http = httpx.AsyncClient(timeout=20.0, limits=httpx.Limits(max_connections=5))
    return _http


class CodeRequest(BaseModel):
    prompt: str
    language: str = "python"


class CodeResponse(BaseModel):
    code: str
    language: str
    model: str = "AI"


DEMO_CODES = {
    "python": '# {prompt}\ndef solution():\n    return [i * 2 for i in range(10)]\n\nprint(solution())\n',
    "javascript": '// {prompt}\nfunction solution() {{ return Array.from({{length: 10}}, (_, i) => i * 2); }}\nconsole.log(solution());\n',
}


def extract_code(raw: str, language: str) -> str:
    match = re.search(r"```(?:\w+)?\s*\n(.*?)```", raw, re.DOTALL)
    return match.group(1).strip() if match else raw.strip()


async def _call_one(model_id: str, messages: list, max_tokens: int, temperature: float) -> tuple[str, str] | None:
    try:
        payload = {"model": model_id, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
        http = _get_http()
        resp = await http.post(OPENROUTER_URL, json=payload,
                               headers={"Authorization": f"Bearer {OPENROUTER_TOKEN}", "Content-Type": "application/json"})
        if resp.status_code == 200:
            reply = resp.json()["choices"][0]["message"]["content"]
            return reply, model_id.split("/")[-1].replace(":free", "")
    except Exception:
        pass
    return None


@router.post("/generate", response_model=CodeResponse)
async def generate_code(request: CodeRequest):
    lang_name = {"python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
                 "go": "Go", "java": "Java", "c++": "C++", "rust": "Rust"}.get(request.language, request.language)

    if OPENROUTER_TOKEN:
        messages = [
            {"role": "system", "content": f"Пиши код на {lang_name}. Только код. Без markdown обёрток."},
            {"role": "user", "content": request.prompt},
        ]

        # Параллельно 2 модели
        tasks = [asyncio.ensure_future(_call_one(m, messages, 1024, 0.3)) for m in FREE_CODE_MODELS[:2]]
        done, _ = await asyncio.wait(tasks, timeout=20.0, return_when=asyncio.FIRST_COMPLETED)
        for t in done:
            result = t.result()
            if result:
                code = extract_code(result[0], request.language)
                return CodeResponse(code=code, language=request.language, model=result[1])

        # Третья модель
        result = await _call_one(FREE_CODE_MODELS[2], messages, 1024, 0.3) if len(FREE_CODE_MODELS) > 2 else None
        if result:
            code = extract_code(result[0], request.language)
            return CodeResponse(code=code, language=request.language, model=result[1])

    template = DEMO_CODES.get(request.language, DEMO_CODES["python"])
    return CodeResponse(code=template.format(prompt=request.prompt), language=request.language, model="demo")
