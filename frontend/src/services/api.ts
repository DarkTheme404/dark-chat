const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function fetchWithTimeout(url: string, options: RequestInit = {}, timeoutMs: number = 60000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    return response;
  } finally {
    clearTimeout(timeout);
  }
}

export const api = {
  async chat(message: string, sessionId: string = '') {
    const response = await fetchWithTimeout(`${API_BASE}/api/chat/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId }),
    }, 60000);
    return response.json();
  },

  async generateCode(prompt: string, language: string = 'python') {
    const response = await fetchWithTimeout(`${API_BASE}/api/code/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, language }),
    }, 30000);
    return response.json();
  },

  async generateImage(prompt: string) {
    const response = await fetchWithTimeout(`${API_BASE}/api/image/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt }),
    }, 30000);
    return response.json();
  },

  async generateVideo(prompt: string) {
    const response = await fetchWithTimeout(`${API_BASE}/api/video/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt }),
    }, 30000);
    return response.json();
  },

  async listSessions() {
    const response = await fetchWithTimeout(`${API_BASE}/api/sessions/`);
    return response.json();
  },

  async createSession(title: string = 'Новый чат') {
    const response = await fetchWithTimeout(`${API_BASE}/api/sessions/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    return response.json();
  },

  async getSession(sessionId: string) {
    const response = await fetchWithTimeout(`${API_BASE}/api/sessions/${sessionId}`);
    return response.json();
  },

  async deleteSession(sessionId: string) {
    const response = await fetchWithTimeout(`${API_BASE}/api/sessions/${sessionId}`, {
      method: 'DELETE',
    });
    return response.json();
  },
};
