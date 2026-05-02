import React, { useState, useRef, useEffect } from "react";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [model, setModel] = useState("llama-3.3-70b-versatile");
  const [style, setStyle] = useState("paragraph");
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Animated node network background canvas
  useEffect(() => {
    const chat = document.querySelector(".chat");
    if (!chat) return;
    const canvas = document.createElement("canvas");
    canvas.id = "node-canvas";
    chat.prepend(canvas);

    const ctx = canvas.getContext("2d");
    const N = 40;
    let animId;

    const resize = () => {
      canvas.width  = chat.offsetWidth;
      canvas.height = chat.offsetHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const nodes = Array.from({ length: N }, () => ({
      x:  Math.random() * canvas.width,
      y:  Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      r:  Math.random() * 1.8 + 0.8,
    }));

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (let i = 0; i < N; i++) {
        const a = nodes[i];
        a.x += a.vx; a.y += a.vy;
        if (a.x < 0 || a.x > canvas.width)  a.vx *= -1;
        if (a.y < 0 || a.y > canvas.height) a.vy *= -1;
        for (let j = i + 1; j < N; j++) {
          const b = nodes[j];
          const dx = a.x - b.x, dy = a.y - b.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.strokeStyle = `rgba(108,99,255,${(1 - dist / 120) * 0.18})`;
            ctx.lineWidth = 0.6;
            ctx.stroke();
          }
        }
        ctx.beginPath();
        ctx.arc(a.x, a.y, a.r, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(167,139,250,0.55)";
        ctx.fill();
      }
      animId = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", resize);
      canvas.remove();
    };
  }, []);

  // Auto-resize textarea as user types
  const handleInput = (e) => {
    setQuestion(e.target.value);
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = ta.scrollHeight + "px";
    }
  };

  // Upload — original logic unchanged
  const uploadFile = async () => {
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    await fetch("http://127.0.0.1:8000/upload", {
      method: "POST",
      body: formData,
    });
    setUploading(false);
    setUploaded(true);
  };

  // Ask — original logic unchanged
  const askQuestion = async () => {
    if (!question.trim()) return;

    const newMessages = [...messages, { role: "user", content: question }];
    setMessages(newMessages);
    setQuestion("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    setLoading(true);

    const res = await fetch("http://127.0.0.1:8000/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, model, style }),
    });

    const data = await res.json();
    setLoading(false);

    setMessages([
      ...newMessages,
      {
        role: "assistant",
        content: data.answer,
        sources: data.sources || [],
      },
    ]);
  };

  // Send on Enter, new line on Shift+Enter
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      askQuestion();
    }
  };

  return (
    <div className="app">

      {/* ── Sidebar ── */}
      <aside className="sidebar">

        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">⬡</div>
          <div className="sidebar-logo-text">RAG<span>Mind</span></div>
        </div>

        {/* Document upload */}
        <div className="sidebar-section">
          <span className="sidebar-label">Document</span>
          <div className={`upload-zone ${file ? "has-file" : ""}`}>
            <input
              type="file"
              onChange={(e) => {
                setFile(e.target.files[0]);
                setUploaded(false);
              }}
            />
            <div className="upload-icon">📄</div>
            <div className="upload-text">
              {file ? "" : "Drop file or click to browse"}
            </div>
            {file && <div className="upload-filename">{file.name}</div>}
          </div>

          <button
            className="upload-btn"
            onClick={uploadFile}
            disabled={!file || uploading}
          >
            {uploading ? "Uploading…" : "Upload Document"}
          </button>

          {uploaded && (
            <div className="upload-success">
              <span>✓</span> Indexed successfully
            </div>
          )}
        </div>

        <hr />

        {/* Model selector */}
        <div className="sidebar-section">
          <span className="sidebar-label">Model</span>
          <select value={model} onChange={(e) => setModel(e.target.value)}>
            <option value="llama-3.3-70b-versatile">Llama 3.3 70B — Best</option>
            <option value="llama-3.1-8b-instant">Llama 3.1 8B — Fast</option>
            <option value="qwen/qwen3-32b">Qwen 3 32B</option>
          </select>
        </div>

        {/* Response style selector */}
        <div className="sidebar-section">
          <span className="sidebar-label">Response Style</span>
          <select value={style} onChange={(e) => setStyle(e.target.value)}>
            <option value="paragraph">Paragraph</option>
            <option value="bullet">Bullet Points</option>
            <option value="short">Short Answer</option>
          </select>
        </div>

      </aside>

      {/* ── Chat ── */}
      <main className="chat">

        {/* Top bar */}
        <div className="chat-topbar">
          <div className="topbar-dot" />
          <span className="topbar-title">Document QA</span>
          <span className="topbar-badge">{model.split("-")[0]}</span>
        </div>

        {/* Messages */}
        <div className="messages">

          {messages.length === 0 && !loading && (
            <div className="empty-state">
              <div className="empty-icon">💬</div>
              <div className="empty-title">Ask your document</div>
              <div className="empty-sub">
                Upload a file on the left, then ask anything about it.
              </div>
            </div>
          )}

          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.role}`}>

              <div className={`msg-avatar ${msg.role}`}>
                {msg.role === "assistant" ? "⬡" : "↑"}
              </div>

              <div className="msg-body">
                <div className="bubble">
                  {msg.content}
                </div>

                {msg.sources && msg.sources.length > 0 && (
                  <div className="sources">
                    <strong>Sources</strong>
                    <ul>
                      {msg.sources.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

            </div>
          ))}

          {/* Typing indicator while waiting */}
          {loading && (
            <div className="message assistant">
              <div className="msg-avatar assistant">⬡</div>
              <div className="msg-body">
                <div className="typing-indicator">
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div className="input-area">
          <textarea
            ref={textareaRef}
            className="chat-input"
            value={question}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Ask something about your document…"
            rows={1}
          />
          <button
            className="send-btn"
            onClick={askQuestion}
            disabled={!question.trim() || loading}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="white">
              <path d="M2 21L23 12 2 3v7l15 2-15 2v7z" />
            </svg>
          </button>
        </div>

      </main>
    </div>
  );
}

export default App;