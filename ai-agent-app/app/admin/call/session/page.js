// LiveChatAdmin.js
"use client";

import { useEffect, useRef, useState } from "react";

export default function LiveChatAdmin() {
  const [sessionId, setSessionId] = useState("");
  const [connectedSession, setConnectedSession] = useState("");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const wsRef = useRef(null);

  const connect = () => {
    if (!sessionId) return;

    if (wsRef.current) wsRef.current.close();

    const wsUrl = `ws://localhost:8001/ws/${sessionId}/agent`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectedSession(sessionId);
      setMessages([]);
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      setMessages((prev) => [...prev, { sender: msg.sender, content: msg.content }]);
    };

    ws.onclose = () => {
      wsRef.current = null;
      setConnectedSession("");
    };
  };

  const sendMessage = () => {
    if (!wsRef.current || wsRef.current.readyState !== 1) return;
    if (!input.trim()) return;

    const payload = {
      sender: "agent",
      content: input.trim(),
    };

    wsRef.current.send(JSON.stringify(payload)); // จะไปเข้าที่ ws_endpoint แล้ว broadcast ออก
    setInput("");
  };

  const takeover = async () => {
    if (!sessionId) return;
    await fetch(process.env.NEXT_PUBLIC_API_URL + `/admin/sessions/${sessionId}/takeover`, {
      method: "POST",
      credentials: "include",
    });
  };

  const backToAI = async () => {
    if (!sessionId) return;
    await fetch(process.env.NEXT_PUBLIC_API_URL + `/admin/sessions/${sessionId}/back-to-ai`, {
      method: "POST",
      credentials: "include",
    });
  };

  return (
    <div style={{ padding: 16 }}>
      <h1>Live Chat Admin</h1>

      <div style={{ marginBottom: 8 }}>
        <input
          value={sessionId}
          onChange={(e) => setSessionId(e.target.value)}
          placeholder="ใส่ session_id จาก DB"
          style={{ width: 300, marginRight: 8 }}
        />
        <button
          onClick={() => { connect(); takeover();}} style={{ marginRight: 8 }}>
          เชื่อมต่อห้อง
        </button>
        {/* <button onClick={takeover} style={{ marginRight: 8 }}>
          Take over (โหมด Human)
        </button> */}
        <button onClick={backToAI}>กลับไปให้ AI ตอบ</button>
      </div>

      {connectedSession && <p>session: {connectedSession}</p>}

      <div
        style={{
          border: "1px solid #ccc",
          padding: 8,
          height: 300,
          overflowY: "auto",
          marginBottom: 8,
        }}
      >
        {messages.map((m, i) => (
          <div key={i} style={{ marginBottom: 4 }}>
            {m.sender === "user" && (
              <div>
                <strong>ลูกค้า:</strong> {m.content}
              </div>
            )}
            {m.sender === "ai" && (
              <div>
                <strong>AI:</strong> {m.content}
              </div>
            )}
            {m.sender === "agent" && (
              <div style={{ textAlign: "right" }}>
                <strong>ฉัน:</strong> {m.content}
              </div>
            )}
          </div>
        ))}
      </div>

      <div>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="ตอบกลับลูกค้า..."
          style={{ width: 300, marginRight: 8 }}
        />
        <button onClick={sendMessage}>ส่ง</button>
      </div>
    </div>
  );
}
