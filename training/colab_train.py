"""
Dark Chat — Fine-tuning Qwen2.5 1.5B (LoRA)
Лимиты: 15 ГБ GPU, 12.7 ГБ RAM, 112 ГБ диск
Время: ~1-2 часа

ИНСТРУКЦИЯ:
1. colab.research.google.com
2. Runtime → Change runtime type → T4 GPU
3. Создай одну ячейку, вставь ВЕСЬ этот код
4. Shift+Enter
"""

# === Ячейка 1: Установка ===
!pip install -q transformers datasets trl peft accelerate

# === Ячейка 2: Весь код ===
import torch
import gc
import json
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer, DataCollatorForLanguageModeling
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset

# Проверка GPU
print(f"CUDA: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    props = torch.cuda.get_device_properties(0)
    print(f"GPU память: {props.total_memory / 1024**3:.1f} GB")

# Датасет
training_data = [
    {"instruction": "Привет", "output": "Привет! Чем могу помочь?"},
    {"instruction": "Кто ты?", "output": "Я Dark Chat — AI-ассистент. Могу отвечать на вопросы, генерировать код и помогать с задачами."},
    {"instruction": "Что ты умеешь?", "output": "Я умею: отвечать на вопросы, писать код на разных языках, объяснять сложные вещи простыми словами."},
    {"instruction": "Напиши hello world на Python", "output": "print('Hello, World!')"},
    {"instruction": "Напиши hello world на JavaScript", "output": "console.log('Hello, World!');"},
    {"instruction": "Напиши hello world на Go", "output": "package main\n\nimport \"fmt\"\n\nfunc main() {\n    fmt.Println(\"Hello, World!\")\n}"},
    {"instruction": "Что такое переменная?", "output": "Переменная — это именованная область памяти, в которой хранится значение."},
    {"instruction": "Объясни интернет простыми словами", "output": "Интернет — это глобальная сеть компьютеров, соединённых друг с другом."},
    {"instruction": "2+2=", "output": "4"},
    {"instruction": "Что такое AI?", "output": "AI — искусственный интеллект. Программы, которые могут учиться и принимать решения."},
    {"instruction": "Напиши функцию факториала на Python", "output": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)"},
    {"instruction": "Что такое массив?", "output": "Массив — структура данных, хранящая список элементов."},
    {"instruction": "Расскажи анекдот", "output": "Программист — это тот, кто решает проблему, о которой ты не знал."},
    {"instruction": "Как создать сайт?", "output": "HTML (структура), CSS (стили), JavaScript (логика). Фреймворки: React, Vue, Django."},
    {"instruction": "Что такое API?", "output": "API — интерфейс для общения программ друг с другом."},
    {"instruction": "Как работает Python?", "output": "Python — интерпретируемый язык. Код читается построчно, выполняется CPython."},
    {"instruction": "Что такое база данных?", "output": "База данных — хранилище информации. Примеры: SQLite, PostgreSQL, MySQL."},
    {"instruction": "Напиши сортировку пузырьком", "output": "def bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(0, n-i-1):\n            if arr[j] > arr[j+1]:\n                arr[j], arr[j+1] = arr[j+1], arr[j]\n    return arr"},
    {"instruction": "Что такое Git?", "output": "Git — система контроля версий."},
    {"instruction": "Объясни Docker", "output": "Docker — контейнеризация приложений."},
    {"instruction": "Что такое REST API?", "output": "REST API — стиль веб-API. Методы: GET, POST, PUT, DELETE."},
    {"instruction": "Напиши чтение файла на Python", "output": "with open('file.txt', 'r') as f:\n    content = f.read()"},
    {"instruction": "Что такое рекурсия?", "output": "Рекурсия — функция вызывает сама себя."},
    {"instruction": "Как создать API на Python?", "output": "from fastapi import FastAPI\napp = FastAPI()\n\n@app.get('/')\ndef home():\n    return {'msg': 'Hello'}"},
    {"instruction": "Что такое SQL?", "output": "SQL — язык запросов: SELECT, INSERT, UPDATE, DELETE."},
    {"instruction": "Напиши чат-бот на Python", "output": "while True:\n    msg = input('Ты: ')\n    if msg == 'привет':\n        print('Бот: Привет!')\n    elif msg == 'пока':\n        break"},
    {"instruction": "Что такое ООП?", "output": "ООП — объектно-ориентированное программирование."},
    {"instruction": "Объясни async/await", "output": "async/await — асинхронное программирование."},
    {"instruction": "Что такое middleware?", "output": "Middleware — промежуточный слой между запросом и ответом."},
    {"instruction": "Напиши HTTP-сервер", "output": "from http.server import HTTPServer, SimpleHTTPRequestHandler\nserver = HTTPServer(('localhost', 8000), SimpleHTTPRequestHandler)\nserver.serve_forever()"},
    {"instruction": "Что такое CI/CD?", "output": "CI — сборка, CD — деплой. GitHub Actions."},
]
print(f"Датасет: {len(training_data)} примеров")

# Загрузка модели
MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print(f"Загружаю {MODEL_NAME}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float16,
    low_cpu_mem_usage=True,
    trust_remote_code=True,
)

# LoRA
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=8,
    lora_alpha=16,
    lora_dropout=0.05,
    bias="none",
    target_modules=["q_proj", "v_proj"],
)

model = get_peft_model(model, lora_config)
model = model.to(device)

gc.collect()
torch.cuda.empty_cache()

print(f"Память: {torch.cuda.memory_allocated() / 1024**3:.1f} GB")
model.print_trainable_parameters()

# Подготовка данных
def format_example(example):
    return {"text": f"### Инструкция:\n{example['instruction']}\n\n### Ответ:\n{example['output']}"}

dataset = Dataset.from_list([format_example(d) for d in training_data])

def tokenize_function(examples):
    return tokenizer(examples["text"], truncation=True, max_length=256, padding="max_length")

tokenized = dataset.map(tokenize_function, batched=True, remove_columns=["text"])
split = tokenized.train_test_split(test_size=0.1)

print(f"Train: {len(split['train'])}, Eval: {len(split['test'])}")

# Обучение
training_args = TrainingArguments(
    output_dir="./darkchat-qwen-lora",
    num_train_epochs=3,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
    learning_rate=2e-4,
    weight_decay=0.01,
    warmup_steps=50,
    logging_steps=10,
    save_steps=200,
    fp16=True,
    optim="adamw_torch",
    report_to="none",
    eval_strategy="steps",
    eval_steps=50,
    save_total_limit=2,
    gradient_checkpointing=True,
    max_grad_norm=0.3,
    lr_scheduler_type="cosine",
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=split["train"],
    eval_dataset=split["test"],
    data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
)

print("=== Обучение ===")
trainer.train()
print("Готово!")

# Сохранение
trainer.save_model("./darkchat-qwen-lora")
tokenizer.save_pretrained("./darkchat-qwen-lora")
print("Модель сохранена!")

# Тест
model.eval()

def generate(prompt):
    inputs = tokenizer(f"### Инструкция:\n{prompt}\n\n### Ответ:\n", return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=150, temperature=0.7, do_sample=True)
    return tokenizer.decode(outputs[0], skip_special_tokens=True).split("### Ответ:\n")[-1]

print("\n=== Тест ===")
print("Q: Привет!")
print(f"A: {generate('Привет!')}")
print("\nQ: Напиши hello world на Python")
print(f"A: {generate('Напиши hello world на Python')}")
print("\nQ: Что такое API?")
print(f"A: {generate('Что такое API?')}")

# Скачивание
import shutil
from google.colab import files

shutil.make_archive("darkchat-qwen-lora", "zip", "./darkchat-qwen-lora")
files.download("darkchat-qwen-lora.zip")
print("Скачано!")
