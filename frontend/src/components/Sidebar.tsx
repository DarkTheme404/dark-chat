import React, { useState, useEffect } from 'react';

interface Session {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message: string;
}

interface SidebarProps {
  activeSession: string | null;
  onSelectSession: (sessionId: string) => void;
  onNewSession: () => void;
  refreshTrigger: number;
}

export function Sidebar({ activeSession, onSelectSession, onNewSession, refreshTrigger }: SidebarProps) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSessions();
  }, [refreshTrigger]);

  const loadSessions = async () => {
    try {
      const res = await fetch('/api/sessions/');
      const data = await res.json();
      setSessions(data.sessions);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const deleteSession = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    if (!confirm('Удалить сессию?')) return;

    try {
      await fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' });
      loadSessions();
    } catch (e) {
      console.error(e);
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return 'Сегодня';
    if (days === 1) return 'Вчера';
    if (days < 7) return `${days} дн. назад`;
    return date.toLocaleDateString('ru');
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h3>Чаты</h3>
        <button className="new-chat-btn" onClick={onNewSession}>
          + Новый
        </button>
      </div>

      <div className="sessions-list">
        {loading && <div className="loading-sessions">Загрузка...</div>}

        {!loading && sessions.length === 0 && (
          <div className="no-sessions">Нет сессий</div>
        )}

        {sessions.map(session => (
          <div
            key={session.session_id}
            className={`session-item ${activeSession === session.session_id ? 'active' : ''}`}
            onClick={() => onSelectSession(session.session_id)}
          >
            <div className="session-title">
              {session.title || 'Без названия'}
            </div>
            <div className="session-meta">
              <span className="session-date">{formatDate(session.updated_at)}</span>
              <span className="session-count">{session.message_count} сообщ.</span>
            </div>
            <button
              className="session-delete"
              onClick={(e) => deleteSession(e, session.session_id)}
              title="Удалить"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
