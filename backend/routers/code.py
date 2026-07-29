from fastapi import APIRouter
from pydantic import BaseModel
import httpx
import os

router = APIRouter()

HF_TOKEN = os.getenv("HF_TOKEN", "")
API_URL = "https://api-inference.huggingface.co/models/deepseek-ai/deepseek-coder-6.7b-instruct"


class CodeRequest(BaseModel):
    prompt: str
    language: str = "python"


class CodeResponse(BaseModel):
    code: str
    language: str
    model: str = "DeepSeek-Coder-6.7B"


DEMO_CODES = {
    "python": '''# {prompt}
def solution():
    """Решение задачи"""
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
    "go": '''// {prompt}
package main

import "fmt"

func solution() []int {{
    result := make([]int, 10)
    for i := range result {{
        result[i] = i * 2
    }}
    return result
}}

func main() {{
    fmt.Println(solution())
}}
''',
}


@router.post("/generate", response_model=CodeResponse)
async def generate_code(request: CodeRequest):
    """Сгенерировать код по описанию"""

    # Пробуем HF API
    if HF_TOKEN:
        try:
            system_prompt = f"Ты — AI для генерации кода на {request.language}. Генерируй только код."
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.prompt}
            ]

            headers = {"Authorization": f"Bearer {HF_TOKEN}"}
            payload = {
                "inputs": messages,
                "parameters": {"max_new_tokens": 2048, "temperature": 0.3}
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(API_URL, json=payload, headers=headers)
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        code = result[0].get("generated_text", "")
                        return CodeResponse(code=code, language=request.language)
        except Exception:
            pass

    # Демо-код
    template = DEMO_CODES.get(request.language, DEMO_CODES["python"])
    code = template.format(prompt=request.prompt)
    return CodeResponse(code=code, language=request.language, model="demo")
