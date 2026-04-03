import React, { useState } from "react";

function App() {
  const [file, setFile] = useState(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [model, setModel] = useState("llama-3.3-70b-versatile");
  const [style, setStyle] = useState("paragraph");

  // 🔥 Upload PDF
  const uploadFile = async () => {
    if (!file) {
      alert("Please select a file!");
      return;
    }

    const formData = new FormData();
    formData.append("files", file); // ⚠️ backend expects "files"

    try {
      const res = await fetch("http://127.0.0.1:8000/upload", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      alert(data.message || "Upload done!");
    } catch (err) {
      alert("Upload failed!");
    }
  };

  // 🔥 Ask Question
  const askQuestion = async () => {
    if (!question) {
      alert("Enter a question!");
      return;
    }

    try {
      const res = await fetch("http://127.0.0.1:8000/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question,
          model,
          style,
        }),
      });

      const data = await res.json();

      setAnswer(data.answer);
      setSources(data.sources || []);
    } catch (err) {
      setAnswer("Error connecting to backend");
    }
  };

  return (
    <div style={{ padding: "30px", fontFamily: "Arial" }}>
      <h1>🔥 RAG AI Assistant</h1>

      {/* 📂 Upload */}
      <h3>Upload PDF</h3>
      <input type="file" onChange={(e) => setFile(e.target.files[0])} />
      <button onClick={uploadFile}>Upload</button>

      <hr />

      {/* 💬 Ask */}
      <h3>Ask Question</h3>

      <input
        type="text"
        placeholder="Type your question..."
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
      />

      <br /><br />

      {/* 🤖 Model */}
      <select value={model} onChange={(e) => setModel(e.target.value)}>
        <option value="llama-3.3-70b-versatile">Best Model</option>
        <option value="llama-3.1-8b-instant">Fast Model</option>
        <option value="qwen/qwen3-32b">Qwen Model</option>
      </select>

      {/* 🎯 Style */}
      <select value={style} onChange={(e) => setStyle(e.target.value)}>
        <option value="paragraph">Paragraph</option>
        <option value="bullet">Bullet</option>
        <option value="short">Short</option>
      </select>

      <br /><br />

      <button onClick={askQuestion}>Ask</button>

      {/* 🧠 Answer */}
      <h3>Answer</h3>
      <p>{answer}</p>

      {/* 📄 Sources */}
      <h3>Sources</h3>
      <ul>
        {sources.map((src, i) => (
          <li key={i}>{src}</li>
        ))}
      </ul>
    </div>
  );
}

export default App;