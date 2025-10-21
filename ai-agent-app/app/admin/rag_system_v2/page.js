"use client";

import { useEffect, useState, useMemo } from "react";
import Navbar from "../Component/nav";
import { LogoutButton } from "../Component/logout";
import styles from "./page.module.css";

export default function RagSystem() {
  const API = process.env.NEXT_PUBLIC_API_URL;

  const [loadingList, setLoadingList] = useState(true);
  const [listErr, setListErr] = useState("");
  const [collections, setCollections] = useState([]);
  const [selected, setSelected] = useState("");

  const [rowsResp, setRowsResp] = useState(null);
  const [loadingPanel, setLoadingPanel] = useState(false);
  const [panelErr, setPanelErr] = useState("");

  useEffect(() => {
    (async () => {
      try {
        setLoadingList(true);
        setListErr("");
        const r = await fetch(`${API}/admin/collections`);
        const j = await r.json();
        if (Array.isArray(j.collections)) setCollections(j.collections);
        else throw new Error(j?.message || "Cannot load collections");
      } catch (e) {
        setListErr(e?.message || "load collections error");
      } finally {
        setLoadingList(false);
      }
    })();
  }, [API]);

  async function loadRows(name, page = 1, pageSize) {
    if (!name) return;
    setLoadingPanel(true);
    setPanelErr("");
    try {
      const ps = pageSize ?? (rowsResp ? rowsResp.page_size : 20);
      const data = await fetch(
        `${API}/admin/collections/${encodeURIComponent(
          name
        )}/rows?page=${page}&page_size=${ps}`
      ).then((r) => r.json());
      setRowsResp(data);
    } catch (e) {
      setPanelErr(e?.message || "load rows error");
    } finally {
      setLoadingPanel(false);
    }
  }

  function handleSelect(name) {
    setSelected(name);
    setRowsResp(null);
    loadRows(name, 1);
  }

  const totalPages = useMemo(() => {
    if (!rowsResp) return 1;
    const t = rowsResp.total || 0;
    const ps = rowsResp.page_size || 1;
    return Math.max(1, Math.ceil(t / ps));
  }, [rowsResp]);

  return (
    <div className={styles.layout}>
      <Navbar />
      <main className={styles.main}>
        <header className={styles.header}>
          <h1 className={styles.title}>AI Knowledge</h1>
          <div>
            <LogoutButton>ออกจากระบบ</LogoutButton>
          </div>
        </header>

        <div className={styles.contentGrid}>
          {/* Sidebar */}
          <aside className={styles.sidebar}>
            <div className={styles.sectionTitle}>Collections</div>
            {loadingList && <div className={styles.muted}>กำลังโหลด…</div>}
            {listErr && <div className={styles.error}>⚠ {listErr}</div>}
            {!loadingList && !listErr && (
              <ul className={styles.list}>
                {collections.map((c) => (
                  <li key={c}>
                    <button
                      className={`${styles.listItem} ${
                        selected === c ? styles.active : ""
                      }`}
                      onClick={() => handleSelect(c)}
                    >
                      {c}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </aside>

          {/* Panel */}
          <section className={styles.panel}>
            {!selected && (
              <div className={styles.placeholder}>
                เลือกคอลเล็กชันทางซ้ายเพื่อดูข้อมูล
              </div>
            )}

            {selected && (
              <>
                <div className={styles.sectionTitle}>
                  {selected} {loadingPanel && <span className={styles.muted}>…</span>}
                </div>
                {panelErr && <div className={styles.error}>⚠ {panelErr}</div>}

                {rowsResp && (
                  <div className={styles.card}>
                    <div className={styles.cardTitle}>
                      Rows (page {rowsResp.page} / {totalPages})
                    </div>

                    <div className={styles.tableWrap}>
                      <RowsTable rows={rowsResp.rows} />
                    </div>

                    <div className={styles.pagination}>
                      <button
                        className={styles.button}
                        disabled={rowsResp.page <= 1 || loadingPanel}
                        onClick={() => loadRows(selected, rowsResp.page - 1)}
                      >
                        ← Prev
                      </button>
                      <span className={styles.muted}>
                        {rowsResp.page} / {totalPages}
                      </span>
                      <button
                        className={styles.button}
                        disabled={rowsResp.page >= totalPages || loadingPanel}
                        onClick={() => loadRows(selected, rowsResp.page + 1)}
                      >
                        Next →
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}

function RowsTable({ rows }) {
  if (!rows || rows.length === 0) {
    return <div className={styles.muted}>ไม่มีข้อมูล</div>;
  }

  const cols = Object.keys(rows[0] || {});

  return (
    <table className={styles.table}>
      <thead>
        <tr>
          {cols.map((c) => (
            <th key={c}>{c}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            {cols.map((c) => {
              const val = r[c];
              if (Array.isArray(val) && c.toLowerCase().includes("vector")) {
                const len = r[`${c}_len`] ?? val.length;
                const preview = val.slice(0, 5).join(", ");
                const more = len > 5 ? `  (+${len - 5})` : "";
                return <td key={c}>[{preview}]{more}</td>;
              }
              return <td key={c}>{stringifyCell(val)}</td>;
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function stringifyCell(v) {
  if (v === null || v === undefined) return "";
  if (typeof v === "object") return JSON.stringify(v);
  const str = String(v);

  return str.length > 80 ? str.slice(0, 80) + "…" : str;
}

