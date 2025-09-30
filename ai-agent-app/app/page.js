"use client"

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import styles from "./page.module.css";

export default function Home() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const SESSION_KEY = "chat_session_id";
  const getSessionId = () => (typeof window !== "undefined" ? sessionStorage.getItem(SESSION_KEY) : null);
  const setSessionId = (id) => { if (typeof window !== "undefined") sessionStorage.setItem(SESSION_KEY, id); };

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { role: "human", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch(process.env.NEXT_PUBLIC_API_URL + "/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json",
          'X-Session-Id': getSessionId() || '',
         },
        body: JSON.stringify({ messages: [...messages, userMessage] }),
      });
      const data = await response.json();
      if (data.session_id) setSessionId(data.session_id);
      setMessages((prev) => [...prev, { role: "ai", content: data.response }]);
      setInput('');
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Chat with AI</h1>

      <div className={styles.chatBox}>
        {messages.map((m, i) => (
          <div
            key={i}
            className={`${styles.msg} ${
              m.role === "human" ? styles.userMsg : styles.aiMsg
            }`}
          >
            <div className={styles.md}>
              <ReactMarkdown>{m.content}</ReactMarkdown>
            </div>
          </div>
        ))}
      </div>

      <div className={styles.inputArea}>
        <input
          className={styles.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="พิมพ์ข้อความ..."
        />
        <button
          className={styles.button}
          onClick={sendMessage}
          disabled={loading}
        >
          {loading ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}
