# Ключевые решения

## AI модели
- **OpenRouter.ai** — выбран потому что Render Free блокирует DNS к huggingface.co
- **Бесплатные модели** — nemotron-nano-9b (быстрые), nemotron-550b (умные)
- **Параллельный вызов** — asyncio.wait(FIRST_COMPLETED) для скорости
- **asyncio.ensure_future** — обязателен для asyncio.wait (иначе ошибка)

## Бэкенд
- **SQLite** — выбран для simplicity, работает на Render Free
- **DB auto-recovery** — при повреждении удаляет и пересоздаёт
- **Глобальный exception handler** — FastAPI не падает на необработанных ошибках
- **ALTER TABLE миграции** — SQLite не поддерживает IF NOT EXISTS для столбцов

## Фронтенд
- **React + Vite** — быстрая сборка, простой деплой на Vercel
- **Cyberpunk стиль** — неон cyan/magenta, scanlines, neural canvas
- **Canvas анимация** — 40 узлов с connection lines, pointer-events: none
- **position: absolute** для canvas — position: fixed перекрывал UI

## Генерация контента
- **Pollinations.ai** — бесплатная генерация изображений, без токена
- **FlatAI redirect** — нет бесплатного API для видео, только redirect
- **Groq Whisper** — лучший бесплатный STT
- **Web Speech API** — TTS/STT прямо в браузере

## Deep Thinking
- **Тумблер с текстовой подписью** — пользователь не понимал emoji
- **Две модели параллельно** — первая быстрые, вторая умные
- **Разные timeout** — 20s для быстрых, 45s для умных

## Деплой
- **Render Free** — бесплатный хостинг, но спит после 15 мин
- **Vercel Free** — мгновенный деплой фронтенда
- **Автодеплой** — push в main → автоматический деплой
