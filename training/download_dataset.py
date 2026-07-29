#!/usr/bin/env python3
"""
Скачивание датасета из Dark Chat API для Kaggle
================================================

Использование:
  python download_dataset.py

Скачивает darkchat_alpaca_dataset.json → загрузи в Kaggle как Data
"""
import httpx
import json
import os

API_URL = os.getenv("DARKCHAT_API", "https://dark-chat-api.onrender.com")


def main():
    print(f"Скачиваю датасет из {API_URL}...")

    # Сначала заполняем данными (отправляем тестовые запросы)
    test_messages = [
        "Привет, кто ты?",
        "Что ты умеешь?",
        "Напиши hello world на Python",
        "Объясни что такое переменная",
        "Какой天气 сегодня?",
        "Расскажи анекдот",
        "Помоги с математикой: 2+2",
        "Что такое AI?",
        "Напиши код на JavaScript",
        "Объясни интернет простыми словами",
    ]

    print("Генерирую тестовые данные...")
    for msg in test_messages:
        try:
            resp = httpx.post(f"{API_URL}/api/chat/", json={"message": msg}, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                print(f"  [{data['model']}] {msg[:30]}...")
        except Exception as e:
            print(f"  Ошибка: {e}")

    # Скачиваем датасет
    print("\nСкачиваю датасет...")
    resp = httpx.get(f"{API_URL}/api/feedback/training/export?format=alpaca&min_quality=0.3", timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        pairs = data["pairs"]

        # Сохраняем
        output_file = "darkchat_alpaca_dataset.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(pairs, f, ensure_ascii=False, indent=2)

        print(f"Сохранено {len(pairs)} пар в {output_file}")
        print(f"\nСледующий шаг:")
        print(f"1. Зайди на kaggle.com")
        print(f"2. Code → New Notebook")
        print(f"3. Data → Add Data → загрузи {output_file}")
        print(f"4. Скопируй training/kaggle_finetune.py в ячейки")
        print(f"5. Settings → Accelerator → GPU T4 × 2")
        print(f"6. Run All")
    else:
        print(f"Ошибка: {resp.status_code} {resp.text}")


if __name__ == "__main__":
    main()
