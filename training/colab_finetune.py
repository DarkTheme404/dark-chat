"""
Dark Chat — Fine-tuning на Google Colab (бесплатный GPU)
=========================================================

Инструкция:
1. colab.research.google.com
2. File → Upload notebook → загрузи этот файл
3. Runtime → Change runtime type → T4 GPU
4. Runtime → Run All
5. Жди ~1-2 часа
"""

# === Ячейка 1: Установка ===
!pip install -q transformers datasets trl accelerate bitsandbytes

# === Ячейка 2: Генерация датасета ===
import json

# Базовый датасет для обучения
training_data = [
    {"instruction": "Привет", "output": "Привет! Чем могу помочь?"},
    {"instruction": "Кто ты?", "output": "Я Dark Chat — AI-ассистент. Могу отвечать на вопросы, генерировать код и помогать с задачами."},
    {"instruction": "Что ты умеешь?", "output": "Я умею: отвечать на вопросы, писать код на разных языках, объяснять сложные вещи простыми словами, помогать с математикой и логикой."},
    {"instruction": "Напиши hello world на Python", "output": "print('Hello, World!')"},
    {"instruction": "Напиши hello world на JavaScript", "output": "console.log('Hello, World!');"},
    {"instruction": "Напиши hello world на Go", "output": "package main\n\nimport \"fmt\"\n\nfunc main() {\n    fmt.Println(\"Hello, World!\")\n}"},
    {"instruction": "Что такое переменная?", "output": "Переменная — это именованная область памяти, в которой хранится значение. Например: x = 5, где x — имя переменной, а 5 — её значение."},
    {"instruction": "Объясни интернет простыми словами", "output": "Интернет — это глобальная сеть компьютеров, соединённых друг с другом. Через интернет можно обмениваться данными: отправлять сообщения, смотреть видео, работать."},
    {"instruction": "2+2=", "output": "4"},
    {"instruction": "Что такое AI?", "output": "AI (Artificial Intelligence) — искусственный интеллект. Это компьютерные программы, которые могут学习, рассуждать и принимать решения, как человек."},
    {"instruction": "Напиши функцию для нахождения факториала на Python", "output": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)"},
    {"instruction": "Что такое массив?", "output": "Массив — это структура данных, хранящая список элементов одного типа. Доступ к элементам по индексу: arr[0], arr[1] и т.д."},
    {"instruction": "Расскажи анекдот", "output": "Программист — это тот, кто решает проблему, о которой ты не знал, способом, который ты не понимаешь."},
    {"instruction": "Как создать сайт?", "output": "Для создания сайта нужно: 1) HTML — структура, 2) CSS — стили, 3) JavaScript — логика. Можно использовать готовые фреймворки: React, Vue, Django."},
    {"instruction": "Что такое API?", "output": "API (Application Programming Interface) — интерфейс программного взаимодействия. Это набор правил, по которым программы общаются друг с другом."},
    {"instruction": "Как работает Python?", "output": "Python — интерпретируемый язык. Код читается построчно, преобразуется в байт-код и выполняется виртуальной машиной Python (CPython)."},
    {"instruction": "Что такое база данных?", "output": "База данных — это организованное хранилище информации. Примеры: SQLite, PostgreSQL, MySQL. Данные хранятся в таблицах с строками и столбцами."},
    {"instruction": "Напиши сортировку пузырьком", "output": "def bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(0, n-i-1):\n            if arr[j] > arr[j+1]:\n                arr[j], arr[j+1] = arr[j+1], arr[j]\n    return arr"},
    {"instruction": "Что такое Git?", "output": "Git — система контроля версий. Позволяет отслеживать изменения в коде, работать в команде, откатывать ошибки. GitHub — облачный сервис для хранения Git-репозиториев."},
    {"instruction": "Объясни что такое Docker", "output": "Docker — платформа для контейнеризации. Упакует приложение со всеми зависимостями в контейнер, который работает одинаково на любом сервере."},
    {"instruction": "Что такое REST API?", "output": "REST API — архитектурный стиль для веб-API. Использует HTTP-методы: GET (получить), POST (создать), PUT (обновить), DELETE (удалить)."},
    {"instruction": "Напиши код для чтения файла на Python", "output": "with open('file.txt', 'r') as f:\n    content = f.read()\nprint(content)"},
    {"instruction": "Что такое рекурсия?", "output": "Рекурсия — функция, которая вызывает сама себя. Пример: factorial(n) = n * factorial(n-1). Должна иметь условие остановки."},
    {"instruction": "Как создать REST API на Python?", "output": "Используй Flask или FastAPI:\n\nfrom fastapi import FastAPI\napp = FastAPI()\n\n@app.get('/')\ndef home():\n    return {'message': 'Hello'}"},
    {"instruction": "Что такое SQL?", "output": "SQL — язык запросов для работы с базами данных. Основные команды: SELECT (выбрать), INSERT (добавить), UPDATE (обновить), DELETE (удалить)."},
    {"instruction": "Напиши простой чат-бот на Python", "output": "while True:\n    msg = input('Ты: ')\n    if msg == 'привет':\n        print('Бот: Привет!')\n    elif msg == 'пока':\n        print('Бот: Пока!')\n        break\n    else:\n        print('Бот: Не понял')"},
    {"instruction": "Что такоеoop?", "output": "ООП (Объектно-Ориентированное Программирование) — парадигма, где код организован вокруг объектов. Основные принципы: инкапсуляция, наследование, полиморфизм."},
    {"instruction": "Объясни async/await на Python", "output": "async/await — асинхронное программирование. async def создаёт асинхронную функцию, await ждёт результат. Позволяет выполнять несколько задач параллельно."},
    {"instruction": "Что такое middleware?", "output": "Middleware — промежуточный слой между запросом и ответом. Обрабатывает данные до передачи дальше: аутентификация, логирование, шифрование."},
    {"instruction": "Напиши простой HTTP-сервер на Python", "output": "from http.server import HTTPServer, SimpleHTTPRequestHandler\n\nserver = HTTPServer(('localhost', 8000), SimpleHTTPRequestHandler)\nprint('Сервер запущен')\nserver.serve_forever()"},
    {"instruction": "Что такое CI/CD?", "output": "CI (Continuous Integration) — автоматическая сборка и тестирование кода. CD (Continuous Deployment) — автоматический деплой. Инструменты: GitHub Actions, Jenkins, GitLab CI."},
]

# Сохраняем
with open('darkchat_dataset.json', 'w', encoding='utf-8') as f:
    json.dump(training_data, f, ensure_ascii=False, indent=2)

print(f"Создано {len(training_data)} примеров для обучения")

# === Ячейка 3: Загрузка модели ===
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer, DataCollatorForLanguageModeling
from datasets import Dataset

MODEL_NAME = "google/gemma-2-2b-it"

print(f"Загружаю {MODEL_NAME}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float16,
    device_map="auto",
)
print("Модель загружена!")

# === Ячейка 4: Подготовка данных ===
def format_example(example):
    return {"text": f"### Инструкция:\n{example['instruction']}\n\n### Ответ:\n{example['output']}"}

dataset = Dataset.from_list([format_example(d) for d in training_data])

def tokenize_function(examples):
    return tokenizer(examples["text"], truncation=True, max_length=512, padding="max_length")

tokenized = dataset.map(tokenize_function, batched=True, remove_columns=["text"])
split = tokenized.train_test_split(test_size=0.1)

print(f"Train: {len(split['train'])}, Eval: {len(split['test'])}")

# === Ячейка 5: Обучение ===
training_args = TrainingArguments(
    output_dir="./darkchat-finetuned",
    num_train_epochs=3,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
    learning_rate=2e-4,
    warmup_steps=50,
    logging_steps=10,
    save_steps=200,
    fp16=True,
    optim="adamw_8bit",
    report_to="none",
    eval_strategy="steps",
    eval_steps=50,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=split["train"],
    eval_dataset=split["test"],
    data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
)

print("Обучение...")
trainer.train()
print("Готово!")

# === Ячейка 6: Сохранение ===
trainer.save_model("./darkchat-gemma-finetuned")
tokenizer.save_pretrained("./darkchat-gemma-finetuned")
print("Модель сохранена!")

# === Ячейка 7: Тест ===
def generate(prompt):
    inputs = tokenizer(f"### Инструкция:\n{prompt}\n\n### Ответ:\n", return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=200, temperature=0.7)
    return tokenizer.decode(outputs[0], skip_special_tokens=True).split("### Ответ:\n")[-1]

print("\n=== Тест ===")
print("Q: Привет!")
print(f"A: {generate('Привет!')}")
print("\nQ: Напиши hello world на Python")
print(f"A: {generate('Напиши hello world на Python')}")
print("\nQ: Что такое API?")
print(f"A: {generate('Что такое API?')}")

# === Ячейка 8: Скачивание ===
from google.colab import files
import shutil

shutil.make_archive('darkchat-gemma-finetuned', 'zip', './darkchat-gemma-finetuned')
files.download('darkchat-gemma-finetuned.zip')
print("Скачано!")
