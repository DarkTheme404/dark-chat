# Структура файлов

```
dark-chat/
├── README.md                    # Описание проекта
├── render.yaml                  # Конфигурация Render (deploy)
├── .gitignore
│
├── backend/
│   ├── main.py                  # FastAPI entry point (v3.2.0)
│   ├── models.py                # SQLite модели, DB init, training export
│   ├── requirements.txt         # Зависимости Python
│   └── routers/
│       ├── __init__.py          # Экспорт всех роутеров
│       ├── chat.py              # Чат с авто-роутингом + deep thinking
│       ├── code.py              # Генерация кода (параллельные модели)
│       ├── image.py             # Генерация изображений (Pollinations.ai)
│       ├── video.py             # Видео (redirect на FlatAI)
│       ├── upload.py            # Загрузка и анализ файлов
│       ├── feedback.py          # Оценки, статистика, экспорт
│       ├── sessions.py          # CRUD сессий
│       └── market.py            # Yahoo Finance прокси
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── vercel.json              # Конфигурация Vercel
│   ├── index.html
│   └── src/
│       ├── App.tsx              # Главный компонент + NeuralBackground + ThinkingToggle
│       ├── App.css              # Cyberpunk тема (1460 строк)
│       ├── main.tsx
│       ├── components/
│       │   ├── index.tsx        # ChatMessage, CodeBlock, ImageBlock, VideoBlock
│       │   ├── Sidebar.tsx      # Список сессий
│       │   ├── FeedbackForm.tsx # Форма оценки
│       │   └── AdminPanel.tsx   # Админ-панель
│       └── services/
│           └── api.ts           # API клиент (fetchWithTimeout)
│
├── training/
│   ├── DarkChat_Train.ipynb     # Colab notebook (Qwen2.5 1.5B + LoRA)
│   ├── gen_notebook.py          # Генератор .ipynb файлов
│   ├── kaggle_finetune.py       # Kaggle GPU скрипт
│   ├── kaggle_finetune_tpu.py   # Kaggle TPU скрипт
│   ├── download_dataset.py      # Скачивание данных из API
│   └── colab_train.py           # Colab скрипт
│
├── context/                     # ← ЭТА ПАПКА (контекст для AI)
│   ├── README.md
│   ├── architecture.md
│   ├── status.md
│   ├── done.md
│   ├── todo.md
│   ├── decisions.md
│   ├── files.md                 # ← вы здесь
│   ├── env.md
│   ├── bugs.md
│   └── deploy.md
│
└── .opencode/                   # Конфигурация opencode
```

## Ключевые файлы для понимания кода
1. `backend/routers/chat.py` — основная логика чата (авто-роутинг, модели, thinking)
2. `backend/models.py` — все БД модели и self-learning
3. `frontend/src/App.tsx` — весь UI, нейросеть, тумблер
4. `frontend/src/App.css` — cyberpunk тема
