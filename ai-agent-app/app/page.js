"use client";

import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import styles from "./page.module.css";

export default function Home() {
  // --- chat state ---
  const [messages, setMessages] = useState([
    { role: "ai", content: "สวัสดี เราคือ HealthCare++ 🩺 พร้อมช่วยแนะนำสินค้าสุขภาพให้คุณค่ะ" },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // --- session handling ---
  const SESSION_KEY = "chat_session_id";
  const getSessionId = () =>
    typeof window !== "undefined" ? sessionStorage.getItem(SESSION_KEY) : null;
  const setSessionId = (id) => {
    if (typeof window !== "undefined") sessionStorage.setItem(SESSION_KEY, id);
  };

  // --- refs / actions ---
  const chatRef = useRef(null);
  const ctaToChat = () => {
    if (chatRef.current) chatRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { role: "human", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch(process.env.NEXT_PUBLIC_API_URL + "/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Id": getSessionId() || "",
        },
        body: JSON.stringify({ messages: [...messages, userMessage] }),
        credentials: "include",
      });

      const data = await response.json();
      if (data?.session_id) setSessionId(data.session_id);

      const aiText =
        typeof data?.response === "string"
          ? data.response
          : "ขอโทษค่ะ ระบบมีปัญหาชั่วคราว ลองอีกครั้งได้นะคะ";
      setMessages((prev) => [...prev, { role: "ai", content: aiText }]);
    } catch (e) {
      console.error(e);
      setMessages((prev) => [
        ...prev,
        { role: "ai", content: "โอ๊ปส์! มีบางอย่างผิดพลาด กรุณาลองใหม่อีกครั้งค่ะ" },
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
          <a href="#products">Products</a>
          <a href="#whyus">Why Us</a>
          <a href="#faq">FAQ</a>
        </nav>
      </header>

      {/* Hero */}
      <section className={styles.hero}>
        <div className={styles.heroInner}>
          <div className={styles.heroText}>
            <div className={styles.badge}>
              ระบบผู้ช่วยอัจฉริยะที่จะช่วยค้นหา เปรียบเทียบ และแนะนำผลิตภัณฑ์จากร้าน HealthCare++
            </div>

            <h1 className={styles.headline}>
              ดูแลสุขภาพง่ายขึ้น <br /> <span className={styles.accent}>ด้วยผู้ช่วย AI ที่รู้ใจคุณ</span>
              <br />
              ลองคุยกับผู้ช่วย AI ของเรา <br /> <span className={styles.accent}>เพื่อแนะนำสินค้า</span>
            </h1>

            <div className={styles.heroButtons}>
              <button className={styles.primaryBtn} onClick={ctaToChat}>
                คุยหรือลองสอบถาม AI เลย !
              </button>
            </div>
          </div>

          {/* twin images like screenshot */}
          <div className={styles.imageRow}>
            <div className={styles.cardImg}>
              <img src="/cyber_ai.jpg" alt="" />
            </div>
            <div className={styles.cardImg}>
              <img src="/care_ai.jpg" alt="" />
            </div>
          </div>
        </div>
      </section>

      {/* Chat box */}
      <section id="chat" ref={chatRef} className={styles.chatSection} aria-label="AI Chat">
        <div className={styles.chatWrap}>
          <h2 className={styles.chatTitle}>Chat with AI</h2>

          <div className={styles.chatBox}>
            {messages.map((m, i) => (
              <div
                key={i}
                className={`${styles.msgRow} ${m.role === "human" ? styles.right : styles.left}`}
              >
                {m.role !== "human" && (
                  <div className={styles.profile}>
                    <img src="/made-in-china.webp" alt="AI" />
                    <div className={styles.name}>HealthCare++</div>
                  </div>
                )}

                <div
                  className={`${styles.bubble} ${m.role === "human" ? styles.userBubble : styles.aiBubble}`}
                >
                  <ReactMarkdown>{m.content}</ReactMarkdown>
                </div>

                {m.role === "human" && (
                  <div className={styles.profile}>
                    <img src="/tai.png" alt="User" />
                    <div className={styles.name}>คุณ</div>
                  </div>
                )}
              </div>
            ))}
          </div>


          <div className={styles.inputArea}>
            <input
              className={styles.input}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
              placeholder="พิมพ์ เช่น “โฟมล้างหน้าสำหรับผิวแห้ง”"
              aria-label="พิมพ์ข้อความแชต"
            />
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
