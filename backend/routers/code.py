"""Генерация кода через OpenRouter (бесплатные модели)"""
from fastapi import APIRouter
from pydantic import BaseModel
import httpx
import os
import re
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

OPENROUTER_TOKEN = os.getenv("OPENROUTER_TOKEN", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
FREE_CODE_MODELS = [
    "cohere/north-mini-code:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-nano-9b-v2:free",
]


class CodeRequest(BaseModel):
    prompt: str
    language: str = "python"


class CodeResponse(BaseModel):
    code: str
    language: str
    model: str = "AI"


DEMO_CODES = {
    "python": '''# {prompt}
def solution():
    result = []
    for i in range(10):
        result.append(i * 2)
    return result

if __name__ == "__main__":
    print(solution())
''',
    "javascript": '''// {prompt}
function solution() {{
    const result = [];
    for (let i = 0; i < 10; i++) {{
        result.push(i * 2);
    }}
    return result;
}}
console.log(solution());
''',
}


def extract_code(raw: str, language: str) -> str:
    """Извлекает код из ответа модели (убирает markdown блоки)"""
    # Убираем ```python ... ``` обёртки
    pattern = r"```(?:\w+)?\s*\n(.*?)```"
    match = re.search(pattern, raw, re.DOTALL)
    if match:
        return match.group(1).strip()
    return raw.strip()


@router.post("/generate", response_model=CodeResponse)
async def generate_code(request: CodeRequest):
    """Сгенерировать код по описанию"""

    lang_map = {
        "python": "Python",
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "go": "Go",
        "java": "Java",
        "c++": "C++",
        "rust": "Rust",
    }
    lang_name = lang_map.get(request.language, request.language)

    if OPENROUTER_TOKEN:
        messages = [
            {
                "role": "system",
                "content": (
                    f"Ты — профессиональный программист. Пиши код на {lang_name}.\n"
                    "ПРАВИЛА:\n"
                    "- Генерируй ТОЛЬКО код, без объяснений, без markdown\n"
                    "- Не оборачивай в ``` блоки\n"
                    "- Не пиши заголовков типа 'Here is the code:'\n"
                    "- Просто начни с кода сразу\n"
                    "- Код должен быть рабочим и содержать комментарии на русском\n"
                ),
            },
            {"role": "user", "content": request.prompt},
        ]

        headers = {
            "Authorization": f"Bearer {OPENROUTER_TOKEN}",
            "Content-Type": "application/json",
        }

        for model_id in FREE_CODE_MODELS:
            try:
                payload = {
                    "model": model_id,
                    "messages": messages,
                    "max_tokens": 2048,
                    "temperature": 0.3,
                }

                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(OPENROUTER_URL, json=payload, headers=headers)
                    if response.status_code == 200:
                        result = response.json()
                        raw_code = result["choices"][0]["message"]["content"]
                        code = extract_code(raw_code, request.language)
                        model_name = model_id.split("/")[-1].replace(":free", "")
                        logger.info("Code generated: %d chars from %s", len(code), model_name)
                        return CodeResponse(code=code, language=request.language, model=model_name)
            except Exception as e:
                logger.error("Code model %s error: %s", model_id, e)
                continue

    template = DEMO_CODES.get(request.language, DEMO_CODES["python"])
    code = template.format(prompt=request.prompt)
    return CodeResponse(code=code, language=request.language, model="demo")
