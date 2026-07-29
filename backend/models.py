"""Модели данных для системы обучения Dark Chat v2 — автообучение"""
import sqlite3
import os
import uuid
import json
import hashlib
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

DB_PATH = os.getenv("DB_PATH", "darkchat.db")


def get_db():
    """Подключение к SQLite"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Инициализация базы данных"""
    conn = get_db()
    cursor = conn.cursor()

    # Таблица сессий чата
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            title TEXT DEFAULT 'Новый чат',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Таблица запросов (с привязкой к сессии)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            user_message TEXT NOT NULL,
            bot_reply TEXT NOT NULL,
            model_used TEXT DEFAULT 'demo',
            response_time_ms INTEGER DEFAULT 0,
            response_length INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
    """)

    # Таблица отзывов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id INTEGER,
            rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
            comment TEXT,
            category TEXT DEFAULT 'general',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (query_id) REFERENCES queries(id)
        )
    """)

    # Таблица обучения (пары вопрос-ответ для fine-tuning)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS training_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            input_text TEXT NOT NULL,
            output_text TEXT NOT NULL,
            source TEXT DEFAULT 'auto',
            model_used TEXT DEFAULT 'unknown',
            quality_score REAL DEFAULT 0.5,
            used_in_training BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Таблица метрик обучения
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS training_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_queries INTEGER DEFAULT 0,
            total_feedback INTEGER DEFAULT 0,
            avg_rating REAL DEFAULT 0.0,
            training_sessions INTEGER DEFAULT 0,
            total_training_pairs INTEGER DEFAULT 0,
            last_training TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Таблица моделей и их качества (для meta-router)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name TEXT NOT NULL,
            total_queries INTEGER DEFAULT 0,
            total_positive INTEGER DEFAULT 0,
            avg_rating REAL DEFAULT 0.0,
            avg_response_length REAL DEFAULT 0.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Таблица датасетов для обучения
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS training_datasets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_name TEXT NOT NULL,
            format TEXT DEFAULT 'alpaca',
            total_pairs INTEGER DEFAULT 0,
            file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used BOOLEAN DEFAULT 0
        )
    """)

    # Инициализируем метрики
    cursor.execute("SELECT COUNT(*) FROM training_metrics")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO training_metrics DEFAULT VALUES")

    # Создаём дефолтную сессию если нет ни одной
    cursor.execute("SELECT COUNT(*) FROM sessions")
    if cursor.fetchone()[0] == 0:
        default_id = str(uuid.uuid4())[:8]
        cursor.execute(
            "INSERT INTO sessions (session_id, title) VALUES (?, ?)",
            (default_id, "Первый чат")
        )

    # Миграции: добавляем колонки если их нет
    cursor.execute("PRAGMA table_info(queries)")
    cols = [row[1] for row in cursor.fetchall()]
    if "session_id" not in cols:
        cursor.execute("ALTER TABLE queries ADD COLUMN session_id TEXT DEFAULT ''")
    if "response_length" not in cols:
        cursor.execute("ALTER TABLE queries ADD COLUMN response_length INTEGER DEFAULT 0")
    if "response_time_ms" not in cols:
        cursor.execute("ALTER TABLE queries ADD COLUMN response_time_ms INTEGER DEFAULT 0")

    cursor.execute("PRAGMA table_info(training_pairs)")
    cols = [row[1] for row in cursor.fetchall()]
    if "model_used" not in cols:
        cursor.execute("ALTER TABLE training_pairs ADD COLUMN model_used TEXT DEFAULT 'unknown'")
    if "quality_score" not in cols:
        cursor.execute("ALTER TABLE training_pairs ADD COLUMN quality_score REAL DEFAULT 0.5")

    cursor.execute("PRAGMA table_info(training_metrics)")
    cols = [row[1] for row in cursor.fetchall()]
    if "total_training_pairs" not in cols:
        cursor.execute("ALTER TABLE training_metrics ADD COLUMN total_training_pairs INTEGER DEFAULT 0")

    conn.commit()
    conn.close()


# === Функции сбора данных ===

def auto_collect_response(user_message: str, bot_reply: str, model_used: str,
                          response_time_ms: int = 0, session_id: str = "") -> int:
    """Автоматически сохраняет ответ для обучения.

    Каждый ответ от AI автоматически попадает в training_pairs.
    Качество оценивается по метрикам:
    - Длина ответа (не слишком короткий, не слишком длинный)
    - Отсутствие ошибок API
    - Модель (более качественные модели = выше score)
    """
    conn = get_db()
    cursor = conn.cursor()

    # Сохраняем запрос
    cursor.execute(
        "INSERT INTO queries (session_id, user_message, bot_reply, model_used, response_time_ms, response_length) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, user_message, bot_reply, model_used, response_time_ms, len(bot_reply))
    )
    query_id = cursor.lastrowid

    # Оцениваем качество ответа автоматически
    quality = _estimate_quality(user_message, bot_reply, model_used)

    # Сохраняем как training pair (если качество достаточно высокое)
    if quality >= 0.3:
        cursor.execute(
            "INSERT INTO training_pairs (input_text, output_text, source, model_used, quality_score) "
            "VALUES (?, ?, 'auto', ?, ?)",
            (user_message, bot_reply, model_used, quality)
        )

    # Обновляем статистику модели
    _update_model_score(cursor, model_used, quality >= 0.6)

    # Обновляем метрики
    cursor.execute("""
        UPDATE training_metrics SET
            total_queries = total_queries + 1,
            total_training_pairs = (SELECT COUNT(*) FROM training_pairs),
            updated_at = CURRENT_TIMESTAMP
    """)

    conn.commit()
    conn.close()
    return query_id


def _estimate_quality(question: str, answer: str, model: str) -> float:
    """Автоматическая оценка качества ответа (0.0 - 1.0)"""
    score = 0.5  # базовая оценка

    # Длина ответа
    if len(answer) < 10:
        score -= 0.3  # слишком короткий
    elif len(answer) > 50:
        score += 0.1  # достаточно длинный
    if len(answer) > 200:
        score += 0.1  # подробный ответ

    # Качество модели
    model_quality = {
        "nemotron-3-ultra-550b-a55b": 0.9,
        "nemotron-3-super-120b-a12b": 0.8,
        "gemma-4-31b-it": 0.7,
        "north-mini-code": 0.7,
        "nemotron-nano-9b-v2": 0.6,
    }
    for key, quality in model_quality.items():
        if key in model:
            score += (quality - 0.5) * 0.3
            break

    # Наличие кода в ответе (для programming вопросов)
    code_indicators = ["def ", "function ", "class ", "import ", "const ", "let ", "var "]
    if any(ind in answer for ind in code_indicators):
        score += 0.1

    # Отсутствие ошибок
    error_indicators = ["error", "ошибка", "не удалось", "недоступен"]
    if any(err in answer.lower() for err in error_indicators):
        score -= 0.3

    return max(0.0, min(1.0, score))


def _update_model_score(cursor, model_name: str, is_positive: bool):
    """Обновляет статистику модели"""
    cursor.execute("SELECT id FROM model_scores WHERE model_name = ?", (model_name,))
    row = cursor.fetchone()

    if row:
        cursor.execute("""
            UPDATE model_scores SET
                total_queries = total_queries + 1,
                total_positive = total_positive + ?,
                avg_rating = (total_queries * avg_rating + ?) / (total_queries + 1),
                updated_at = CURRENT_TIMESTAMP
            WHERE model_name = ?
        """, (1 if is_positive else 0, 1.0 if is_positive else 0.0, model_name))
    else:
        cursor.execute(
            "INSERT INTO model_scores (model_name, total_queries, total_positive, avg_rating) VALUES (?, 1, ?, ?)",
            (model_name, 1 if is_positive else 0, 1.0 if is_positive else 0.0)
        )


def get_best_model() -> str:
    """Возвращает лучшую модель по статистике"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT model_name, avg_rating FROM model_scores WHERE total_queries >= 3 ORDER BY avg_rating DESC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return "nemotron-3-ultra-550b-a55b"  # дефолт


def export_training_data(format: str = "alpaca", min_quality: float = 0.5) -> list:
    """Экспорт данных для обучения в формате Alpaca/ShareGPT"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT input_text, output_text, quality_score, model_used
        FROM training_pairs
        WHERE quality_score >= ? AND used_in_training = 0
        ORDER BY quality_score DESC
        LIMIT 5000
    """, (min_quality,))

    pairs = []
    for row in cursor.fetchall():
        if format == "alpaca":
            pairs.append({
                "instruction": row[0],
                "input": "",
                "output": row[1],
                "quality": row[2],
                "model": row[3],
            })
        elif format == "sharegpt":
            pairs.append({
                "conversations": [
                    {"from": "human", "value": row[0]},
                    {"from": "gpt", "value": row[1]},
                ],
                "quality": row[2],
                "model": row[3],
            })

    conn.close()
    return pairs


def mark_as_trained():
    """Помечает все неиспользованные пары как использованные"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE training_pairs SET used_in_training = 1 WHERE used_in_training = 0")
    count = cursor.rowcount
    cursor.execute("""
        UPDATE training_metrics SET
            training_sessions = training_sessions + 1,
            last_training = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
    """)
    conn.commit()
    conn.close()
    return count


# Модели Pydantic
class SessionCreate(BaseModel):
    title: Optional[str] = "Новый чат"

class SessionUpdate(BaseModel):
    title: str

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    history: list[dict] = []

class FeedbackCreate(BaseModel):
    query_id: int
    rating: int
    comment: Optional[str] = None
    category: str = "general"

class TrainingPairCreate(BaseModel):
    input_text: str
    output_text: str
    source: str = "feedback"
    quality_score: float = 1.0
