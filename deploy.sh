#!/bin/bash
# Деплой Dark Chat: бэкенд (Render) + фронтенд (Vercel)
#
# Порядок:
# 1. Залей код на GitHub
# 2. Задеплой бэкенд на Render
# 3. Задеплой фронтенд на Vercel
# 4. Пропиши URL бэкенда в Vercel env: VITE_API_URL=https://dark-chat-api.onrender.com

echo "=== Dark Chat Deploy ==="
echo ""
echo "Бэкенд (Render):"
echo "  1. render.com → New → Blueprint → выбери репо"
echo "  2. Задай секрет: HF_TOKEN=твой_токен"
echo "  3. URL будет: https://dark-chat-api.onrender.com"
echo ""
echo "Фронтенд (Vercel):"
echo "  1. vercel.com → Import → выбери репо"
echo "  2. Root Directory: frontend"
echo "  3. Env: VITE_API_URL=https://dark-chat-api.onrender.com"
echo "  4. URL будет: https://dark-chat.vercel.app"
echo ""
echo "После деплоя фронтенда — обнови CORS в backend/main.py:"
echo "  allow_origins=[\"https://dark-chat.vercel.app\"]"
