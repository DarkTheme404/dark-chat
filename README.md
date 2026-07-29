# Dark Chat

AI-powered чат с генерацией кода, изображений и видео.

## Архитектура

```
┌─────────────────────────────────────────┐
│              Dark Chat                  │
├──────────┬──────────┬────────┬──────────┤
│  Чат     │  Код     │  Карты │  Видео   │
│ Mistral  │ DeepSeek │  SDXL  │ CogVideo │
│   7B     │ Coder    │        │ X-5b     │
└────┬─────┴────┬─────┴───┬────┴────┬─────┘
     │          │         │         │
     ▼          ▼         ▼         ▼
┌─────────────────────────────────────────┐
│          FastAPI Backend                │
│    Hugging Face Inference API           │
└─────────────────────────────────────────┘
```

## Быстрый старт

### 1. Клонировать
```bash
git clone https://github.com/DarkTheme404/dark-chat.git
cd dark-chat
```

### 2. Запустить через Docker
```bash
docker-compose up
```

### 3. Или запустить вручную

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### 4. Открыть
- Frontend: http://localhost:3000
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

## API Endpoints

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/chat/` | POST | Чат (Mistral 7B) |
| `/api/code/generate` | POST | Генерация кода (DeepSeek Coder) |
| `/api/image/generate` | POST | Генерация изображений (SDXL) |
| `/api/video/generate` | POST | Генерация видео (CogVideoX) |

## Переменные окружения

| Переменная | Описание | Обязательна |
|------------|----------|-------------|
| `HF_TOKEN` | Hugging Face токен | Нет (но увеличивает лимиты) |

## Технологии

- **Backend:** Python, FastAPI, httpx
- **Frontend:** React, TypeScript, Vite
- **AI Models:** Mistral 7B, DeepSeek Coder, SDXL, CogVideoX
- **API:** Hugging Face Inference API (бесплатно)

## Лицензия

MIT
