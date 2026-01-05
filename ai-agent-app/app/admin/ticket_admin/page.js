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