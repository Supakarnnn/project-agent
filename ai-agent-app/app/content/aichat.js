"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import styles from "./aichat.module.css";
import Feedback from "../feedback";

export default function ChatBox({ chatRef }) {

    // fixed ai message
    const INITIAL_MESSAGE = {
        role: "ai",
        content: "สวัสดีค่ะ ฉันชื่อ Vitails 🩺 พร้อมช่วยแนะนำสินค้าสุขภาพให้คุณค่ะ",
    };

    // storage keys
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
        } catch { }
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

    // chat state
    const [messages, setMessages] = useState(() => {
        const stored = getChatFromStorage();
        return stored && stored.length ? stored : [INITIAL_MESSAGE];
    });

    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);

    // Determine initial mode based on the last message in history
    const [isAgentMode, setIsAgentMode] = useState(() => {
        const stored = getChatFromStorage();
        if (!stored || stored.length === 0) return false;
        const lastMsg = stored[stored.length - 1];
        return lastMsg.role === "agent";
    });

    // session
    const [sessionId, setSessionId] = useState(() => getSessionIdFromStorage());

    const saveSessionId = (id) => {
        setSessionId(id);
        storageSet(SESSION_KEY, id);
    };

    useEffect(() => {
        saveChatToStorage(messages);
    }, [messages]);

    // websocket
    const wsRef = useRef(null);

    const getWsBaseUrl = () => {
        if (process.env.NEXT_PUBLIC_WS_URL) return process.env.NEXT_PUBLIC_WS_URL;
        if (process.env.NEXT_PUBLIC_API_URL) {
            return process.env.NEXT_PUBLIC_API_URL.replace(/^http/, "ws");
        }
        return "";
    };

    useEffect(() => {
        if (!sessionId) return;

        const wsBase = getWsBaseUrl();
        if (!wsBase) return;

        const ws = new WebSocket(`${wsBase}/ws/${sessionId}/user`);
        wsRef.current = ws;

        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.sender === "agent") {
                    setIsAgentMode(true);
                    setMessages((prev) => [...prev, { role: "agent", content: msg.content }]);
                } else if (msg.sender === "system" && msg.content === "END_SESSION") {
                    setIsAgentMode(false);
                }
            } catch (e) {
                console.error("WS parse error", e);
            }
        };

        ws.onclose = () => {
            wsRef.current = null;
        };

        return () => {
            try {
                ws.close();
            } catch { }
        };
    }, [sessionId]);

    // clear chat
    const clearChat = () => {
        if (wsRef.current) {
            try {
                wsRef.current.close();
            } catch { }
            wsRef.current = null;
        }

        setMessages([INITIAL_MESSAGE]);
        setSessionId(null);

        if (typeof window !== "undefined") {
            localStorage.removeItem(CHAT_KEY);
            localStorage.removeItem(SESSION_KEY);
        }
    };

    // send message
    const sendMessage = async () => {
        if (!input.trim() || loading) return;

        const userMessage = { role: "human", content: input.trim() };
        const nextMessages = [...messages, userMessage];

        setMessages(nextMessages);
        setInput("");
        setLoading(true);

        try {
            const historyForBackend = nextMessages
                .filter((m) => ["human", "ai", "system", "agent"].includes(m.role))
                .map((m) => {
                    if (m.role === "agent") {
                        return {
                            role: "ai",
                            content: `[Call Center Agent]: ${m.content}`
                        };
                    }
                    return { role: m.role, content: m.content };
                });

            const response = await fetch(
                (process.env.NEXT_PUBLIC_API_URL || "") + "/chat",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Session-Id": sessionId || "",
                    },
                    body: JSON.stringify({ messages: historyForBackend }),
                    credentials: "include",
                }
            );

            const data = await response.json();

            if (data?.session_id) {
                saveSessionId(data.session_id);
            }

            if (data?.mode === "human") {
                setIsAgentMode(true);
                setLoading(false);
                return;
            }

            const aiMessage = {
                role: "ai",
                content:
                    typeof data?.response === "string"
                        ? data.response
                        : "ขอโทษค่ะ ระบบมีปัญหาชั่วคราว กรุณาลองใหม่อีกครั้งค่ะ",
                message_id: data?.ai_message_id ?? null,
            };

            setIsAgentMode(false);
            setMessages((prev) => [...prev, aiMessage]);
        } catch (e) {
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

    const handleSuggestionClick = (text) => {
        setInput(text);
    };

    return (
        <section
            id="chat"
            className={styles.chatSection}
            aria-label="AI Chat"
        >
            {/* Left */}
            <div className={styles.infoPanel}>
                <div className={styles.aiLabel}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" />
                    </svg>
                    AI-POWERED
                </div>
                <h2 className={styles.title}>
                    Your Personal<br />Wellness Advisor
                </h2>
                <p className={styles.description}>
                    Our AI assistant helps you discover the right products for your unique health goals.
                    Ask about supplements, skincare routines, or herbal remedies — get personalized recommendations instantly.
                </p>

                <div className={styles.tryAskingTitle}>TRY Asking:</div>
                <div className={styles.suggestionChips}>
                    {[
                        "มีวิตามินหรืออาหารเสริมอะไรที่เหมาะกับการดูแลสุขภาพทั่วไปบ้าง?",
                        "ควรเลือกผลิตภัณฑ์ดูแลสุขภาพอย่างไรให้เหมาะกับตัวเอง?",
                        "มีผลิตภัณฑ์ดูแลสุขภาพอะไรแนะนำบ้าง?",
                        "มีโฟมล้างหน้าแบบไหนบ้าง?"
                    ].map((text, i) => (
                        <button
                            key={i}
                            className={styles.chip}
                            onClick={() => handleSuggestionClick(text)}
                        >
                            {text}
                        </button>
                    ))}
                </div>
            </div>

            {/* Right */}
            <div className={styles.chatWrap}>
                {/* Card Header */}
                <div className={styles.cardHeader}>
                    <div className={styles.headerInfo}>
                        <div className={styles.botAvatar}>
                            <img src="/bot.jpg" alt="AI" style={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover' }} />
                        </div>
                        <div>
                            <div className={styles.botName}>Vitalis AI</div>
                            <div className={styles.botStatus}>Always here to help</div>
                        </div>
                    </div>
                    <div className={styles.onlineStatus}>
                        <div className={isAgentMode ? styles.agentDot : styles.dot} />
                        {isAgentMode ? "Callcenter takeover" : "AI is Online"}
                    </div>
                </div>

                {isAgentMode && (
                    <div className={styles.agentBanner}>
                        You are now chatting with a human agent
                    </div>
                )}

                {/* Chat Messages */}
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
                                <div
                                    className={`${styles.bubble} ${isHuman ? styles.userBubble : styles.aiBubble}`}
                                >
                                    <ReactMarkdown>{m.content}</ReactMarkdown>

                                    {isAI && i !== 0 && m.message_id && (
                                        <Feedback
                                            messageId={m.message_id}
                                            sessionId={sessionId}
                                        />
                                    )}
                                </div>
                            </div>
                        );
                    })}

                    {loading && (
                        <div className={`${styles.msgRow} ${styles.left}`}>
                            <div
                                className={`${styles.bubble} ${styles.aiBubble}`}
                            >
                                <div className={styles.typingIndicator}>
                                    Thinking...
                                </div>
                            </div>
                        </div>
                    )}

                    <div />
                </div>

                {/* Input Area */}
                <div className={styles.inputArea}>
                    <div className={styles.inputWrapper}>
                        <textarea
                            className={styles.input}
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === "Enter" && !e.shiftKey) {
                                    e.preventDefault();
                                    sendMessage();
                                }
                            }}
                            placeholder="Ask about products, health tips..."
                            disabled={loading}
                            rows={1}
                        />
                        <button
                            className={styles.clearButton}
                            onClick={clearChat}
                            disabled={loading || messages.length <= 1}
                            title="Clear Chat"
                        >
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <polyline points="3 6 5 6 21 6"></polyline>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            </svg>
                        </button>
                        <button
                            className={styles.sendButton}
                            onClick={sendMessage}
                            disabled={loading || !input.trim()}
                        >
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <line x1="22" y1="2" x2="11" y2="13"></line>
                                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        </section>
    );
}
