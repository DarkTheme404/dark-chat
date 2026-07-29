# Известные баги и ограничения

## Render Free
- **Спит после 15 мин** — холодный старт 20-30с
- **DNS blocking** — блокирует huggingface.co (поэтому OpenRouter, не HF)
- **1 GB RAM** — лимит на free tier
- **512 MB disk** — лимит на free tier

## OpenRouter.ai
- **429 rate limit** — бесплатные модели имеют лимиты
- **Иногда 500** — серверы OpenRouter падают
- **Медленные модели** — nemotron-550b может отвечать 20-40с

## SQLite
- **Нет concurrent writes** — одна запись за раз
- **WAL mode** — включён для параллельных чтений
- **Нет ALTER COLUMN** — миграции через ADD COLUMN + IGNORE

## Фронтенд
- **Canvas performance** — 40 узлов могут тормозить на слабых устройствах
- **Нет SSR** — SPA, SEO не видит контент
- **Нет стриминга** — ответ показывается целиком после генерации

## AI модели
- **Hallucinations** — модели могут выдумывать факты
- **Контекстное окно** — ограничено (8K-32K в зависимости от модели)
- **Русский язык** — модели лучше работают на английском

## Self-learning
- **Мало данных** — пока <100 training pairs
- **Нет валидации** — quality score автоматический, нет human-in-the-loop
- **Qwen2.5-1.5B** — модель слишком маленькая для сложных задач

## Исправленные баги (история)
1. ~~asyncio.wait падал с "coroutines is forbidden"~~ → ensure_future
2. ~~Canvas перекрывал весь UI~~ → position: absolute + z-index
3. ~~emoji toggle непонятен~~ → текстовая подпись
4. ~~DB падала при повреждении~~ → auto-recovery
5. ~~Health check не проверял БД~~ → SELECT 1 в health endpoint
