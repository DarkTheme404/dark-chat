"""Модели данных для системы обучения Dark Chat"""
import sqlite3
import os
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

    # Таблица запросов пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_message TEXT NOT NULL,
            bot_reply TEXT NOT NULL,
            model_used TEXT DEFAULT 'demo',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            source TEXT DEFAULT 'feedback',
            quality_score REAL DEFAULT 1.0,
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
            last_training TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Инициализируем метрики
    cursor.execute("SELECT COUNT(*) FROM training_metrics")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO training_metrics DEFAULT VALUES")

    conn.commit()
    conn.close()


# Модели Pydantic
class QueryCreate(BaseModel):
    user_message: str
    bot_reply: str
    model_used: str = "demo"


class FeedbackCreate(BaseModel):
    query_id: int
    rating: int  # 1-5
    comment: Optional[str] = None
    category: str = "general"


class TrainingPairCreate(BaseModel):
    input_text: str
    output_text: str
    source: str = "feedback"
    quality_score: float = 1.0


class TrainingMetrics(BaseModel):
    total_queries: int
    total_feedback: int
    avg_rating: float
    training_sessions: int
    last_training: Optional[str]
