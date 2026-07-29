import React from 'react';

export function ChatMessage({ content }: { content: string }) {
  return (
    <div className="chat-message">
      <p>{content}</p>
    </div>
  );
}

export function CodeBlock({ code }: { code: string }) {
  return (
    <div className="code-block">
      <div className="code-header">
        <span>Python</span>
        <button onClick={() => navigator.clipboard.writeText(code)}>
          Копировать
        </button>
      </div>
      <pre><code>{code}</code></pre>
    </div>
  );
}

export function ImageBlock({ src }: { src: string }) {
  return (
    <div className="image-block">
      <img src={src} alt="Generated" />
      <a href={src} download="dark-chat-image.png">
        Скачать
      </a>
    </div>
  );
}

export function VideoBlock({ src }: { src: string }) {
  return (
    <div className="video-block">
      <video controls src={src}>
        Ваш браузер не поддерживает видео
      </video>
    </div>
  );
}
