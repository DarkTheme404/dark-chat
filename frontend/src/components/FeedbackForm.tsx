import React, { useState } from 'react';

interface FeedbackFormProps {
  queryId: number;
  onClose: () => void;
}

export function FeedbackForm({ queryId, onClose }: FeedbackFormProps) {
  const [rating, setRating] = useState(0);
  const [hoveredRating, setHoveredRating] = useState(0);
  const [comment, setComment] = useState('');
  const [category, setCategory] = useState('general');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async () => {
    if (rating === 0) return;

    try {
      const response = await fetch('/api/feedback/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query_id: queryId,
          rating,
          comment,
          category,
        }),
      });

      if (response.ok) {
        setSubmitted(true);
        setTimeout(onClose, 2000);
      }
    } catch (error) {
      console.error('Feedback error:', error);
    }
  };

  if (submitted) {
    return (
      <div className="feedback-form">
        <div className="feedback-success">
          <span className="success-icon">✓</span>
          <p>Спасибо за отзыв! Он поможет улучшить Dark Chat.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="feedback-form">
      <h4>Оцените ответ</h4>

      <div className="rating-stars">
        {[1, 2, 3, 4, 5].map(star => (
          <button
            key={star}
            className={`star ${star <= (hoveredRating || rating) ? 'active' : ''}`}
            onClick={() => setRating(star)}
            onMouseEnter={() => setHoveredRating(star)}
            onMouseLeave={() => setHoveredRating(0)}
          >
            ★
          </button>
        ))}
        <span className="rating-label">
          {rating === 1 && 'Плохо'}
          {rating === 2 && 'Слабо'}
          {rating === 3 && 'Нормально'}
          {rating === 4 && 'Хорошо'}
          {rating === 5 && 'Отлично'}
        </span>
      </div>

      <select
        value={category}
        onChange={e => setCategory(e.target.value)}
        className="feedback-category"
      >
        <option value="general">Общий</option>
        <option value="accuracy">Точность</option>
        <option value="helpfulness">Полезность</option>
        <option value="creativity">Креативность</option>
        <option value="code_quality">Качество кода</option>
        <option value="language">Язык</option>
      </select>

      <textarea
        value={comment}
        onChange={e => setComment(e.target.value)}
        placeholder="Комментарий (необязательно)"
        className="feedback-comment"
        rows={3}
      />

      <div className="feedback-actions">
        <button onClick={onClose} className="btn-cancel">
          Отмена
        </button>
        <button onClick={handleSubmit} disabled={rating === 0} className="btn-submit">
          Отправить
        </button>
      </div>
    </div>
  );
}

export function FeedbackButton({ queryId }: { queryId: number }) {
  const [showForm, setShowForm] = useState(false);

  return (
    <>
      <button
        className="feedback-trigger"
        onClick={() => setShowForm(true)}
        title="Оценить ответ"
      >
        📝
      </button>
      {showForm && (
        <FeedbackForm queryId={queryId} onClose={() => setShowForm(false)} />
      )}
    </>
  );
}
