# Архитектура Dark Chat

## Общая схема

```
[Пользователь] → [Vercel (React)] → [Render (FastAPI)] → [OpenRouter.ai / Pollinations.ai]
                                          ↓
                                     [SQLite DB]
```

## Бэкенд (backend/)

### main.py
- Точка входа FastAPI
- Подключает все роутеры
- Глобальный обработчик ошибок (не даёт сервису упасть)
- Health check `/health` проверяет и БД

### models.py
- SQLite модели: sessions, queries, feedback, training_pairs, training_metrics, model_scores
- `get_db()` — подключение с автовосстановлением при повреждении
- `init_db()` — создаёт таблицы + ALTER TABLE миграции для существующих БД
- `auto_collect_response()` — автоматически сохраняет каждый ответ AI как training pair
- `_estimate_quality()` — оценивает качество ответа по длине и модели
- `export_training_data()` — экспорт в форматах Alpaca/ShareGPT

### routers/chat.py
- **Главная функция:** `POST /api/chat/`
- Авто-роутинг по намерению пользователя (regex):
  - `image` → Pollinations.ai
  - `code` → OpenRouter (code модели)
  - `video` → FlatAI redirect
  - `analysis` → OpenRouter (chat модели)
  - `chat` → OpenRouter (chat модели + история из БД)
- **Deep Thinking toggle:** параметр `thinking: bool`
  - `False` → быстрые модели (nemotron-nano-9b, gemma-4-31b), 512 tokens, 20s timeout
  - `True` → умные модели (nemotron-550b, nemotron-120b), 1024 tokens, 45s timeout
- Параллельный вызов 2 моделей через `asyncio.wait(FIRST_COMPLETED)`
- Автоназвание сессии (prefix-stripping алгоритм)
- История: последние 10 сообщений из БД

### routers/code.py
- `POST /api/code/generate` — генерация кода
- Параллельный вызов 2 моделей
- Авто-извлечение кода из markdown блоков

### routers/image.py
- `POST /api/image/generate` — Pollinations.ai (бесплатно, без токена)

### routers/video.py
- `POST /api/video/generate` — redirect на FlatAI (бесплатно, без signup)

### routers/upload.py
- `POST /api/files/upload` — загрузка файлов
- Изображения → AI vision анализ (Nemotron Ultra)
- Аудио → Groq Whisper STT → анализ
- Видео → ffmpeg извлечение кадров → AI vision
- Документы → AI текстовый анализ

### routers/feedback.py
- Оценка ответов (1-5 звёзд)
- Статистика, экспорт датасетов, скоринг моделей

### routers/sessions.py
- CRUD сессий (список, создание, чтение, удаление)
- Все операции обёрнуты в try/except

### routers/market.py
- `GET /api/market/{symbol}` — прокси Yahoo Finance (обход CORS)

## Фронтенд (frontend/src/)

### App.tsx
- Главный компонент с 7 вкладками: Чат, Код, Картинки, Видео, Озвучка, Трейдинг, Настройки
- **NeuralBackground** — Canvas анимация нейросети (40 узлов, связи, cyan свечение)
- **ThinkingToggle** — тумблер «Глубокое мышление» / «Быстрый режим»
- Cyberpunk UI: scanlines, neon glow, градиенты

### components/
- `Sidebar.tsx` — список сессий, удаление, даты
- `FeedbackForm.tsx` — форма оценки (звёзды + категория + комментарий)
- `AdminPanel.tsx` — статистика, отзывы, тренировка
- `index.tsx` — ChatMessage, CodeBlock, ImageBlock, VideoBlock

### services/api.ts
- API клиент с `fetchWithTimeout` (60s для чата)
- Методы: chat, generateCode, generateImage, generateVideo, uploadFile, getMarketData

### App.css
- Cyberpunk тема: --neon-cyan, --neon-magenta, --neon-purple
- Анимации: scanlineScroll, spin, messageIn, recordPulse
- Мобильная адаптация (768px, 480px breakpoints)
- Safe area для iPhone

## Тренировка (training/)
- `DarkChat_Train.ipynb` — ноутбук для Colab/Kaggle
- Qwen2.5-1.5B-Instruct + LoRA (r=8, alpha=16)
- Готов к запуску на免费 GPU

## Парсеры (не относятся к Dark Chat, но есть в репо)
- fuelprice.ru, gdebenz.ru, ishubenzin.ru — парсеры АЗС
- seed_top_cities.py — заполнение demo данными
- НЕ подключены к Dark Chat, это отдельный проект "Бензин рядом"
