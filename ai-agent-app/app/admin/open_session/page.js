"use client";

import { useEffect, useRef, useState } from "react";
import Navbar from "../Component/nav";
import { LogoutButton } from "../Component/logout";
import styles from "./page.module.css";

export default function Home() {
  const API = process.env.NEXT_PUBLIC_API_URL;

  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const limit = 10;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  useEffect(() => {
    const fetchTickets = async () => {
      try {
        setLoading(true);
        setErrorMsg("");

        const res = await fetch(
          `${API}/admin/open-session?page=${page}&limit=${limit}`,
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

  return (
    <div className={styles.layout}>
      <Navbar />

      <main className={styles.main}>
        <div className={styles.header}>
          <h1 className={styles.title}>Session opened in server</h1>
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
                  <th>ID</th>
                  <th>started_at</th>
                  <th>last_activity_at</th>
                  <th>closed_at</th>
                  <th>status</th>
                  <th>message_count</th>
                  <th>total_duration_sec</th>
                  <th>dialog_status</th>
                  <th>mode</th>
                </tr>
              </thead>
              <tbody>
                {tickets.map((t) => (
                  <tr key={t.id}>
                    <td>{t.id}</td>
                    <td>{t.started_at? new Date(t.started_at).toLocaleString("th-TH"):"-"}</td>
                    <td>{t.last_activity_at ? new Date(t.last_activity_at).toLocaleString("th-TH"):"-"}</td>
                    <td>{t.closed_at ? new Date(t.closed_at).toLocaleString("th-TH"):"-"}</td>
                    <td>{t.status}</td>
                    <td>{t.message_count}</td>
                    <td>{t.total_duration_sec}</td>
                    <td>{t.dialog_status}</td>
                    <td>{t.mode}</td>
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