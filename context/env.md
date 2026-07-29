# Окружение и секреты

## Render (Бэкенд)
- **SERVICe:** dark-chat-api.onrender.com
- **PYTHON:** 3.12.11
- **DB_PATH:** darkchat.db (SQLite, в корне проекта)
- **OPENROUTER_TOKEN:** токен OpenRouter.ai (единственный секрет)
- **AutoDeploy:** true (автодеплой при push в main)

## Vercel (Фронтенд)
- **SERVICe:** dark-chat-puce.vercel.app
- **Framework:** Vite + React
- **Build:** `npm run build`
- **Output:** dist/
- **Config:** vercel.json (SPA rewrites)

## OpenRouter.ai
- **URL:** https://openrouter.ai/api/v1/chat/completions
- **Бесплатные модели:**
  - nvidia/nemotron-nano-9b-v2:free (быстрая)
  - google/gemma-4-31b-it:free (средняя)
  - nvidia/nemotron-3-super-120b-a12b:free (умная)
  - nvidia/nemotron-3-ultra-550b-a55b:free (самая умная)
  - cohere/north-mini-code:free (код)
- **Лимиты:** rate limit 429 иногда, 20s timeout

## Pollinations.ai
- **URL:** https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024&nologo=true
- **Токен:** не нужен
- **Лимиты:** иногда медленно (до 60с)

## FlatAI
- **URL:** https://flatai.org/ai-video-generator/
- **Тип:** redirect (нет API)
- **Регистрация:** не нужна

## Groq (Whisper STT)
- **URL:** https://api.groq.com/openai/v1/audio/transcriptions
- **Токен:** через OPENROUTER_TOKEN (OpenRouter проксирует)
- **Модель:** whisper-large-v3

## Локальная разработка
```bash
cd backend
pip install -r requirements.txt
export OPENROUTER_TOKEN="your_token_here"
python main.py
# → http://localhost:8000

cd frontend
npm install
npm run dev
# → http://localhost:3000
```

## Ключевые переменные окружения
| Переменная | Где | Описание |
|---|---|---|
| OPENROUTER_TOKEN | Render | Токен OpenRouter.ai |
| DB_PATH | Render | Путь к SQLite (по умолчанию darkchat.db) |
