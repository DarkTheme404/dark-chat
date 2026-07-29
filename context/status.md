# Текущее состояние проекта

## Статус: РАБОЧИЙ
- Бэкенд: v3.2.0, health OK, БД OK
- Фронтенд: cyberpunk UI, deployed
- Чат: работает (исправлен asyncio.wait bug)
- Генерация кода: работает
- Генерация изображений: работает (Pollinations.ai)
- Видео: redirect на FlatAI
- Трейдинг: TradingView + AI анализ
- Озвучка: Web Speech API TTS/STT
- Файлы: загрузка + анализ
- Feedback: оценка + экспорт
- Self-learning: авто-сбор training pairs

## Последние исправления
1. **asyncio.wait bug** — корутины не оборачивались в Task, чат падал с 500
2. **Canvas z-index** — нейросеть-фон перекрывала весь интерфейс
3. **Deep Thinking toggle** — подпись «Глубокое мышление» / «Быстрый режим»

## Версии файлов (последний коммит)
- main.py: v3.2.0, глобальный exception handler
- chat.py: parallel models, thinking toggle, asyncio.ensure_future
- code.py: parallel models, asyncio.ensure_future
- models.py: DB auto-recovery, try/except везде
- sessions.py: try/except на всех операциях
- App.tsx: NeuralBackground, ThinkingToggle, cyberpunk UI
- App.css: cyberpunk тема, анимации, responsive

## Known Issues
- Render Free: спит после 15 мин бездействия (холодный старт ~30с)
- OpenRouter: бесплатные модели иногда 429 (rate limit)
- Pollinations.ai: иногда медленная генерация (до 60с)
- Groq Whisper STT: требует OPENROUTER_TOKEN для AI-анализа транскрипта
- Vercel: SPA, нужен vercel.json для перенаправления всех путей на index.html
