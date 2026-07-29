import React, { useState, useRef, useEffect, useCallback } from 'react';
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
  responseType?: string;
  imageData?: string;
  codeData?: string;
  language?: string;
  redirectUrl?: string;
  generator?: string;
  fileUrl?: string;
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
  const [uploading, setUploading] = useState(false);
  const [thinking, setThinking] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => { scrollToBottom(); }, [messages]);

  useEffect(() => {
    if (activeSession && activeTab === 'chat') loadSessionMessages(activeSession);
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
    } catch (e) { console.error(e); }
  };

  const handleNewSession = () => { setActiveSession(null); setMessages([]); setSidebarOpen(false); };
  const handleSelectSession = (id: string | null) => { setActiveSession(id); setSidebarOpen(false); };

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
      let sessionTitle = '';
      let responseType = 'text';
      let imageData = '';
      let codeData = '';
      let language = '';
      let redirectUrl = '';
      let generator = '';

      switch (activeTab) {
        case 'chat': {
          const chatRes = await api.chat(input, activeSession || '', thinking);
          response = chatRes.reply;
          queryId = chatRes.query_id;
          newSessionId = chatRes.session_id;
          sessionTitle = chatRes.session_title || '';
          responseType = chatRes.type || 'text';
          imageData = chatRes.image || '';
          codeData = chatRes.code || '';
          language = chatRes.language || '';
          redirectUrl = chatRes.redirect_url || '';
          generator = chatRes.generator || '';
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
          if (videoRes.redirect_url) window.open(videoRes.redirect_url, '_blank');
          response = videoRes.status || videoRes.video_url || 'Видео готово';
          break;
        }
      }

      if (newSessionId && newSessionId !== activeSession) {
        setActiveSession(newSessionId);
        // Небольшая задержка чтобы БД обновила название
        setTimeout(() => setRefreshTrigger(prev => prev + 1), 1500);
      } else if (newSessionId && sessionTitle) {
        // Обновляем список сессий чтобы показать новое название
        setTimeout(() => setRefreshTrigger(prev => prev + 1), 1500);
      }

      setMessages(prev => [...prev, {
        id: Date.now() + 1, type: 'assistant', content: response, tab: activeTab, queryId,
        responseType, imageData, codeData, language, redirectUrl, generator,
      }]);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const userMessage: Message = {
      id: Date.now(), type: 'user',
      content: `📎 ${file.name} (${(file.size / 1024).toFixed(0)}KB)`,
      tab: 'chat',
    };
    setMessages(prev => [...prev, userMessage]);
    setUploading(true);

    try {
      const res = await api.uploadFile(file, input || '');
      setMessages(prev => [...prev, {
        id: Date.now() + 1, type: 'assistant', content: res.reply, tab: 'chat',
        responseType: res.file_type === 'image' ? 'image' : 'text',
        imageData: res.file_url || '',
      }]);
    } catch (error) {
      setMessages(prev => [...prev, {
        id: Date.now() + 1, type: 'assistant', content: 'Ошибка загрузки файла', tab: 'chat',
      }]);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
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
                if (window.innerWidth <= 768) setSidebarOpen(!sidebarOpen);
                else setSidebarCollapsed(!sidebarCollapsed);
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
              <button key={tab.id} className={`tab ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id)}>
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
                    <p>Отправляйте текст, фото, видео, аудио, документы — AI всё проанализирует</p>
                    <p className="hint">💡 Фото → описание, Код → генерация, Видео → анализ кадров</p>
                  </div>
                )}

                {messages.map(msg => (
                  <div key={msg.id} className={`message ${msg.type}`}>
                    {msg.type === 'user' ? (
                      <div className="user-message">{msg.content}</div>
                    ) : (
                      <div className="assistant-message">
                        {msg.responseType === 'image' && msg.imageData ? (
                          <ImageBlock src={msg.imageData} />
                        ) : msg.responseType === 'code' && msg.codeData ? (
                          <CodeBlock code={msg.codeData} />
                        ) : msg.responseType === 'video' && msg.redirectUrl ? (
                          <div className="video-redirect">
                            <p>{msg.content}</p>
                            <a href={msg.redirectUrl} target="_blank" rel="noopener noreferrer" className="btn-video-link">
                              🎬 Открыть {msg.generator || 'генератор видео'}
                            </a>
                          </div>
                        ) : (
                          <ChatMessage content={msg.content} />
                        )}
                        {msg.queryId && msg.queryId > 0 && (
                          <div className="feedback-area"><FeedbackButton queryId={msg.queryId} /></div>
                        )}
                      </div>
                    )}
                  </div>
                ))}

                {(loading || uploading) && (
                  <div className="loading">
                    <div className="spinner"></div>
                    <span>{uploading ? 'Загрузка файла...' : 'Генерация...'}</span>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              <div className="input-area">
                <input type="file" ref={fileInputRef} onChange={handleFileUpload}
                  accept="image/*,audio/*,video/*,.pdf,.txt,.csv,.json,.md" className="file-input" />
                <button className="btn-attach" onClick={() => fileInputRef.current?.click()}
                  disabled={loading || uploading} title="Прикрепить файл">📎</button>
                {activeTab === 'chat' && (
                  <button
                    className={`btn-thinking ${thinking ? 'active' : ''}`}
                    onClick={() => setThinking(!thinking)}
                    title={thinking ? 'Глубокое мышление: включено (умные модели, длинные ответы)' : 'Быстрый режим (быстрые модели)'}
                  >
                    {thinking ? '🧠' : '⚡'}
                  </button>
                )}
                <input
                  type="text" value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyPress={e => e.key === 'Enter' && handleSend()}
                  placeholder={
                    activeTab === 'chat' ? 'Напишите сообщение или прикрепите файл...' :
                    activeTab === 'code' ? 'Опишите какой код нужен...' :
                    activeTab === 'image' ? 'Опишите изображение...' :
                    'Опишите видео...'
                  }
                  disabled={loading || uploading}
                />
                <button onClick={handleSend} disabled={loading || uploading || !input.trim()}>
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
  const [symbol, setSymbol] = useState('BTC-USD');
  const [customSymbol, setCustomSymbol] = useState('');
  const [interval, setInterval] = useState('1d');
  const [analysis, setAnalysis] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [marketData, setMarketData] = useState<any>(null);
  const [goal, setGoal] = useState('');
  const [strategy, setStrategy] = useState('');
  const [period, setPeriod] = useState('1mo');

  const popularSymbols = [
    { group: 'Крипто', items: [
      { label: 'BTC', value: 'BTC-USD' },
      { label: 'ETH', value: 'ETH-USD' },
      { label: 'SOL', value: 'SOL-USD' },
      { label: 'BNB', value: 'BNB-USD' },
      { label: 'XRP', value: 'XRP-USD' },
    ]},
    { group: 'Акции США', items: [
      { label: 'AAPL', value: 'AAPL' },
      { label: 'TSLA', value: 'TSLA' },
      { label: 'MSFT', value: 'MSFT' },
      { label: 'GOOGL', value: 'GOOGL' },
      { label: 'AMZN', value: 'AMZN' },
      { label: 'NVDA', value: 'NVDA' },
      { label: 'META', value: 'META' },
    ]},
    { group: 'ETF', items: [
      { label: 'SPY', value: 'SPY' },
      { label: 'QQQ', value: 'QQQ' },
      { label: 'VTI', value: 'VTI' },
    ]},
    { group: 'Форекс', items: [
      { label: 'EUR/USD', value: 'EURUSD=X' },
      { label: 'GBP/USD', value: 'GBPUSD=X' },
      { label: 'USD/JPY', value: 'USDJPY=X' },
      { label: 'USD/RUB', value: 'USDRUB=X' },
    ]},
    { group: 'Сырьё', items: [
      { label: 'Золото', value: 'GC=F' },
      { label: 'Серебро', value: 'SI=F' },
      { label: 'Нефть', value: 'CL=F' },
    ]},
  ];

  const periods = [
    { label: '1Н', value: '5d' },
    { label: '1М', value: '1mo' },
    { label: '3М', value: '3mo' },
    { label: '6М', value: '6mo' },
    { label: '1Г', value: '1y' },
    { label: '5Л', value: '5y' },
  ];

  const tvSymbol = symbol.includes('-') && !symbol.includes('=') ? `BINANCE:${symbol.replace('-','')}` :
    symbol.includes('=') ? symbol.replace('=','') : `NASDAQ:${symbol}`;

  const fetchMarketData = useCallback(async () => {
    try {
      const data = await api.getMarketData(symbol);
      setMarketData(data?.chart?.result?.[0] || null);
    } catch { setMarketData(null); }
  }, [symbol]);

  useEffect(() => { fetchMarketData(); }, [fetchMarketData]);

  const getChartSummary = () => {
    if (!marketData?.indicators?.quote?.[0]) return 'Нет данных';
    const q = marketData.indicators.quote[0];
    const closes = (q.close || []).filter((v: number|null) => v != null) as number[];
    if (closes.length < 2) return 'Недостаточно данных';

    const last = closes[closes.length - 1];
    const prev = closes[closes.length - 2];
    const high = Math.max(...closes);
    const low = Math.min(...closes);
    const change = ((last - prev) / prev * 100).toFixed(2);
    const changeAll = ((last - closes[0]) / closes[0] * 100).toFixed(2);

    const sma20 = closes.slice(-20).reduce((a: number, b: number) => a + b, 0) / Math.min(closes.length, 20);
    const sma50 = closes.slice(-50).reduce((a: number, b: number) => a + b, 0) / Math.min(closes.length, 50);

    return `Цена: ${last.toFixed(2)} | Изм: ${change}% (день), ${changeAll}% (период) | High: ${high.toFixed(2)} | Low: ${low.toFixed(2)} | SMA20: ${sma20.toFixed(2)} | SMA50: ${sma50.toFixed(2)} | Точек: ${closes.length}`;
  };

  const handleFullAnalyze = async () => {
    setAnalyzing(true);
    setAnalysis('');
    const chartInfo = getChartSummary();

    const goalText = goal ? `\nЦель трейдера: ${goal}` : '';
    const strategyText = strategy ? `\nСтратегия: ${strategy}` : '';

    const prompt = `Ты профессиональный трейдер-аналитик. Проанализируй ${symbol} на основе данных графика.

ДАННЫЕ ГРАФИКА:
${chartInfo}

ЦЕЛЬ И СТРАТЕГИЯ:${goalText}${strategyText}

Дай развёрнутый анализ:
1. Текущий тренд и его сила
2. Уровни поддержки и сопротивления (конкретные цены)
3. Технические индикаторы (SMA, RSI приблизительно)
4. Точка входа (цена покупки/продажи)
5. Тейк-профит и стоп-лосс
6. Рекомендация: ПОКУПАТЬ / ПРОДАВАТЬ / ЖДАТЬ
7. Риски

Если цель трейдера указана — дай персонализированный совет с учётом его стратегии.`;

    try {
      const res = await api.chat(prompt, '');
      setAnalysis(res.reply || 'Не удалось выполнить анализ');
    } catch {
      setAnalysis('Ошибка при анализе. Попробуйте позже.');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleSuggestAsset = async () => {
    if (!goal.trim()) return;
    setAnalyzing(true);
    setAnalysis('');

    const prompt = `Ты профессиональный финансовый консультант. Трейдер хочет: ${goal}
${strategy ? `Его стратегия: ${strategy}` : ''}

Подбери 3-5 наиболее подходящих инструментов (акции, крипто, форекс, ETF, сырьё) для достижения этой цели.
Для каждого укажи:
- Тикер/название
- Почему подходит (2-3 причины)
- Текущая цена (если знаешь)
- Рекомендуемая доля в портфеле
- Риски

Будь конкретным, цифры и тикеры, не общие слова.`;

    try {
      const res = await api.chat(prompt, '');
      setAnalysis(res.reply || 'Не удалось подобрать инструменты');
    } catch {
      setAnalysis('Ошибка. Попробуйте позже.');
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="trading-panel">
      <div className="trading-toolbar">
        <div className="trading-row">
          <select value={symbol} onChange={e => setSymbol(e.target.value)} className="trading-select">
            {popularSymbols.map(group => (
              <optgroup key={group.group} label={group.group}>
                {group.items.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
              </optgroup>
            ))}
          </select>
          <input type="text" className="trading-input" placeholder="Свой тикер..."
            value={customSymbol} onChange={e => setCustomSymbol(e.target.value)}
            onKeyPress={e => { if (e.key === 'Enter' && customSymbol.trim()) setSymbol(customSymbol.trim().toUpperCase()); }} />
        </div>

        <div className="trading-row">
          <div className="interval-btns">
            {periods.map(p => (
              <button key={p.value} className={`interval-btn ${period === p.value ? 'active' : ''}`}
                onClick={() => setPeriod(p.value)}>{p.label}</button>
            ))}
          </div>
        </div>

        <div className="trading-goals">
          <input type="text" className="trading-input full" placeholder="🎯 Чего хотите добиться? (напр: заработать 20% за месяц, пассивный доход, хеджирование рисков)"
            value={goal} onChange={e => setGoal(e.target.value)} />
          <input type="text" className="trading-input full" placeholder="📊 Стратегия (напр: скальпинг, свинг, долгосрочное инвестирование, DCA)"
            value={strategy} onChange={e => setStrategy(e.target.value)} />
        </div>

        <div className="trading-actions">
          <button className="btn-analyze" onClick={handleFullAnalyze} disabled={analyzing}>
            {analyzing ? '...' : '🧠 Анализ графика'}
          </button>
          <button className="btn-suggest" onClick={handleSuggestAsset} disabled={analyzing || !goal.trim()}>
            {analyzing ? '...' : '🎯 Подобрать инструмент'}
          </button>
        </div>
      </div>

      <div className="trading-chart">
        <iframe
          key={`${symbol}-${period}`}
          src={`https://www.tradingview.com/widgetembed/?symbol=${tvSymbol}&interval=D&theme=dark&style=1&locale=ru&hide_top_toolbar=0&hide_side_toolbar=1&allow_symbol_change=0&save_image=0&calendar=0&hide_volume=1`}
          frameBorder="0" scrolling="no" title="TradingView Chart"
        />
      </div>

      {marketData && (
        <div className="market-summary">
          <span>{getChartSummary()}</span>
        </div>
      )}

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
  const [rate, setRate] = useState(0.9);
  const [pitch, setPitch] = useState(1.0);
  const [volume, setVolume] = useState(1.0);
  const [history, setHistory] = useState<{ text: string; time: string }[]>([]);
  const [transcript, setTranscript] = useState('');
  const [recording, setRecording] = useState(false);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    const loadVoices = () => {
      const v = window.speechSynthesis?.getVoices() || [];
      // Приоритет: русские高质量 голоса
      const ru = v.filter(voice => voice.lang.startsWith('ru'));
      const en = v.filter(voice => voice.lang.startsWith('en') && voice.name.includes('Google'));
      setVoices(ru.length > 0 ? ru : [...en, ...v.slice(0, 10)]);
    };
    loadVoices();
    window.speechSynthesis?.addEventListener('voiceschanged', loadVoices);
    return () => window.speechSynthesis?.removeEventListener('voiceschanged', loadVoices);
  }, []);

  const speak = () => {
    if (!text.trim() || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();

    // Разбиваем длинный текст на предложения для более естественного звучания
    const sentences = text.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [text];

    let i = 0;
    const speakNext = () => {
      if (i >= sentences.length) {
        setSpeaking(false);
        setHistory(prev => [{ text: text.slice(0, 80), time: new Date().toLocaleTimeString('ru') }, ...prev].slice(0, 50));
        return;
      }

      const utterance = new SpeechSynthesisUtterance(sentences[i].trim());
      if (selectedVoice) {
        const voice = voices.find(v => v.name === selectedVoice);
        if (voice) utterance.voice = voice;
      }
      utterance.rate = rate;
      utterance.pitch = pitch;
      utterance.volume = volume;
      utterance.onend = () => { i++; speakNext(); };
      utterance.onerror = () => { setSpeaking(false); };
      window.speechSynthesis.speak(utterance);
    };

    setSpeaking(true);
    speakNext();
  };

  const stopSpeaking = () => { window.speechSynthesis?.cancel(); setSpeaking(false); };

  const startRecognition = () => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { setTranscript('Распознавание не поддерживается'); return; }
    const recognition = new SR();
    recognition.lang = 'ru-RU';
    recognition.continuous = false;
    recognition.interimResults = true;
    recognitionRef.current = recognition;

    recognition.onresult = (event: any) => {
      let final = '', interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) final += event.results[i][0].transcript;
        else interim += event.results[i][0].transcript;
      }
      setTranscript(final || interim);
      if (final) setText(prev => prev ? prev + ' ' + final : final);
    };
    recognition.onerror = () => setRecording(false);
    recognition.onend = () => setRecording(false);
    recognition.start();
    setRecording(true);
  };

  const stopRecognition = () => { recognitionRef.current?.stop(); setRecording(false); };

  const presets = [
    { label: '📰 Новости', text: 'Привет! Расскажи последние новости в мире технологий и криптовалют.' },
    { label: '📖 Рассказ', text: 'Однажды в тёмном ночном городе программист написал код, который изменил мир навсегда. Все забыли про баги, а деплой прошёл с первого раза.' },
    { label: '🎓 Обучение', text: 'Давай изучим основы Python. Объясни переменные, типы данных и функции простыми словами.' },
    { label: '😂 Шутка', text: 'Программист пришёл в бар. Бармен говорит: Чего закажешь? Программист: Пиво. Бармен: Пиво не найдено. Программист: Тогда кофе. Бармен: Кофе не найдено. Программист: Ну тогда воду. Бармен: Вода не найдена. Программист: Ну что у вас тогда есть? Бармен: Все функции работают, но данных нет.' },
  ];

  return (
    <div className="voice-panel">
      <div className="voice-section">
        <h3>🔊 Текст в речь</h3>
        <textarea className="voice-textarea" value={text} onChange={e => setText(e.target.value)}
          placeholder="Введите текст для озвучки..." rows={4} />

        <div className="voice-controls">
          <select className="voice-select" value={selectedVoice} onChange={e => setSelectedVoice(e.target.value)}>
            <option value="">Авто (лучший русский)</option>
            {voices.map(v => (
              <option key={v.name} value={v.name}>{v.name} ({v.lang})</option>
            ))}
          </select>

          <div className="voice-slider">
            <label>Скорость: {rate.toFixed(1)}x</label>
            <input type="range" min="0.5" max="1.5" step="0.05" value={rate}
              onChange={e => setRate(parseFloat(e.target.value))} />
          </div>

          <div className="voice-slider">
            <label>Тон: {pitch.toFixed(1)}</label>
            <input type="range" min="0.5" max="1.5" step="0.05" value={pitch}
              onChange={e => setPitch(parseFloat(e.target.value))} />
          </div>

          <div className="voice-slider">
            <label>Громкость: {Math.round(volume * 100)}%</label>
            <input type="range" min="0.3" max="1" step="0.05" value={volume}
              onChange={e => setVolume(parseFloat(e.target.value))} />
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
        <h3>🎤 Речь в текст</h3>
        <div className="voice-actions">
          {recording ? (
            <button className="btn-voice stop" onClick={stopRecognition}>⏹ Стоп запись</button>
          ) : (
            <button className="btn-voice record" onClick={startRecognition}>🎙 Записать</button>
          )}
        </div>
        {transcript && <div className="voice-transcript"><p>{transcript}</p></div>}
      </div>

      {history.length > 0 && (
        <div className="voice-section">
          <h3>📋 История</h3>
          <div className="voice-history">
            {history.map((h, i) => (
              <div key={i} className="voice-history-item">
                <span className="voice-history-time">{h.time}</span>
                <span className="voice-history-text">{h.text}{h.text.length >= 80 ? '...' : ''}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
