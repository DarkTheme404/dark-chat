"""API для отзывов и обучения Dark Chat v2"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from models import get_db, init_db, FeedbackCreate, TrainingPairCreate, export_training_data, mark_as_trained

router = APIRouter()

init_db()


@router.post("/submit")
async def submit_feedback(feedback: FeedbackCreate):
    """Отправить отзыв на ответ бота (улучшает качество обучения)"""
    conn = get_db()
    cursor = conn.cursor()

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

    # Обновляем качество training pair на основе отзыва
    cursor.execute(
        "UPDATE training_pairs SET quality_score = quality_score * ? "
        "WHERE input_text = (SELECT user_message FROM queries WHERE id = ?) "
        "AND quality_score < 1.0",
        (feedback.rating / 5.0, feedback.query_id)
    )

    # Обновляем метрики
    cursor.execute("""
        UPDATE training_metrics SET
            total_feedback = total_feedback + 1,
            avg_rating = (SELECT AVG(rating) FROM feedback),
            updated_at = CURRENT_TIMESTAMP
    """)

    # Если отзыв хороший (4-5) — повышаем score модели
    if feedback.rating >= 4:
        cursor.execute("SELECT model_used FROM queries WHERE id = ?", (feedback.query_id,))
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "UPDATE model_scores SET total_positive = total_positive + 1, "
                "avg_rating = (total_queries * avg_rating + 1.0) / (total_queries + 1) "
                "WHERE model_name = ?",
                (row[0],)
            )

    conn.commit()
    conn.close()

    return {"status": "ok", "feedback_id": feedback_id, "message": "Спасибо за отзыв!"}


@router.get("/stats")
async def get_stats():
    """Статистика обучения"""
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

    cursor.execute("SELECT COUNT(*) FROM training_pairs WHERE used_in_training = 1")
    used_pairs = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(rating) FROM feedback")
    avg_rating = cursor.fetchone()[0] or 0

    cursor.execute("SELECT model_name, total_queries, total_positive, avg_rating FROM model_scores ORDER BY avg_rating DESC")
    models = [{"name": r[0], "queries": r[1], "positive": r[2], "rating": round(r[3], 2)} for r in cursor.fetchall()]

    conn.close()

    return {
        "total_queries": total_queries,
        "total_feedback": total_feedback,
        "total_training_pairs": total_pairs,
        "used_in_training": used_pairs,
        "ready_for_training": total_pairs - used_pairs,
        "avg_rating": round(avg_rating, 2),
        "models": models,
    }


@router.get("/recent")
async def get_recent_feedback(limit: int = 20):
    """Последние отзывы"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT f.id, f.rating, f.comment, f.category, f.created_at,
               q.user_message, q.bot_reply, q.model_used
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
            "model": row[7],
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
async def export_training_data_endpoint(format: str = "alpaca", min_quality: float = 0.5):
    """Экспорт данных для fine-tuning (Alpaca/ShareGPT формат)"""
    pairs = export_training_data(format=format, min_quality=min_quality)
    return {
        "total": len(pairs),
        "pairs": pairs,
        "format": format,
        "min_quality": min_quality,
    }


@router.post("/training/apply")
async def apply_training():
    """Пометить данные как использованные для обучения"""
    count = mark_as_trained()
    return {
        "status": "ok",
        "message": f"Помечено {count} пар как использованные",
        "applied": count,
    }


@router.get("/training/export-file")
async def export_training_file(format: str = "alpaca"):
    """Скачать датасет как JSON файл"""
    pairs = export_training_data(format=format, min_quality=0.4)
    return {
        "filename": f"darkchat_{format}_dataset.json",
        "content": pairs,
        "total": len(pairs),
    }
