"""API для отзывов и обучения Dark Chat"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from models import get_db, init_db, FeedbackCreate, TrainingPairCreate, TrainingMetrics

router = APIRouter()

# Инициализируем БД при старте
init_db()


@router.post("/submit")
async def submit_feedback(feedback: FeedbackCreate):
    """Отправить отзыв на ответ бота"""
    conn = get_db()
    cursor = conn.cursor()

    # Проверяем существование query
    cursor.execute("SELECT id FROM queries WHERE id = ?", (feedback.query_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Запрос не найден")

    # Сохраняем отзыв
    cursor.execute(
        "INSERT INTO feedback (query_id, rating, comment, category) VALUES (?, ?, ?, ?)",
        (feedback.query_id, feedback.rating, feedback.comment, feedback.category)
    )
    feedback_id = cursor.lastrowid

    # Обновляем метрики
    cursor.execute("""
        UPDATE training_metrics SET
            total_feedback = total_feedback + 1,
            avg_rating = (SELECT AVG(rating) FROM feedback),
            updated_at = CURRENT_TIMESTAMP
    """)

    # Если отзыв хороший (4-5), добавляем пару для обучения
    if feedback.rating >= 4:
        cursor.execute("SELECT user_message, bot_reply FROM queries WHERE id = ?", (feedback.query_id,))
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "INSERT INTO training_pairs (input_text, output_text, source, quality_score) VALUES (?, ?, 'feedback', ?)",
                (row[0], row[1], feedback.rating / 5.0)
            )

    conn.commit()
    conn.close()

    return {"status": "ok", "feedback_id": feedback_id, "message": "Спасибо за отзыв!"}


@router.get("/stats")
async def get_stats():
    """Получить статистику обучения"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM training_metrics")
    metrics = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) FROM queries")
    total_queries = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM feedback")
    total_feedback = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM training_pairs")
    total_pairs = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(rating) FROM feedback")
    avg_rating = cursor.fetchone()[0] or 0

    cursor.execute("SELECT category, COUNT(*) as cnt FROM feedback GROUP BY category ORDER BY cnt DESC")
    categories = [{"category": row[0], "count": row[1]} for row in cursor.fetchall()]

    cursor.execute("SELECT rating, COUNT(*) as cnt FROM feedback GROUP BY rating ORDER BY rating")
    rating_dist = [{"rating": row[0], "count": row[1]} for row in cursor.fetchall()]

    conn.close()

    return {
        "total_queries": total_queries,
        "total_feedback": total_feedback,
        "total_training_pairs": total_pairs,
        "avg_rating": round(avg_rating, 2),
        "categories": categories,
        "rating_distribution": rating_dist,
    }


@router.get("/recent")
async def get_recent_feedback(limit: int = 20):
    """Получить последние отзывы"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT f.id, f.rating, f.comment, f.category, f.created_at,
               q.user_message, q.bot_reply
        FROM feedback f
        JOIN queries q ON f.query_id = q.id
        ORDER BY f.created_at DESC
        LIMIT ?
    """, (limit,))

    feedbacks = []
    for row in cursor.fetchall():
        feedbacks.append({
            "id": row[0],
            "rating": row[1],
            "comment": row[2],
            "category": row[3],
            "created_at": row[4],
            "user_message": row[5],
            "bot_reply": row[6],
        })

    conn.close()
    return {"feedbacks": feedbacks}


@router.post("/training/add")
async def add_training_pair(pair: TrainingPairCreate):
    """Добавить пару для обучения вручную"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO training_pairs (input_text, output_text, source, quality_score) VALUES (?, ?, ?, ?)",
        (pair.input_text, pair.output_text, pair.source, pair.quality_score)
    )
    pair_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return {"status": "ok", "pair_id": pair_id}


@router.get("/training/export")
async def export_training_data():
    """Экспорт данных для обучения (формат для fine-tuning)"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT input_text, output_text, quality_score
        FROM training_pairs
        WHERE used_in_training = 0
        ORDER BY quality_score DESC
        LIMIT 1000
    """)

    pairs = []
    for row in cursor.fetchall():
        pairs.append({
            "input": row[0],
            "output": row[1],
            "quality": row[2],
        })

    conn.close()

    return {
        "total": len(pairs),
        "pairs": pairs,
        "format": "input-output pairs for fine-tuning"
    }


@router.post("/training/apply")
async def apply_training():
    """Применить данные для обучения (обновить модель)"""
    conn = get_db()
    cursor = conn.cursor()

    # Получаем необработанные пары
    cursor.execute("""
        SELECT id, input_text, output_text, quality_score
        FROM training_pairs
        WHERE used_in_training = 0
        ORDER BY quality_score DESC
        LIMIT 100
    """)

    pairs = cursor.fetchall()

    if not pairs:
        conn.close()
        return {"status": "ok", "message": "Нет новых данных для обучения", "applied": 0}

    # Помечаем как использованные
    pair_ids = [p[0] for p in pairs]
    placeholders = ",".join("?" * len(pair_ids))
    cursor.execute(f"UPDATE training_pairs SET used_in_training = 1 WHERE id IN ({placeholders})", pair_ids)

    # Обновляем метрики
    cursor.execute("""
        UPDATE training_metrics SET
            training_sessions = training_sessions + 1,
            last_training = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
    """)

    conn.commit()
    conn.close()

    return {
        "status": "ok",
        "message": f"Применено {len(pairs)} пар для обучения",
        "applied": len(pairs),
        "note": "В демо-режиме данные сохраняются для будущего fine-tuning"
    }
