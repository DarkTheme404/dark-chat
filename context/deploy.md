# Как деплоить

## Автодеплой (основной способ)
1. `git push origin main`
2. Render автоматически деплоит бэкенд (1-3 мин)
3. Vercel автоматически деплоит фронтенд (30-60 сек)

## Ручной деплой бэкенда (Render)
1. Зайти на https://dashboard.render.com
2. Выбрать сервис dark-chat-api
3. Manual Deploy → Deploy latest commit
4. Ждать пока build завершится

## Ручной деплой фронтенда (Vercel)
1. Зайти на https://vercel.com/dashboard
2. Выбрать проект dark-chat-puce
3. Deployments → Redeploy
4. Ждать

## Локальная разработка

### Бэкенд
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
export OPENROUTER_TOKEN="ваш_токен"
python main.py
# → http://localhost:8000
# → http://localhost:8000/docs (Swagger)
```

### Фронтенд
```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### Фронтенд (продакшен сборка)
```bash
cd frontend
npm run build
# → dist/ (статические файлы)
```

## Тренировка модели
```bash
# В Colab:
# 1. Загрузить training/DarkChat_Train.ipynb
# 2. Runtime → Change runtime type → T4 GPU
# 3. Запустить все ячейки
# 4. Скачать модель из /content/final_model/
```

## Обновление зависимостей
```bash
# Бэкенд
pip install --upgrade -r requirements.txt
# Фронтенд
npm update
```

## Проверка здоровья
```bash
curl https://dark-chat-api.onrender.com/health
# → {"status":"ok","version":"3.2.0","db":"ok"}
```

## Логи
- **Render:** Dashboard → Logs
- **Vercel:** Dashboard → Deployments → функция → Logs
- **Локально:** stdout в терминале
