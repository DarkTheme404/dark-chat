import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage, CodeBlock, ImageBlock, VideoBlock, FeedbackButton, AdminPanel, Sidebar } from './components';
import { api } from './services/api';
import './App.css';

type Tab = 'chat' | 'code' | 'image' | 'video' | 'admin';

interface Message {
  id: number;
  type: 'user' | 'assistant';
  content: string;
  tab: Tab;
  queryId?: number;
}

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('chat');
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Загружаем сообщения при выборе сессии
  useEffect(() => {
    if (activeSession && activeTab === 'chat') {
      loadSessionMessages(activeSession);
    }
  }, [activeSession]);

  const loadSessionMessages = async (sessionId: string) => {
    try {
      const res = await fetch(`/api/sessions/${sessionId}`);
      const data = await res.json();

      const loadedMessages: Message[] = [];
      data.messages.forEach((msg: any) => {
        loadedMessages.push({
          id: msg.id * 2,
          type: 'user',
          content: msg.user_message,
          tab: 'chat',
        });
        loadedMessages.push({
          id: msg.id * 2 + 1,
          type: 'assistant',
          content: msg.bot_reply,
          tab: 'chat',
          queryId: msg.id,
        });
      });

      setMessages(loadedMessages);
    } catch (e) {
      console.error(e);
    }
  };

  const handleNewSession = () => {
    setActiveSession(null);
    setMessages([]);
    setSidebarOpen(false);
  };

  const handleSelectSession = (id: string | null) => {
    setActiveSession(id);
    setSidebarOpen(false);
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now(),
      type: 'user',
      content: input,
      tab: activeTab,
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      let response = '';
      let queryId = 0;
      let newSessionId = '';

      switch (activeTab) {
        case 'chat':
          const chatRes = await api.chat(input, activeSession || '');
          response = chatRes.reply;
          queryId = chatRes.query_id;
          newSessionId = chatRes.session_id;
          break;
        case 'code':
          const codeRes = await api.generateCode(input, 'python');
          response = codeRes.code;
          break;
        case 'image':
          const imageRes = await api.generateImage(input);
          response = imageRes.image;
          break;
        case 'video':
          const videoRes = await api.generateVideo(input);
          response = videoRes.video_url || videoRes.status;
          break;
      }

      // Если создалась новая сессия — обновляем
      if (newSessionId && newSessionId !== activeSession) {
        setActiveSession(newSessionId);
        setRefreshTrigger(prev => prev + 1);
      }

      const assistantMessage: Message = {
        id: Date.now() + 1,
        type: 'assistant',
        content: response,
        tab: activeTab,
        queryId,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: 'chat', label: 'Чат', icon: '💬' },
    { id: 'code', label: 'Код', icon: '💻' },
    { id: 'image', label: 'Изображения', icon: '🖼️' },
    { id: 'video', label: 'Видео', icon: '🎬' },
    { id: 'admin', label: 'Админка', icon: '⚙️' },
  ];

  return (
    <div className="app">
      <header className="header">
        {activeTab === 'chat' && (
          <button className="menu-btn" onClick={() => setSidebarOpen(!sidebarOpen)}>☰</button>
        )}
        <div className="header-text">
          <h1>Dark Chat</h1>
          <p>AI-powered ассистент с самообучением</p>
        </div>
      </header>

      <div className="main-layout">
        {activeTab === 'chat' && (
          <>
            <Sidebar
              activeSession={activeSession}
              onSelectSession={handleSelectSession}
              onNewSession={handleNewSession}
              refreshTrigger={refreshTrigger}
              className={sidebarOpen ? 'open' : ''}
            />
            {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}
          </>
        )}

        <div className="content-area">
          <nav className="tabs">
            {tabs.map(tab => (
              <button
                key={tab.id}
                className={`tab ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </nav>

          {activeTab === 'admin' ? (
            <AdminPanel />
          ) : (
            <main className="chat-area">
              <div className="messages">
                {messages.length === 0 && (
                  <div className="empty-state">
                    <h2>Добро пожаловать в Dark Chat!</h2>
                    <p>Выберите сессию или начните новый чат</p>
                    <p className="hint">💡 Отвечайте на отзывы — это помогает обучать модель</p>
                  </div>
                )}

                {messages.map(msg => (
                  <div key={msg.id} className={`message ${msg.type}`}>
                    {msg.type === 'user' ? (
                      <div className="user-message">{msg.content}</div>
                    ) : (
                      <div className="assistant-message">
                        {msg.tab === 'image' && msg.content.startsWith('data:') ? (
                          <ImageBlock src={msg.content} />
                        ) : msg.tab === 'code' ? (
                          <CodeBlock code={msg.content} />
                        ) : msg.tab === 'video' && msg.content.startsWith('data:') ? (
                          <VideoBlock src={msg.content} />
                        ) : (
                          <ChatMessage content={msg.content} />
                        )}

                        {msg.queryId && msg.queryId > 0 && (
                          <div className="feedback-area">
                            <FeedbackButton queryId={msg.queryId} />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}

                {loading && (
                  <div className="loading">
                    <div className="spinner"></div>
                    <span>Генерация...</span>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              <div className="input-area">
                <input
                  type="text"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyPress={e => e.key === 'Enter' && handleSend()}
                  placeholder={
                    activeTab === 'chat' ? 'Напишите сообщение...' :
                    activeTab === 'code' ? 'Опишите какой код нужен...' :
                    activeTab === 'image' ? 'Опишите изображение...' :
                    'Опишите видео...'
                  }
                  disabled={loading}
                />
                <button onClick={handleSend} disabled={loading || !input.trim()}>
                  {loading ? '...' : '→'}
                </button>
              </div>
            </main>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
