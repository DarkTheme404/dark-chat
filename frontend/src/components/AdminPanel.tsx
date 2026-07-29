import React, { useState, useEffect } from 'react';

interface Stats {
  total_queries: number;
  total_feedback: number;
  total_training_pairs: number;
  avg_rating: number;
  categories: { category: string; count: number }[];
  rating_distribution: { rating: number; count: number }[];
}

interface Feedback {
  id: number;
  rating: number;
  comment: string;
  category: string;
  created_at: string;
  user_message: string;
  bot_reply: string;
}

export function AdminPanel() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [feedbacks, setFeedbacks] = useState<Feedback[]>([]);
  const [activeTab, setActiveTab] = useState<'stats' | 'feedback' | 'training'>('stats');

  useEffect(() => {
    loadStats();
    loadFeedbacks();
  }, []);

  const loadStats = async () => {
    try {
      const res = await fetch('/api/feedback/stats');
      setStats(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const loadFeedbacks = async () => {
    try {
      const res = await fetch('/api/feedback/recent');
      const data = await res.json();
      setFeedbacks(data.feedbacks);
    } catch (e) {
      console.error(e);
    }
  };

  const applyTraining = async () => {
    try {
      const res = await fetch('/api/feedback/training/apply', { method: 'POST' });
      const data = await res.json();
      alert(data.message);
      loadStats();
    } catch (e) {
      console.error(e);
    }
  };

  const exportData = async () => {
    try {
      const res = await fetch('/api/feedback/training/export');
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'darkchat-training-data.json';
      a.click();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="admin-panel">
      <h2>Панель управления Dark Chat</h2>

      <div className="admin-tabs">
        <button
          className={activeTab === 'stats' ? 'active' : ''}
          onClick={() => setActiveTab('stats')}
        >
          Статистика
        </button>
        <button
          className={activeTab === 'feedback' ? 'active' : ''}
          onClick={() => setActiveTab('feedback')}
        >
          Отзывы
        </button>
        <button
          className={activeTab === 'training' ? 'active' : ''}
          onClick={() => setActiveTab('training')}
        >
          Обучение
        </button>
      </div>

      {activeTab === 'stats' && stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-number">{stats.total_queries}</div>
            <div className="stat-label">Всего запросов</div>
          </div>
          <div className="stat-card">
            <div className="stat-number">{stats.total_feedback}</div>
            <div className="stat-label">Отзывов</div>
          </div>
          <div className="stat-card">
            <div className="stat-number">{stats.total_training_pairs}</div>
            <div className="stat-label">Пар для обучения</div>
          </div>
          <div className="stat-card">
            <div className="stat-number">{stats.avg_rating.toFixed(1)} ★</div>
            <div className="stat-label">Средняя оценка</div>
          </div>

          <div className="stat-card wide">
            <h4>Распределение оценок</h4>
            {stats.rating_distribution.map(d => (
              <div key={d.rating} className="rating-bar">
                <span>{d.rating} ★</span>
                <div className="bar" style={{ width: `${(d.count / stats.total_feedback) * 100}%` }} />
                <span>{d.count}</span>
              </div>
            ))}
          </div>

          <div className="stat-card wide">
            <h4>Категории</h4>
            {stats.categories.map(c => (
              <div key={c.category} className="category-item">
                <span>{c.category}</span>
                <span>{c.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'feedback' && (
        <div className="feedback-list">
          {feedbacks.length === 0 && <p>Пока нет отзывов</p>}
          {feedbacks.map(f => (
            <div key={f.id} className="feedback-item">
              <div className="feedback-header">
                <span className="feedback-rating">{'★'.repeat(f.rating)}{'☆'.repeat(5 - f.rating)}</span>
                <span className="feedback-category">{f.category}</span>
                <span className="feedback-date">{new Date(f.created_at).toLocaleDateString('ru')}</span>
              </div>
              <div className="feedback-messages">
                <div className="msg user">👤 {f.user_message}</div>
                <div className="msg bot">🤖 {f.bot_reply.substring(0, 100)}...</div>
              </div>
              {f.comment && <div className="feedback-comment">💬 {f.comment}</div>}
            </div>
          ))}
        </div>
      )}

      {activeTab === 'training' && (
        <div className="training-panel">
          <h3>Управление обучением</h3>
          <p>Экспортируйте данные для обучения или примените накопленные отзывы.</p>

          <div className="training-actions">
            <button onClick={exportData} className="btn-export">
              📥 Экспорт данных (JSON)
            </button>
            <button onClick={applyTraining} className="btn-apply">
              🔄 Применить отзывы для обучения
            </button>
          </div>

          <div className="training-info">
            <h4>Как работает обучение:</h4>
            <ol>
              <li>Пользователи отправляют запросы</li>
              <li>Они оценивают ответы (1-5 звёзд)</li>
              <li>Хорошие ответы (4-5 ★) сохраняются как обучающие данные</li>
              <li>Данные экспортируются для fine-tuning модели</li>
              <li>Модель дообучается на пользовательских данных</li>
            </ol>
          </div>
        </div>
      )}
    </div>
  );
}
