"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import Navbar from "../Component/nav";
import { LogoutButton } from "../Component/logout";
import styles from "./page.module.css";

const SEARCH_FIELDS = ["ProductName", "ProductName_Eng", "name", "name_eng", "code"];

export default function RagSystem() {
  const API = process.env.NEXT_PUBLIC_API_URL;

  const [loadingList, setLoadingList] = useState(true);
  const [listErr, setListErr] = useState("");
  const [collections, setCollections] = useState([]);
  const [selected, setSelected] = useState("");

  const [rowsResp, setRowsResp] = useState(null);
  const [loadingPanel, setLoadingPanel] = useState(false);
  const [panelErr, setPanelErr] = useState("");

  const [query, setQuery] = useState("");
  const [allRows, setAllRows] = useState(null);
  const [loadingAll, setLoadingAll] = useState(false); 
  const [allErr, setAllErr] = useState("");
  const [clientPage, setClientPage] = useState(1);
  const CLIENT_PAGE_SIZE = 20;

  const [hiddenCols, setHiddenCols] = useState(["id", "pk", "text", "notes"]);

  //list collection
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

  const loadRows = useCallback(
    async (name, page = 1, pageSize) => {
      if (!name) return;
      setLoadingPanel(true);
      setPanelErr("");
      try {
        const ps = pageSize ?? (rowsResp ? rowsResp.page_size : 20);
        const url = new URL(`${API}/admin/collections/${encodeURIComponent(name)}/rows`);
        url.searchParams.set("page", String(page));
        url.searchParams.set("page_size", String(ps));
        const data = await fetch(url.toString()).then((r) => r.json());
        setRowsResp(data);
      } catch (e) {
        setPanelErr(e?.message || "load rows error");
      } finally {
        setLoadingPanel(false);
      }
    },
    [API, rowsResp]
  );

  //fetch all page
  const fetchAllPages = useCallback(
    async (name) => {
      setAllErr("");
      setLoadingAll(true);
      try {
        const firstUrl = new URL(`${API}/admin/collections/${encodeURIComponent(name)}/rows`);
        firstUrl.searchParams.set("page", "1");
        firstUrl.searchParams.set("page_size", "100");
        const first = await fetch(firstUrl.toString()).then((r) => r.json());

        const total = first?.total ?? 0;
        const pageSize = 1000;
        const pages = Math.max(1, Math.ceil(total / pageSize));

        let acc = first?.rows || [];
        if (pageSize !== 100) {
          acc = [];
          for (let p = 1; p <= pages; p++) {
            const u = new URL(`${API}/admin/collections/${encodeURIComponent(name)}/rows`);
            u.searchParams.set("page", String(p));
            u.searchParams.set("page_size", String(pageSize));
            const j = await fetch(u.toString()).then((r) => r.json());
            acc = acc.concat(j?.rows || []);
          }
        }
        setAllRows(acc);
      } catch (e) {
        setAllErr(e?.message || "fetch all pages error");
      } finally {
        setLoadingAll(false);
      }
    },
    [API]
  );

  function handleSelect(name) {
    setSelected(name);
    setRowsResp(null);
    setAllRows(null);
    setClientPage(1);
    setQuery("");
    setHiddenCols(["id", "pk", "text", "notes"]); ////////////// ค่าเริ่มต้นการซ่อน /////////////////////
    loadRows(name, 1);
  }

  const submitSearch = useCallback(() => {
    if (!selected) return;
    setClientPage(1);
    if (!allRows) fetchAllPages(selected);
  }, [selected, allRows, fetchAllPages]);

  const searching = (query || "").trim().length > 0;
  const sourceRows = useMemo(() => {
    if (searching) {
      return allRows ?? rowsResp?.rows ?? [];
    }
    return rowsResp?.rows ?? [];
  }, [searching, allRows, rowsResp]);

  const filteredAll = useMemo(() => {
    const q = (query || "").trim().toLowerCase();
    if (!q) return sourceRows;
    return sourceRows.filter((r) =>
      SEARCH_FIELDS.some((k) => r?.[k] && String(r[k]).toLowerCase().includes(q))
    );
  }, [sourceRows, query]);

  const serverTotalPages = useMemo(() => {
    if (!rowsResp) return 1;
    const t = rowsResp.total || 0;
    const ps = rowsResp.page_size || 1;
    return Math.max(1, Math.ceil(t / ps));
  }, [rowsResp]);

  const clientTotalPages = useMemo(() => {
    return Math.max(1, Math.ceil((filteredAll?.length || 0) / CLIENT_PAGE_SIZE));
  }, [filteredAll]);

  const tableRows = useMemo(() => {
    if (searching) {
      const start = (clientPage - 1) * CLIENT_PAGE_SIZE;
      return filteredAll.slice(start, start + CLIENT_PAGE_SIZE);
    }
    return sourceRows;
  }, [searching, filteredAll, clientPage, sourceRows]);

  const startIndex = useMemo(() => {
    if (searching) return (clientPage - 1) * CLIENT_PAGE_SIZE;
    return (rowsResp?.page - 1) * (rowsResp?.page_size || 0);
  }, [searching, clientPage, rowsResp]);

  const allCols = useMemo(() => {
    const sample = (allRows || rowsResp?.rows || []).slice(0, 100);
    const set = new Set();
    for (const r of sample) Object.keys(r || {}).forEach((k) => set.add(k));
    return Array.from(set);
  }, [allRows, rowsResp]);

  const visibleCols = useMemo(
    () => allCols.filter((c) => !hiddenCols.includes(c)),
    [allCols, hiddenCols]
  );

  return (
    <div className={styles.layout}>
      <Navbar />
      <main className={styles.main}>
        <header className={styles.header}>
          <h1 className={styles.title}>AI Knowledge</h1>
          <div><LogoutButton>ออกจากระบบ</LogoutButton></div>
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
                      className={`${styles.listItem} ${selected === c ? styles.active : ""}`}
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
              <div className={styles.placeholder}>เลือกคอลเล็กชันทางซ้ายเพื่อดูข้อมูล</div>
            )}

            {selected && (
              <>
                <div className={styles.sectionTitle}>
                  {selected} {(loadingPanel || loadingAll) && <span className={styles.muted}>…</span>}
                </div>

                {/* Search Bar */}
                <div className={styles.card} style={{ marginBottom: 12 }}>
                  <div className={styles.cardTitle}>ค้นหา</div>
                  <div className={styles.searchRow}>
                    <input
                      className={styles.input}
                      placeholder="ค้นหา"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter") submitSearch(); }}
                    />
                    <button className={styles.button} onClick={submitSearch} disabled={!selected || loadingAll}>
                      ค้นหาทุกหน้า
                    </button>
                    <button
                      className={styles.ghostButton}
                      onClick={() => { setQuery(""); setClientPage(1); }}
                      disabled={loadingAll}
                    >
                      ล้าง
                    </button>
                    <span className={styles.muted} style={{ marginLeft: "auto" }}>
                      {loadingAll
                        ? "กำลังดึงข้อมูล"
                        : searching && allRows
                        ? `ผลลัพธ์ ${filteredAll.length} จากทั้งหมด ${allRows.length}`: ""}
                    </span>
                  </div>
                  {allErr && <div className={styles.error} style={{ marginTop: 8 }}>⚠ {allErr}</div>}
                </div>

                {(rowsResp || allRows) && (
                  <div className={styles.card} style={{ marginBottom: 12 }}>
                    <div className={styles.cardTitle}>Filter</div>
                    <ColumnsPicker allCols={allCols} hiddenCols={hiddenCols} onChange={setHiddenCols} />
                  </div>
                )}
                {panelErr && <div className={styles.error}>⚠ {panelErr}</div>}

                {/* Table */}
                {(rowsResp || allRows) && (
                  <div className={styles.card}>
                    <div className={styles.cardTitle}>
                      {searching
                        ? `Rows (page ${clientPage} / ${clientTotalPages})`
                        : `Rows (page ${rowsResp?.page} / ${serverTotalPages})`}
                    </div>

                    <div className={styles.tableWrap}>
                      <RowsTable rows={tableRows} cols={visibleCols} startIndex={startIndex} />
                    </div>

                    <div className={styles.pagination}>
                      {searching ? (
                        <>
                          <button
                            className={styles.button}
                            disabled={clientPage <= 1 || loadingAll}
                            onClick={() => setClientPage((p) => Math.max(1, p - 1))}
                          >
                            ← Prev
                          </button>
                          <span className={styles.muted}>{clientPage} / {clientTotalPages}</span>
                          <button
                            className={styles.button}
                            disabled={clientPage >= clientTotalPages || loadingAll}
                            onClick={() => setClientPage((p) => Math.min(clientTotalPages, p + 1))}
                          >
                            Next →
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            className={styles.button}
                            disabled={rowsResp?.page <= 1 || loadingPanel}
                            onClick={() => loadRows(selected, rowsResp.page - 1)}
                          >
                            ← Prev
                          </button>
                          <span className={styles.muted}>{rowsResp?.page} / {serverTotalPages}</span>
                          <button
                            className={styles.button}
                            disabled={rowsResp?.page >= serverTotalPages || loadingPanel}
                            onClick={() => loadRows(selected, rowsResp.page + 1)}
                          >
                            Next →
                          </button>
                        </>
                      )}
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

function RowsTable({ rows, cols, startIndex = 0 }) {
  if (!rows || rows.length === 0) {
    return <div className={styles.muted}>ไม่มีข้อมูล</div>;
  }
  const effectiveCols = cols && cols.length > 0 ? cols : Object.keys(rows[0] || {});
  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th style={{ width: 80, textAlign: "center" }}>Rows</th>
          {effectiveCols.map((c) => (<th key={c}>{c}</th>))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            <td style={{ textAlign: "center" }}>{startIndex + i + 1}</td>
            {effectiveCols.map((c) => {
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

function ColumnsPicker({ allCols, hiddenCols, onChange }) {
  if (!allCols || allCols.length === 0) {
    return <div className={styles.muted}>ไม่มีคอลัมน์ให้เลือก</div>;
  }
  const toggle = (col) => {
    const isHidden = hiddenCols.includes(col);
    if (isHidden) onChange(hiddenCols.filter((c) => c !== col));
    else onChange([...hiddenCols, col]);
  };
  const showAll = () => onChange([]);
  return (
    <div className={styles.columnsPicker}>
      <div className={styles.columnsPickerActions}>
        <button className={styles.ghostButton} onClick={showAll}>แสดงทั้งหมด</button>
      </div>
      <div className={styles.columnsGrid}>
        {allCols.map((c) => {
          const checked = !hiddenCols.includes(c);
          return (
            <label key={c} className={styles.colItem}>
              <input type="checkbox" checked={checked} onChange={() => toggle(c)} />
              <span>{c}</span>
            </label>
          );
        })}
      </div>
    </div>
  );
}

function stringifyCell(v) {
  if (v === null || v === undefined) return "";
  if (typeof v === "object") return JSON.stringify(v);
  const str = String(v);
  return str.length > 80 ? str.slice(0, 80) + "…" : str;
}
