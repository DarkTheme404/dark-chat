import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage, CodeBlock, ImageBlock, FeedbackButton, AdminPanel, Sidebar } from './components';
import { api } from './services/api';
import './App.css';

type Tab = 'chat' | 'code' | 'image' | 'video' | 'trading' | 'voice' | 'admin';

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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

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
        loadedMessages.push({ id: msg.id * 2, type: 'user', content: msg.user_message, tab: 'chat' });
        loadedMessages.push({ id: msg.id * 2 + 1, type: 'assistant', content: msg.bot_reply, tab: 'chat', queryId: msg.id });
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

    const userMessage: Message = { id: Date.now(), type: 'user', content: input, tab: activeTab };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      let response = '';
      let queryId = 0;
      let newSessionId = '';

      switch (activeTab) {
        case 'chat': {
          const chatRes = await api.chat(input, activeSession || '');
          response = chatRes.reply;
          queryId = chatRes.query_id;
          newSessionId = chatRes.session_id;
          break;
        }
        case 'code': {
          const codeRes = await api.generateCode(input, 'python');
          response = codeRes.code;
          break;
        }
        case 'image': {
          const imageRes = await api.generateImage(input);
          response = imageRes.image;
          break;
        }
        case 'video': {
          const videoRes = await api.generateVideo(input);
          if (videoRes.redirect_url) {
            window.open(videoRes.redirect_url, '_blank');
          }
          response = videoRes.status || videoRes.video_url || 'Видео готово';
          break;
        }
      }

      if (newSessionId && newSessionId !== activeSession) {
        setActiveSession(newSessionId);
        setRefreshTrigger(prev => prev + 1);
      }

      const assistantMessage: Message = { id: Date.now() + 1, type: 'assistant', content: response, tab: activeTab, queryId };
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
    { id: 'image', label: 'Картинки', icon: '🖼️' },
    { id: 'video', label: 'Видео', icon: '🎬' },
    { id: 'voice', label: 'Озвучка', icon: '🔊' },
    { id: 'trading', label: 'Трейдинг', icon: '📈' },
    { id: 'admin', label: '⚙️', icon: '' },
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
              className={`${sidebarOpen ? 'open' : ''} ${sidebarCollapsed ? 'collapsed' : ''}`}
            />
            <button
              className="sidebar-collapse-btn"
              onClick={() => {
                if (window.innerWidth <= 768) {
                  setSidebarOpen(!sidebarOpen);
                } else {
                  setSidebarCollapsed(!sidebarCollapsed);
                }
              }}
            >
              {sidebarCollapsed ? '▶' : '◀'}
            </button>
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
                {tab.icon && <span className="tab-icon">{tab.icon}</span>}
                <span className="tab-label">{tab.label}</span>
              </button>
            ))}
          </nav>

          {activeTab === 'admin' ? (
            <AdminPanel />
          ) : activeTab === 'trading' ? (
            <TradingPanel />
          ) : activeTab === 'voice' ? (
            <VoicePanel />
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
                          <div className="video-block"><video src={msg.content} controls /></div>
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

/* ==================== TRADING PANEL ==================== */
function TradingPanel() {
  const [symbol, setSymbol] = useState('BTCUSD');
  const [interval, setInterval] = useState('D');
  const [analysis, setAnalysis] = useState('');
  const [analyzing, setAnalyzing] = useState(false);

  const symbols = [
    { label: 'BTC/USD', value: 'BTCUSD' },
    { label: 'ETH/USD', value: 'ETHUSD' },
    { label: 'SOL/USD', value: 'SOLUSD' },
    { label: 'AAPL', value: 'AAPL' },
    { label: 'TSLA', value: 'TSLA' },
    { label: 'SPY', value: 'SPY' },
    { label: 'MSFT', value: 'MSFT' },
    { label: 'GOOGL', value: 'GOOGL' },
  ];

  const intervals = [
    { label: '1м', value: '1' },
    { label: '5м', value: '5' },
    { label: '1ч', value: '60' },
    { label: '4ч', value: '240' },
    { label: '1Д', value: 'D' },
    { label: '1Н', value: 'W' },
  ];

  const tvSymbol = symbol.includes('BTC') || symbol.includes('ETH') || symbol.includes('SOL')
    ? `BINANCE:${symbol}`
    : `NASDAQ:${symbol}`;

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setAnalysis('');
    try {
      const res = await fetch('/api/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `Проанализируй ${symbol} на таймфрейме ${interval}. Кратко: тренд, уровни поддержки/сопротивления, вход/выход.`,
          session_id: ''
        })
      });
      const data = await res.json();
      setAnalysis(data.reply || 'Нет данных для анализа');
    } catch {
      setAnalysis('Ошибка при анализе');
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="trading-panel">
      <div className="trading-toolbar">
        <div className="trading-controls">
          <select value={symbol} onChange={e => setSymbol(e.target.value)}>
            {symbols.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
          <div className="interval-btns">
            {intervals.map(i => (
              <button
                key={i.value}
                className={`interval-btn ${interval === i.value ? 'active' : ''}`}
                onClick={() => setInterval(i.value)}
              >
                {i.label}
              </button>
            ))}
          </div>
          <button className="btn-analyze" onClick={handleAnalyze} disabled={analyzing}>
            {analyzing ? '...' : '🧠 Анализ'}
          </button>
        </div>
      </div>

      <div className="trading-chart">
        <iframe
          key={`${symbol}-${interval}`}
          src={`https://www.tradingview.com/widgetembed/?symbol=${tvSymbol}&interval=${interval}&theme=dark&style=1&locale=ru&hide_top_toolbar=0&hide_side_toolbar=0&allow_symbol_change=0&save_image=0&calendar=0&hide_volume=0`}
          frameBorder="0"
          scrolling="no"
          title="TradingView Chart"
        />
      </div>

      {analysis && (
        <div className="trading-analysis">
          <h3>📊 Анализ</h3>
          <ChatMessage content={analysis} />
        </div>
      )}
    </div>
  );
}

/* ==================== VOICE PANEL ==================== */
function VoicePanel() {
  const [text, setText] = useState('');
  const [speaking, setSpeaking] = useState(false);
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState('');
  const [rate, setRate] = useState(1);
  const [pitch, setPitch] = useState(1);
  const [history, setHistory] = useState<{ text: string; time: string }[]>([]);
  const [transcript, setTranscript] = useState('');
  const [recording, setRecording] = useState(false);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    const loadVoices = () => {
      const v = window.speechSynthesis?.getVoices() || [];
      const ru = v.filter(voice => voice.lang.startsWith('ru'));
      setVoices(ru.length > 0 ? ru : v);
    };
    loadVoices();
    window.speechSynthesis?.addEventListener('voiceschanged', loadVoices);
    return () => window.speechSynthesis?.removeEventListener('voiceschanged', loadVoices);
  }, []);

  const speak = () => {
    if (!text.trim() || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    if (selectedVoice) {
      const voice = voices.find(v => v.name === selectedVoice);
      if (voice) utterance.voice = voice;
    }
    utterance.rate = rate;
    utterance.pitch = pitch;
    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => {
      setSpeaking(false);
      setHistory(prev => [{ text, time: new Date().toLocaleTimeString('ru') }, ...prev].slice(0, 50));
    };
    window.speechSynthesis.speak(utterance);
  };

  const stopSpeaking = () => {
    window.speechSynthesis?.cancel();
    setSpeaking(false);
  };

  const startRecognition = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setTranscript('Распознавание речи не поддерживается в этом браузере');
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = 'ru-RU';
    recognition.continuous = false;
    recognition.interimResults = true;
    recognitionRef.current = recognition;

    recognition.onresult = (event: any) => {
      let finalTranscript = '';
      let interimTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interimTranscript += event.results[i][0].transcript;
        }
      }
      setTranscript(finalTranscript || interimTranscript);
      if (finalTranscript) {
        setText(prev => prev ? prev + ' ' + finalTranscript : finalTranscript);
      }
    };

    recognition.onerror = () => setRecording(false);
    recognition.onend = () => setRecording(false);
    recognition.start();
    setRecording(true);
  };

  const stopRecognition = () => {
    recognitionRef.current?.stop();
    setRecording(false);
  };

  const presets = [
    { label: '📰 Новости', text: 'Привет! Расскажи последние новости в мире технологий и криптовалют.' },
    { label: '📖 Рассказ', text: 'Однажды в тёмном ночном городе программист написал код, который изменил мир навсегда.' },
    { label: '🎓 Обучение', text: 'Давай изучим основы Python. Объясни переменные, типы данных и функции.' },
    { label: '😂 Шутка', text: 'Расскажи анекдот про программистов.' },
  ];

  return (
    <div className="voice-panel">
      <div className="voice-section">
        <h3>🔊 Текст в речь (TTS)</h3>
        <textarea
          className="voice-textarea"
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Введите текст для озвучки..."
          rows={4}
        />

        <div className="voice-controls">
          <select className="voice-select" value={selectedVoice} onChange={e => setSelectedVoice(e.target.value)}>
            <option value="">Авто (русский)</option>
            {voices.map(v => (
              <option key={v.name} value={v.name}>{v.name} ({v.lang})</option>
            ))}
          </select>

          <div className="voice-slider">
            <label>Скорость: {rate.toFixed(1)}x</label>
            <input type="range" min="0.5" max="2" step="0.1" value={rate} onChange={e => setRate(parseFloat(e.target.value))} />
          </div>

          <div className="voice-slider">
            <label>Тон: {pitch.toFixed(1)}</label>
            <input type="range" min="0.5" max="2" step="0.1" value={pitch} onChange={e => setPitch(parseFloat(e.target.value))} />
          </div>
        </div>

        <div className="voice-actions">
          {speaking ? (
            <button className="btn-voice stop" onClick={stopSpeaking}>⏹ Стоп</button>
          ) : (
            <button className="btn-voice play" onClick={speak} disabled={!text.trim()}>▶ Озвучить</button>
          )}
        </div>

        <div className="voice-presets">
          {presets.map((p, i) => (
            <button key={i} className="voice-preset" onClick={() => setText(p.text)}>{p.label}</button>
          ))}
        </div>
      </div>

      <div className="voice-section">
        <h3>🎤 Речь в текст (STT)</h3>
        <div className="voice-actions">
          {recording ? (
            <button className="btn-voice stop" onClick={stopRecognition}>⏹ Стоп запись</button>
          ) : (
            <button className="btn-voice record" onClick={startRecognition}>🎙 Записать</button>
          )}
        </div>
        {transcript && (
          <div className="voice-transcript">
            <p>{transcript}</p>
          </div>
        )}
      </div>

      {history.length > 0 && (
        <div className="voice-section">
          <h3>📋 История озвучки</h3>
          <div className="voice-history">
            {history.map((h, i) => (
              <div key={i} className="voice-history-item">
                <span className="voice-history-time">{h.time}</span>
                <span className="voice-history-text">{h.text.slice(0, 60)}{h.text.length > 60 ? '...' : ''}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
