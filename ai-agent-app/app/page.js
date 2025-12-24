"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import styles from "./page.module.css";
import Feedback from "./feedback";

export default function Home() {
  //fix ai message
  const INITIAL_MESSAGE = {
    role: "ai",
    content: "สวัสดี เราคือ HealthCare++ 🩺 พร้อมช่วยแนะนำสินค้าสุขภาพให้คุณค่ะ",
  };

  //stroge message
  const SESSION_KEY = "chat_session_id";
  const CHAT_KEY = "chat_messages_v1";
  const storageGet = (key) => {
    if (typeof window === "undefined") return null;
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  };

  const storageSet = (key, value) => {
    if (typeof window === "undefined") return;
    try {
      localStorage.setItem(key, value);
    } catch {
      // ignore
    }
  };

  const storageRemove = (key) => {
    if (typeof window === "undefined") return;
    try {
      localStorage.removeItem(key);
    } catch {
      // ignore
    }
  };

  const getSessionIdFromStorage = () => storageGet(SESSION_KEY);

  const getChatFromStorage = () => {
    const raw = storageGet(CHAT_KEY);
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : null;
    } catch {
      return null;
    }
  };

  const saveChatToStorage = (msgs) => {
    storageSet(CHAT_KEY, JSON.stringify(msgs));
  };

  //chat state
  const [messages, setMessages] = useState(() => {
    const stored = getChatFromStorage();
    return stored && stored.length ? stored : [INITIAL_MESSAGE];
  });

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  //session
  const [sessionId, setSessionId] = useState(() => getSessionIdFromStorage());

  const saveSessionId = (id) => {
    setSessionId(id);
    storageSet(SESSION_KEY, id);
  };
  useEffect(() => {
    saveChatToStorage(messages);
  }, [messages]);

  //live chat websocket
  const wsRef = useRef(null);

  const getWsBaseUrl = () => {
    if (process.env.NEXT_PUBLIC_WS_URL) return process.env.NEXT_PUBLIC_WS_URL;
    if (process.env.NEXT_PUBLIC_API_URL) {
      return process.env.NEXT_PUBLIC_API_URL.replace(/^http/, "ws");
    }
    return "";
  };

  // open / close WebSocket ตาม sessionId
  useEffect(() => {
    if (!sessionId) return;

    const wsBase = getWsBaseUrl();
    if (!wsBase) return;

    const ws = new WebSocket(`${wsBase}/ws/${sessionId}/user`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("[WS] user connected to", sessionId);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.sender === "agent") {
          setMessages((prev) => [...prev, { role: "agent", content: msg.content }]);
        }
      } catch (err) {
        console.error("WS message parse error:", err);
      }
    };

    ws.onclose = () => {
      console.log("[WS] user disconnected");
      wsRef.current = null;
    };

    ws.onerror = (err) => {
      console.error("[WS] error:", err);
    };

    return () => {
      console.log("[WS] cleanup");
      try {
        ws.close();
      } catch { }
    };
  }, [sessionId]);

  const chatRef = useRef(null);
  const endRef = useRef(null);

  const ctaToChat = () => {
    if (chatRef.current)
      chatRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const scrollToEnd = useCallback(() => {
    if (endRef.current) endRef.current.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToEnd();
  }, [messages, loading, scrollToEnd]);

  //clear chat
  const clearChat = () => {
    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch (e) {
        console.warn("WS close error", e);
      }
      wsRef.current = null;
    }

    setMessages([INITIAL_MESSAGE]);
    setSessionId(null);

    if (typeof window !== "undefined") {
      localStorage.removeItem(CHAT_KEY);
      localStorage.removeItem(SESSION_KEY);
    }
  };

  //send message
  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = { role: "human", content: input.trim() };
    const nextMessages = [...messages, userMessage];

    setMessages(nextMessages);
    setInput("");
    setLoading(true);

    try {
      const historyForBackend = nextMessages
        .filter((m) => m.role === "human" || m.role === "ai" || m.role === "system")
        .map((m) => ({ role: m.role, content: m.content }));

      const response = await fetch((process.env.NEXT_PUBLIC_API_URL || "") + "/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Id": sessionId || "",
        },
        body: JSON.stringify({ messages: historyForBackend }),
        credentials: "include",
      });

      const data = await response.json();

      if (data && data.session_id) {
        saveSessionId(data.session_id);
      }

      // if mode = human
      if (data && data.mode === "human") {
        return;
      }

      const aiText =
        data && typeof data.response === "string"
          ? data.response
          : "ขอโทษค่ะ ระบบมีปัญหาชั่วคราว กรุณาลองใหม่อีกครั้งค่ะ";

      setMessages((prev) => [...prev, { role: "ai", content: aiText }]);
    } catch (e) {
      console.error(e);
      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          content: "ขอโทษค่ะ ระบบมีปัญหาชั่วคราว กรุณาลองใหม่อีกครั้งค่ะ",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      {/* Top Nav */}
      <header className={styles.nav}>
        <div className={styles.logo}>HealthCare++</div>
        <nav className={styles.navLinks}>
          <a href="/payment">Payment</a>
          <a href="#whyus">Why Us</a>
          <a href="#faq">FAQ</a>
        </nav>
      </header>

      <section className={styles.hero}>
        <div className={styles.heroInner}>
          <div className={styles.heroText}>
            <div className={styles.badge}>
              ระบบผู้ช่วยอัจฉริยะที่จะช่วยค้นหา เปรียบเทียบ และแนะนำผลิตภัณฑ์จากร้าน
              HealthCare++
            </div>

            <h1 className={styles.headline}>
              ดูแลสุขภาพง่ายขึ้น <br />
              <span className={styles.accent}>ด้วยผู้ช่วย AI ที่รู้ใจคุณ</span>
              <br />
              ลองคุยกับผู้ช่วย AI ของเรา <br />
              <span className={styles.accent}>เพื่อแนะนำสินค้า</span>
            </h1>

            <div className={styles.heroButtons}>
              <button className={styles.primaryBtn} onClick={ctaToChat}>
                คุยหรือลองสอบถาม AI เลย !
              </button>
            </div>
          </div>

          <div className={styles.imageRow}>
            <div className={styles.cardImg}>
              <img src="/cyber_ai.jpg" alt="" />
            </div>
            <div className={styles.cardImg}>
              <img src="/care_ai.jpg" alt="" />
            </div>
            <div className={styles.cardImglong}>
              <img src="front_store.png" alt="" />
            </div>
          </div>
        </div>
      </section>

      {/* Chat box */}
      <section id="chat" ref={chatRef} className={styles.chatSection} aria-label="AI Chat">
        <div className={styles.chatWrap}>
          <h2 className={styles.chatTitle}>Chat with AI</h2>

          <div className={styles.chatBox}>
            {messages.map((m, i) => {
              const isHuman = m.role === "human";
              const isAI = m.role === "ai";
              const isAgent = m.role === "agent";

              return (
                <div
                  key={i}
                  className={`${styles.msgRow} ${isHuman ? styles.right : styles.left}`}
                >
                  {!isHuman && (
                    <div className={styles.profile}>
                      {isAI && (
                        <>
                          <img src="/made-in-china.webp" alt="AI" />
                          <div className={styles.name}>HealthCare++</div>
                        </>
                      )}
                      {isAgent && (
                        <>
                          <img src="/admin.png" alt="Agent" />
                          <div className={styles.name}>เจ้าหน้าที่</div>
                        </>
                      )}
                    </div>
                  )}

                  <div
                    className={`${styles.bubble} ${isHuman ? styles.userBubble : styles.aiBubble
                      }`}
                  >
                    <ReactMarkdown>{m.content}</ReactMarkdown>
                    {/* {m.content} */}

                    {isAI && i !== 0 && (
                      <Feedback
                        messageId={i}
                        onRate={(data) => {
                          console.log("rated:", data);
                        }}
                      />
                    )}
                  </div>

                  {isHuman && (
                    <div className={styles.profile}>
                      <img src="/tai_real.png" alt="User" />
                      <div className={styles.name}>คุณ</div>
                    </div>
                  )}
                </div>
              );
            })}

            {loading && (
              <div className={`${styles.msgRow} ${styles.left}`}>
                <div className={styles.profile}>
                  <img src="/made-in-china.webp" alt="AI" />
                  <div className={styles.name}>HealthCare++</div>
                </div>

                <div className={styles.typingIndicator}>
                  <div className={styles.typingDot}></div>
                  <div className={styles.typingDot}></div>
                  <div className={styles.typingDot}></div>
                </div>
              </div>
            )}
          </div>

          <div className={styles.inputArea}>
            <textarea
              className={styles.input}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  if (e.shiftKey) return;
                  e.preventDefault();
                  sendMessage();
                }
              }}
              placeholder='พิมพ์ เช่น “โฟมล้างหน้าสำหรับผิวแห้ง”'
              aria-label="พิมพ์ข้อความแชต"
            />

            {/* Clear chat */}
            <button
              className={styles.button}
              type="button"
              onClick={clearChat}
              disabled={loading}
              title="ลบประวัติแชท"
            >
              Clear chat
            </button>

            {/* Send */}
            <button
              className={styles.button}
              onClick={sendMessage}
              disabled={loading}
              aria-busy={loading}
            >
              {loading ? "..." : "Send"}
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className={styles.footer}>
        <div>© {new Date().getFullYear()} HealthCare++ Shop</div>
        <div className={styles.footerLinks}>
          <a href="#">123</a>
          <a href="#">456</a>
          <a href="#">789</a>
        </div>
      </footer>
    </div>
  );
}
