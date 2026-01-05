"use client";

import { useEffect, useRef, useState } from "react";
import Navbar from "../nav";
import { LogoutButton } from "../../Component/logout";
import styles from "./page.module.css";

function LiveChat({ open, onClose, sessionId, ticketId, code}) {
  const API = process.env.NEXT_PUBLIC_API_URL;
  const pro_API = process.env.NEXT_PUBLIC_PROAPI_URL;

  const [connectedSession, setConnectedSession] = useState("");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const wsRef = useRef(null);

  const connect = (sid) => {
    if (!sid) return;

    if (wsRef.current) wsRef.current.close();

    const wsUrl = `ws://localhost:8001/ws/${sid}/agent`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectedSession(sid);
      setMessages([]);
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      setMessages((prev) => [
        ...prev,
        { sender: msg.sender, content: msg.content },
      ]);
    };

    ws.onclose = () => {
      wsRef.current = null;
      setConnectedSession("");
    };
  };

  const takeover = async (sid) => {
    if (!sid) return;
    await fetch(`${API}/admin/sessions/${sid}/takeover`, {
      method: "POST",
      credentials: "include",
    });
  };

  const backToAI = async () => {
    if (!sessionId) return;
    await fetch(`${API}/admin/sessions/${sessionId}/back-to-ai`, {
      method: "POST",
      credentials: "include",
    });
  };

  const closeCase = async () => {
    if (!ticketId) return;
    await fetch(
      `${API}/admin/tickets/${ticketId}/close`,
      {
        method: "POST",
        credentials: "include",
      }
    );
    await fetch(`${pro_API}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + process.env.NEXT_PUBLIC_CRM_TOKEN,
      },
      body: JSON.stringify({
        code: code,
        status: "Close",
      }),
    });
    await backToAI();
    onClose();
    setTimeout(() => window.location.reload(), 50);
  };

  const sendMessage = () => {
    if (!wsRef.current || wsRef.current.readyState !== 1) return;
    if (!input.trim()) return;

    wsRef.current.send(
      JSON.stringify({ sender: "agent", content: input.trim() })
    );
    setInput("");
  };

  useEffect(() => {
    if (!open) return;

    if (sessionId) {
      connect(sessionId);
      takeover(sessionId);
    }

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [open, sessionId]);

  if (!open) return null;

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.modalHeader}>
          <div>
            <div className={styles.modalTitle}>Live Chat</div>
            <div className={styles.modalSub}>
              session_id: <b>{sessionId || "-"}</b>{" "}
              {connectedSession ? "(connected)" : "(not connected)"}
            </div>
          </div>

          <div className={styles.modalActions}>
            <button
              className={styles.closeBtn}
              onClick={closeCase}
            >
              ปิด case
            </button>
          </div>
        </div>

        <div className={styles.chatBox}>
          {messages.map((m, i) => (
            <div key={i} className={styles.msgRow}>
              {m.sender === "user" && (
                <div className={styles.msgLeft}>
                  <strong>ลูกค้า:</strong> {m.content}
                </div>
              )}
              {m.sender === "ai" && (
                <div className={styles.msgLeft}>
                  <strong>AI:</strong> {m.content}
                </div>
              )}
              {m.sender === "agent" && (
                <div className={styles.msgRight}>
                  <strong>ฉัน:</strong> {m.content}
                </div>
              )}
            </div>
          ))}
        </div>

        <div className={styles.chatInputRow}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="ตอบกลับลูกค้า..."
            className={styles.chatInput}
          />
          <button onClick={sendMessage} className={styles.sendBtn}>
            ส่ง
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  const API = process.env.NEXT_PUBLIC_API_URL;

  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const [chatOpen, setChatOpen] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState("");
  const [selectedTicketId, setSelectedTicketId] = useState(null);
  const [code, setCode] = useState(null);

  const limit = 6;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  useEffect(() => {
    const fetchTickets = async () => {
      try {
        setLoading(true);
        setErrorMsg("");

        const res = await fetch(
          `${API}/admin/tickets?page=${page}&limit=${limit}`,
          { cache: "no-store" }
        );

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        setTickets(Array.isArray(data.items) ? data.items : []);
        setTotal(Number.isFinite(data.total) ? data.total : 0);
      } catch (err) {
        console.error("fetch tickets error:", err);
        setErrorMsg("ดึงข้อมูลไม่สำเร็จ");
        setTickets([]);
        setTotal(0);
      } finally {
        setLoading(false);
      }
    };

    if (!API) {
      setLoading(false);
      setErrorMsg("ยังไม่ได้ตั้งค่า NEXT_PUBLIC_API_URL");
      return;
    }

    fetchTickets();
  }, [page, API]);

  const openChat = (ticketId, sessionId, code) => {
    if (!sessionId) return;
    setSelectedTicketId(ticketId);
    setSelectedSessionId(sessionId);
    setCode(code);
    setChatOpen(true);
  };

  const closeChat = () => {
    setChatOpen(false);
    setSelectedSessionId("");
  };

  return (
    <div className={styles.layout}>
      <Navbar />

      <main className={styles.main}>
        <div className={styles.header}>
          <h1 className={styles.title}>Ticket Dashboard</h1>
          <LogoutButton>Logout</LogoutButton>
        </div>

        {loading && <p>Loading...</p>}
        {!loading && errorMsg && <p>{errorMsg}</p>}
        {!loading && !errorMsg && tickets.length === 0 && (
          <p>ไม่มี่ Ticket ที่ AI สร้าง</p>
        )}

        {!loading && !errorMsg && tickets.length > 0 && (
          <>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Code</th>
                  <th>ชื่อ</th>
                  <th>เบอร์</th>
                  <th>อีเมล</th>
                  <th>หมวดหมู่</th>
                  <th>รายละเอียด</th>
                  <th>สร้างเมื่อ</th>
                  <th>Connect</th>
                </tr>
              </thead>
              <tbody>
                {tickets.map((t) => (
                  <tr key={t.id}>
                    <td>{t.id}</td>
                    <td>{t.code}</td>
                    <td>{t.name || "-"}</td>
                    <td>{t.tel || "-"}</td>
                    <td>{t.email || "-"}</td>
                    <td>{t.category_fullname || "-"}</td>
                    <td>{t.detail || "-"}</td>
                    <td>
                      {t.created_at
                        ? new Date(t.created_at).toLocaleString("th-TH")
                        : "-"}
                    </td>
                    <td>
                      <button
                        className={styles.openBtn}
                        onClick={() => openChat(t.id, t.session_id, t.code)}
                        disabled={!t.session_id}
                        title={!t.session_id ? "ไม่มี session_id" : "เปิดแชท"}
                      >
                        Ready
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className={styles.pagination}>
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
              >
                ◀ ก่อนหน้า
              </button>

              <span>
                หน้า {page} / {totalPages} (ทั้งหมด {total})
              </span>

              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
              >
                ถัดไป ▶
              </button>
            </div>
          </>
        )}
      </main>

      <LiveChat
        open={chatOpen}
        onClose={closeChat}
        sessionId={selectedSessionId}
        ticketId={selectedTicketId}
        code={code}
      />
    </div>
  );
}
