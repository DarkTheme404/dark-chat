"""
Dark Chat — Fine-tuning на Kaggle (бесплатный GPU T4)
=====================================================

Инструкция:
1. Зайди на kaggle.com
2. Code → New Notebook
3. Скопируй этот скрипт в ячейки
4. Загрузи dataset (darkchat_alpaca_dataset.json) через Data → Add Data
5. Выбери GPU: Settings → Accelerator → GPU T4 (2x)
6. Run All

Обучение занимает ~1-2 часа на 1000 пар.
"""

# === Ячейка 1: Установка зависимостей ===
# !pip install -q unsloth transformers datasets trl accelerate bitsandbytes

# === Ячейка 2: Импорты ===
import json
import os
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from trl import SFTTrainer
import torch

# === Ячейка 3: Загрузка датасета ===
# Загрузи файл darkchat_alpaca_dataset.json через Add Data
DATASET_PATH = "/kaggle/input/darkchat-dataset/darkchat_alpaca_dataset.json"

# Если файл не найден — используем пример
if not os.path.exists(DATASET_PATH):
    print("Датасет не найден, создаю пример...")
    sample_data = [
        {"instruction": "Привет", "input": "", "output": "Привет! Чем могу помочь?"},
        {"instruction": "Что ты умеешь?", "input": "", "output": "Я AI-ассистент. Могу отвечать на вопросы, генерировать код и помогать с задачами."},
    ]
    with open("sample_dataset.json", "w") as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)
    DATASET_PATH = "sample_dataset.json"

with open(DATASET_PATH, "r") as f:
    raw_data = json.load(f)

print(f"Загружено {len(raw_data)} примеров")

# Конвертируем в Alpaca формат
def format_example(example):
    if "instruction" in example:
        text = f"### Инструкция:\n{example['instruction']}\n\n### Ответ:\n{example['output']}"
    elif "conversations" in example:
        text = f"### Инструкция:\n{example['conversations'][0]['value']}\n\n### Ответ:\n{example['conversations'][1]['value']}"
    else:
        text = f"### Инструкция:\n{example.get('input', '')}\n\n### Ответ:\n{example.get('output', '')}"
    return {"text": text}

dataset = Dataset.from_list([format_example(d) for d in raw_data])
print(f"Датасет: {len(dataset)} примеров")
print(f"Пример:\n{dataset[0]['text'][:200]}...")

# === Ячейка 4: Загрузка модели ===
MODEL_NAME = "unsloth/Mistral-7B-Instruct-v0.3-bnb-4bit"

print(f"Загружаю {MODEL_NAME}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float16,
    device_map="auto",
    load_in_4bit=True,
)
tokenizer.pad_token = tokenizer.eos_token

print("Модель загружена!")

# === Ячейка 5: Настройка обучения ===
training_args = TrainingArguments(
    output_dir="./darkchat-finetuned",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    weight_decay=0.01,
    warmup_steps=100,
    logging_steps=10,
    save_steps=200,
    fp16=True,
    optim="adamw_8bit",
    report_to="none",
    save_total_limit=2,
)

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    args=training_args,
    max_seq_length=2048,
    packing=True,
)

# === Ячейка 6: Обучение ===
print("Начинаю обучение...")
trainer.train()
print("Обучение завершено!")

# === Ячейка 7: Сохранение модели ===
OUTPUT_DIR = "./darkchat-mistral-finetuned"
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"Модель сохранена в {OUTPUT_DIR}")

# === Ячейка 8: Тест ===
def generate(prompt):
    text = f"### Инструкция:\n{prompt}\n\n### Ответ:\n"
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    outputs = model.generate(**inputs, max_new_tokens=200, temperature=0.7)
    return tokenizer.decode(outputs[0], skip_special_tokens=True).split("### Ответ:\n")[-1]

# Тест
print("\n=== Тест ===")
print("Q: Привет!")
print(f"A: {generate('Привет!')}")
print("\nQ: Напиши hello world на Python")
print(f"A: {generate('Напиши hello world на Python')}")

# === Ячейка 9: Загрузка на HuggingFace (опционально) ===
# from huggingface_hub import HfApi
# api = HfApi()
# api.upload_folder(folder_path=OUTPUT_DIR, repo_id="твой_ник/darkchat-mistral", repo_type="model")
# print("Модель загружена на HuggingFace!")
