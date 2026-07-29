const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = {
  async chat(message: string) {
    const response = await fetch(`${API_BASE}/api/chat/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    return response.json();
  },

  async generateCode(prompt: string, language: string = 'python') {
    const response = await fetch(`${API_BASE}/api/code/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, language }),
    });
    return response.json();
  },

  async generateImage(prompt: string) {
    const response = await fetch(`${API_BASE}/api/image/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt }),
    });
    return response.json();
  },

  async generateVideo(prompt: string) {
    const response = await fetch(`${API_BASE}/api/video/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt }),
    });
    return response.json();
  },
};
