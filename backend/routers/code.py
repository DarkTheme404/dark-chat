from fastapi import APIRouter
from pydantic import BaseModel
import httpx
import os

router = APIRouter()

HF_TOKEN = os.getenv("HF_TOKEN", "")

# DeepSeek Coder через Hugging Face
API_URL = "https://api-inference.huggingface.co/models/deepseek-ai/deepseek-coder-6.7b-instruct"


class CodeRequest(BaseModel):
    prompt: str
    language: str = "python"


class CodeResponse(BaseModel):
    code: str
    language: str
    model: str = "DeepSeek-Coder-6.7B"


@router.post("/generate", response_model=CodeResponse)
async def generate_code(request: CodeRequest):
    """Сгенерировать код по описанию"""

    system_prompt = f"""Ты — Dark Chat Code, AI-ассистент для генерации кода.
Пользователь просит код на языке {request.language}.
Генерируй только код без объяснений. Если нужен комментарий, пиши на русском."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": request.prompt}
    ]

    headers = {}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    payload = {
        "inputs": messages,
        "parameters": {
            "max_new_tokens": 2048,
            "temperature": 0.3,
        }
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(API_URL, json=payload, headers=headers)

        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                code = result[0].get("generated_text", "")
                # Убираем системный промпт из ответа
                if "```" in code:
                    code = code.split("```")[1] if "```" in code else code
            else:
                code = str(result)
        else:
            # Fallback: генерируем простой код
            code = generate_fallback_code(request.prompt, request.language)

    return CodeResponse(code=code, language=request.language)


def generate_fallback_code(prompt: str, language: str) -> str:
    """Заглушка когда API недоступен"""
    if language == "python":
        return f'''# {prompt}
def solution():
    # TODO: Реализовать логику
    pass

if __name__ == "__main__":
    solution()
'''
    elif language == "javascript":
        return f'''// {prompt}
function solution() {{
    // TODO: Реализовать логику
}}

solution();
'''
    else:
        return f"// {prompt}\n// TODO: Реализовать"
