"use client";

import { useEffect, useRef, useState } from "react";
import Navbar from "../nav";
import { LogoutButton } from "../../Component/logout";
import styles from "./page.module.css";

export default function Home() {
  const API = process.env.NEXT_PUBLIC_API_URL;

  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const limit = 20;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  const f2f = (v) => Number.isFinite(Number(v)) ? Number(v).toFixed(2) : "-";

  useEffect(() => {
    const fetchTickets = async () => {
      try {
        setLoading(true);
        setErrorMsg("");

        const res = await fetch(
          `${API}/admin/chat_log?page=${page}&limit=${limit}`,
          { cache: "no-store" }
        );

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        setTickets(Array.isArray(data.items) ? data.items : []);
        setTotal(Number.isFinite(data.total) ? data.total : 0);
      } catch (err) {
        setErrorMsg("ดึงข้อมูลไม่สำเร็จ");
        setTickets([]);
        setTotal(0);
      } finally {
        setLoading(false);
      }
    };

    if (!API) {
      setLoading(false);
      setErrorMsg("error");
      return;
    }

    fetchTickets();
  }, [page, API]);

  return (
    <div className={styles.layout}>
      <Navbar />

      <main className={styles.main}>
        <div className={styles.header}>
          <h1 className={styles.title}>Chat Log in server</h1>
          <LogoutButton>Logout</LogoutButton>
        </div>

        {loading && <p>Loading...</p>}
        {!loading && errorMsg && <p>{errorMsg}</p>}
        {!loading && !errorMsg && tickets.length === 0 && (
          <p>ไม่มี่ Session ใน server</p>
        )}

        {!loading && !errorMsg && tickets.length > 0 && (
          <>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Message_id</th>
                  <th>Session_id</th>
                  <th>Human message</th>
                  <th>Ai message</th>
                  <th>Sentiment</th>
                  <th>Intent name</th>
                  <th>Intent score</th>
                  <th>Ai confident</th>
                  <th>created_at</th>
                  <th>Used tools</th>
                </tr>
              </thead>
              <tbody>
                {tickets.map((t) => (
                  <tr key={t.message_id}>
                    <td>{t.message_id}</td>
                    <td>{t.session_id}</td>
                    <td className={styles.nowrapCell}>{t.human_message}</td>
                    <td className={styles.nowrapCell}>{t.ai_message}</td>
                    <td>{t.sentiment}</td>
                    <td>{t.intent_name}</td>
                    <td>{f2f(t.intent_score)}</td>
                    <td>{f2f(t.ai_confident)}</td>
                    <td>{t.created_at ? new Date(t.created_at).toLocaleString("th-TH") : "-"}</td>
                    <td>{t.used_tools}</td>
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
    </div>
  );
}