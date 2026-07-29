"""
Dark Chat — Fine-tuning на Kaggle TPU v5e-8
============================================

1. Kaggle → Code → New Notebook
2. Data → Add Data → загрузи darkchat_alpaca_dataset.json
3. Settings → Accelerator → TPU v5e-8
4. Скопируй ячейки ниже
5. Run All (~2-3 часа)
"""

# === Ячейка 1: Установка ===
# !pip install -q transformers datasets trl accelerate sentencepiece protobuf

# === Ячейка 2: Импорты ===
import json
import os
import torch
import torch_xla
import torch_xla.core.xla_model as xm
import torch_xla.distributed.xla_multiprocessing as xmp

from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)

# === Ячейка 3: Загрузка датасета ===
DATASET_PATH = "/kaggle/input/darkchat-dataset/darkchat_alpaca_dataset.json"

if not os.path.exists(DATASET_PATH):
    print("Датасет не найден, создаю пример...")
    sample_data = [
        {"instruction": "Привет", "input": "", "output": "Привет! Чем могу помочь?"},
        {"instruction": "Что ты умеешь?", "input": "", "output": "Я AI-ассистент. Могу отвечать на вопросы и генерировать код."},
    ]
    with open("sample_dataset.json", "w") as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)
    DATASET_PATH = "sample_dataset.json"

with open(DATASET_PATH, "r") as f:
    raw_data = json.load(f)

print(f"Загружено {len(raw_data)} примеров")

# === Ячейка 4: Загрузка модели ===
MODEL_NAME = "google/gemma-2-2b-it"

print(f"Загружаю {MODEL_NAME}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float32,  # TPU лучше работает с float32
)

# TPU device
device = xm.xla_device()
model = model.to(device)
print(f"Модель на устройстве: {device}")

# === Ячейка 5: Подготовка данных ===
def format_example(example):
    text = f"### Инструкция:\n{example['instruction']}\n\n### Ответ:\n{example['output']}"
    return {"text": text}

dataset = Dataset.from_list([format_example(d) for d in raw_data])

def tokenize_function(examples):
    return tokenizer(examples["text"], truncation=True, max_length=512, padding="max_length")

tokenized_dataset = dataset.map(tokenize_function, batched=True, remove_columns=["text"])
print(f"Токенизировано: {len(tokenized_dataset)} примеров")

# Разделяем на train/eval
split = tokenized_dataset.train_test_split(test_size=0.1)
train_dataset = split["train"]
eval_dataset = split["test"]
print(f"Train: {len(train_dataset)}, Eval: {len(eval_dataset)}")

# === Ячейка 6: Настройка обучения ===
training_args = TrainingArguments(
    output_dir="./darkchat-finetuned",
    num_train_epochs=3,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
    learning_rate=2e-4,
    weight_decay=0.01,
    warmup_steps=50,
    logging_steps=10,
    save_steps=200,
    fp32=True,  # TPU = float32
    optim="adamw_torch",
    report_to="none",
    save_total_limit=2,
    eval_strategy="steps",
    eval_steps=100,
    load_best_model_at_end=True,
)

data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    data_collator=data_collator,
)

# === Ячейка 7: Обучение ===
print("Начинаю обучение на TPU...")
trainer.train()
print("Обучение завершено!")

# === Ячейка 8: Сохранение ===
OUTPUT_DIR = "./darkchat-gemma-finetuned"
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"Модель сохранена в {OUTPUT_DIR}")

# === Ячейка 9: Тест ===
model.eval()

def generate(prompt):
    text = f"### Инструкция:\n{prompt}\n\n### Ответ:\n"
    inputs = tokenizer(text, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=200, temperature=0.7)
    return tokenizer.decode(outputs[0], skip_special_tokens=True).split("### Ответ:\n")[-1]

print("\n=== Тест ===")
print("Q: Привет!")
print(f"A: {generate('Привет!')}")
print("\nQ: Напиши hello world на Python")
print(f"A: {generate('Напиши hello world на Python')}")

print("\n=== Готово! ===")
print("Модель сохранена в Output → darkchat-finetuned")
