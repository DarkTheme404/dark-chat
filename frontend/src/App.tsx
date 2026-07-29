import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage, CodeBlock, ImageBlock, VideoBlock } from './components';
import { api } from './services/api';
import './App.css';

type Tab = 'chat' | 'code' | 'image' | 'video';

interface Message {
  id: number;
  type: 'user' | 'assistant';
  content: string;
  tab: Tab;
}

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('chat');
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

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

      switch (activeTab) {
        case 'chat':
          const chatRes = await api.chat(input);
          response = chatRes.reply;
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

      const assistantMessage: Message = {
        id: Date.now() + 1,
        type: 'assistant',
        content: response,
        tab: activeTab,
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
  ];

  return (
    <div className="app">
      <header className="header">
        <h1>Dark Chat</h1>
        <p>AI-powered助手 для кода, изображений и видео</p>
      </header>

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

      <main className="chat-area">
        <div className="messages">
          {messages.length === 0 && (
            <div className="empty-state">
              <h2>Добро пожаловать в Dark Chat!</h2>
              <p>Выберите вкладку и начните работу</p>
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
    </div>
  );
}

export default App;
