"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import Navbar from "../Component/nav";
import { LogoutButton } from "../Component/logout";
import styles from "./page.module.css";

export default function RagSystem() {
  const API = process.env.NEXT_PUBLIC_API_URL;

  // load collections + create new collections
  const [collections, setCollections] = useState([]);
  const [loadingList, setLoadingList] = useState(false);
  const [listError, setListError] = useState("");
  const [name, setName] = useState("");
  const [dim, setDim] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [createMsg, setCreateMsg] = useState("");
  const [createErr, setCreateErr] = useState("");

  // upload file
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const [uploadErr, setUploadErr] = useState("");
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadType, setUploadType] = useState("pdf");
  const [targetCollection, setTargetCollection] = useState("");

  // upload history
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [uploadHistory, setUploadHistory] = useState([]);
  const [historyFilter, setHistoryFilter] = useState("");

  // delete history
  const [deleteBusyId, setDeleteBusyId] = useState("");

  const fetchCollections = useCallback(async () => {
    setLoadingList(true);
    setListError("");
    try {
      const r = await fetch(`${API}/admin/get-collections`, {
        method: "GET",
        credentials: "include",
      });
      if (!r.ok) {
        const t = await r.text().catch(() => "");
        throw new Error(t || `Load failed with ${r.status}`);
      }
      const j = await r.json();
      setCollections(Array.isArray(j.collections) ? j.collections : []);
    } catch (e) {
      setListError(e.message || "โหลดรายการล้มเหลว");
    } finally {
      setLoadingList(false);
    }
  }, [API]);

  useEffect(() => {
    fetchCollections();
  }, [fetchCollections]);

  useEffect(() => {
    if (collections?.length && !targetCollection) {
      setTargetCollection(collections[0].name);
    }
  }, [collections, targetCollection]);

  const dimError = useMemo(() => {
    if (!dim.toString().trim()) return "กรอก dim เป็นตัวเลขบังคับ";
    const n = Number(dim);
    if (!Number.isInteger(n)) return "dim ต้องเป็นจำนวนเต็ม";
    if (n <= 0) return "dim ต้องมากกว่า 0";
    if (n > 32768) return "dim สูงเกินไป (<= 32768)";
    return "";
  }, [dim]);

  async function onCreate(e) {
    e.preventDefault();
    setCreateMsg("");
    setCreateErr("");

    const trimmedName = name.trim();
    if (!trimmedName) {
      setCreateErr("กรุณากรอกชื่อ collection");
      return;
    }
    if (dimError) {
      setCreateErr(dimError);
      return;
    }

    setCreating(true);
    try {
      const r = await fetch(`${API}/admin/create_collections`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: trimmedName,
          dim: Number(dim),
          description: description?.trim() || undefined,
        }),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(j?.detail || j?.message || "สร้างไม่สำเร็จ");

      setCreateMsg(`สร้างสำเร็จ: ${j?.collection || trimmedName} (id: ${j?.id ?? "-"})`);
      setName("");
      setDim("");
      setDescription("");
      await fetchCollections();
    } catch (e) {
      setCreateErr(e.message || "สร้างไม่สำเร็จ");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(name) {
    if (!confirm(`ต้องการลบ collection: ${name}?`)) return;
    try {
      const r = await fetch(`${API}/admin/delete_collections/${name}`, {
        method: "DELETE",
        credentials: "include",
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j?.detail || "ลบไม่สำเร็จ");
      await fetchCollections();
    } catch (e) {
      alert(e.message || "ลบไม่สำเร็จ");
    }
  }

  const fetchUploadHistory = useCallback(
    async (col = "") => {
      setHistoryLoading(true);
      setHistoryError("");
      try {
        const url =
          col && col.trim()
            ? `${API}/admin/get-upload_history?collection=${encodeURIComponent(col.trim())}`
            : `${API}/admin/get-upload_history`;
        const r = await fetch(url, { credentials: "include" });
        const j = await r.json();
        if (!r.ok) throw new Error(j?.detail || "โหลดประวัติไม่สำเร็จ");
        setUploadHistory(Array.isArray(j.upload_history) ? j.upload_history : []);
      } catch (e) {
        setHistoryError(e.message || "โหลดประวัติไม่สำเร็จ");
      } finally {
        setHistoryLoading(false);
      }
    },
    [API]
  );

  useEffect(() => {
    fetchUploadHistory("");
  }, [fetchUploadHistory]);

  async function handleDeleteUpload(uploadId) {
    if (!uploadId) return;
    if (!confirm(`ต้องการลบข้อมูลอัปโหลดนี้หรือไม่?\nupload_id: ${uploadId}`)) return;

    try {
      setDeleteBusyId(uploadId);
      const r = await fetch(`${API}/admin/delete_file/${uploadId}`, {
        method: "DELETE",
        credentials: "include",
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(j?.detail || "ลบไม่สำเร็จ");

      await fetchUploadHistory(historyFilter);
    } catch (e) {
      alert(e.message || "ลบไม่สำเร็จ");
    } finally {
      setDeleteBusyId("");
    }
  }

  return (
    <div className={styles.layout}>
      <Navbar />
      <main className={styles.main}>
        <header className={styles.header}>
          <h1 className={styles.title}>AI Knowledge</h1>
          <div><LogoutButton>ออกจากระบบ</LogoutButton></div>
        </header>

        {/* List Collections */}
        <section className={styles.card}>
          <h2 className={styles.sectionTitle}>Collections List</h2>

          {loadingList ? (
            <p>กำลังโหลดรายการ…</p>
          ) : listError ? (
            <p className={styles.errorText}>{listError}</p>
          ) : collections.length === 0 ? (
            <p>ยังไม่มี collection</p>
          ) : (
            <div style={{ marginTop: 20, padding: 12, border: "1px solid #ddd", borderRadius: 8, background: "#fff" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "14px" }}>
                <thead>
                  <tr style={{ background: "#f9fafb" }}>
                    <th style={{ padding: "8px 10px", borderBottom: "1px solid #e5e7eb", textAlign: "left" }}>ID</th>
                    <th style={{ padding: "8px 10px", borderBottom: "1px solid #e5e7eb", textAlign: "left" }}>ชื่อ</th>
                    <th style={{ padding: "8px 10px", borderBottom: "1px solid #e5e7eb", textAlign: "left" }}>dim</th>
                    <th style={{ padding: "8px 10px", borderBottom: "1px solid #e5e7eb", textAlign: "left" }}>คำอธิบาย</th>
                    <th style={{ padding: "8px 10px", borderBottom: "1px solid #e5e7eb", textAlign: "left" }}>สร้างเมื่อ</th>
                    <th style={{ padding: "8px 10px", borderBottom: "1px solid #e5e7eb", textAlign: "left" }}></th>
                  </tr>
                </thead>
                <tbody>
                  {collections.map((c) => (
                    <tr key={c.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                      <td style={{ padding: "8px 10px" }}>{c.id}</td>
                      <td style={{ padding: "8px 10px" }}>{c.name}</td>
                      <td style={{ padding: "8px 10px" }}>{c.dim}</td>
                      <td style={{ padding: "8px 10px" }}>{c.description}</td>
                      <td style={{ padding: "8px 10px" }}>
                        {c.created_at ? new Date(c.created_at).toLocaleString() : "-"}
                      </td>
                      <td style={{ padding: "8px 10px" }}>
                        <button
                          style={{
                            padding: "4px 8px",
                            border: "none",
                            borderRadius: "4px",
                            background: "#ef4444",
                            color: "white",
                            cursor: "pointer",
                            fontSize: "13px",
                          }}
                          onClick={() => handleDelete(c.name)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

            </div>
          )}
        </section>

        {/* Create Collections */}
        <section style={{ marginTop: 16, padding: 12, border: "1px solid #ddd", borderRadius: 8, background: "#fff" }}>
          <h2 className={styles.sectionTitle}>Create New Collections</h2>
          <form onSubmit={onCreate} className={styles.formGrid}>
            <label className={styles.label}>
              ชื่อ (name)
              <input
                className={styles.input}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="เช่น products_th"
              />
            </label>

            <label className={styles.label}>
              มิติเวกเตอร์ (dim)
              <input
                className={styles.input}
                value={dim}
                onChange={(e) => setDim(e.target.value)}
                placeholder="เช่น 1024"
                inputMode="numeric"
              />
              {dimError && dim && <span className={styles.errorText}>{dimError}</span>}
            </label>

            <label className={styles.labelFull}>
              คำอธิบาย (description)
              <textarea
                className={styles.textarea}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="คำอธิบายสั้น ๆ ของ collection"
                rows={3}
              />
            </label>

            <div className={styles.actions}>
              <button className={styles.primaryBtn} type="submit" disabled={creating}>
                {creating ? "กำลังสร้าง..." : "สร้าง Collection"}
              </button>
              {createMsg && <span className={styles.successText}>{createMsg}</span>}
              {createErr && <span className={styles.errorText}>{createErr}</span>}
            </div>
          </form>
        </section>

        {/* Upload file */}
        <section style={{ marginTop: 16, padding: 12, border: "1px solid #ddd", borderRadius: 8, background: "#fff" }}>
          <h2 className={styles.sectionTitle}>Upload Data into Collections</h2>
          {collections.length === 0 ? (
            <p style={{ marginTop: 8, color: "#6b7280" }}>
              ยังไม่มี collection กรุณาสร้าง collection ก่อน
            </p>
          ) : (
            <form onSubmit={handleUpload} style={{ display: "grid", gap: 12, maxWidth: 720, marginTop: 8 }}>
              <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 14, color: "#374151" }}>
                เลือก Collection
                <select
                  value={targetCollection}
                  onChange={(e) => setTargetCollection(e.target.value)}
                  style={{
                    padding: "8px 10px",
                    border: "1px solid #d1d5db",
                    borderRadius: 6,
                    background: "#fff",
                    fontSize: 14,
                    maxWidth: 320,
                  }}
                >
                  {collections.map((c) => (
                    <option key={c.id} value={c.name}>
                      {c.name} (dim: {c.dim})
                    </option>
                  ))}
                </select>
              </label>

              <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 14, color: "#374151" }}>
                ประเภทไฟล์
                <select
                  value={uploadType}
                  onChange={(e) => setUploadType(e.target.value)}
                  style={{
                    padding: "8px 10px",
                    border: "1px solid #d1d5db",
                    borderRadius: 6,
                    background: "#fff",
                    fontSize: 14,
                    maxWidth: 200,
                  }}
                >
                  <option value="pdf">PDF (.pdf)</option>
                  <option value="text">Text (.txt)</option>
                </select>
              </label>

              <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 14, color: "#374151" }}>
                เลือกไฟล์สำหรับ upload
                <input
                  type="file"
                  accept={uploadType === "pdf" ? ".pdf" : ".txt"}
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  style={{
                    padding: 8,
                    border: "1px solid #d1d5db",
                    borderRadius: 6,
                    background: "#fff",
                    fontSize: 14,
                    maxWidth: 420,
                  }}
                />
                <span style={{ fontSize: 12, color: "#6b7280" }}>
                  รองรับไฟล์ PDF และ TXT เท่านั้น
                </span>
              </label>

              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <button
                  type="submit"
                  disabled={uploading || !uploadFile || !targetCollection}
                  style={{
                    padding: "8px 14px",
                    border: "none",
                    borderRadius: 6,
                    background: uploading ? "#9ca3af" : "#6366f1",
                    color: "#fff",
                    cursor: uploading ? "not-allowed" : "pointer",
                    fontSize: 14,
                  }}
                >
                  {uploading ? "กำลังอัปโหลด..." : "อัปโหลดไฟล์"}
                </button>

                {uploadMsg && (
                  <span style={{ color: "#16a34a", fontSize: 14 }}>
                    {uploadMsg}
                  </span>
                )}
                {uploadErr && (
                  <span style={{ color: "#dc2626", fontSize: 14 }}>
                    {uploadErr}
                  </span>
                )}
              </div>
            </form>
          )}
        </section>

        {/* Upload history */}
        <section style={{ marginTop: 16, padding: 12, border: "1px solid #ddd", borderRadius: 8, background: "#fff" }}>
          <h2 className={styles.sectionTitle}>Upload History</h2>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 8, flexWrap: "wrap" }}>
            <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 14, color: "#374151" }}>
              กรองตาม Collection
              <div style={{ display: "flex", gap: 8 }}>
                <select
                  value={historyFilter}
                  onChange={(e) => setHistoryFilter(e.target.value)}
                  style={{
                    padding: "8px 10px",
                    border: "1px solid #d1d5db",
                    borderRadius: 6,
                    background: "#fff",
                    fontSize: 14,
                    minWidth: 220,
                  }}
                >
                  <option value="">ทั้งหมด</option>
                  {collections.map((c) => (
                    <option key={c.id} value={c.name}>
                      {c.name} (dim: {c.dim})
                    </option>
                  ))}
                </select>

                <button
                  onClick={() => fetchUploadHistory(historyFilter)}
                  style={{
                    padding: "8px 14px",
                    border: "none",
                    borderRadius: 6,
                    background: "#6366f1",
                    color: "#fff",
                    cursor: "pointer",
                    fontSize: 14,
                  }}
                >
                  รีเฟรช
                </button>
              </div>
            </label>
          </div>
          {historyLoading ? (
            <p style={{ marginTop: 12 }}>กำลังโหลดประวัติ…</p>
          ) : historyError ? (
            <p style={{ marginTop: 12, color: "#dc2626" }}>{historyError}</p>
          ) : uploadHistory.length === 0 ? (
            <p style={{ marginTop: 12, color: "#6b7280" }}>ยังไม่มีข้อมูลอัปโหลด</p>
          ) : (
            <div
              style={{
                marginTop: 16,
                padding: 12,
                border: "1px solid #ddd",
                borderRadius: 8,
                background: "#fff",
                overflowX: "auto",
              }}
            >
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: "14px",
                }}
              >
                <thead>
                  <tr style={{ background: "#f9fafb" }}>
                    <th style={{ padding: "8px 10px", borderBottom: "1px solid #e5e7eb", textAlign: "left" }}>Upload ID</th>
                    <th style={{ padding: "8px 10px", borderBottom: "1px solid #e5e7eb", textAlign: "left" }}>Collection</th>
                    <th style={{ padding: "8px 10px", borderBottom: "1px solid #e5e7eb", textAlign: "left" }}>Filename</th>
                    <th style={{ padding: "8px 10px", borderBottom: "1px solid #e5e7eb", textAlign: "left" }}>Timestamp</th>
                    <th style={{ padding: "8px 10px", borderBottom: "1px solid #e5e7eb", textAlign: "left" }}>Chunks</th>
                    <th style={{ padding: "8px 10px", borderBottom: "1px solid #e5e7eb", textAlign: "left" }}></th>
                  </tr>
                </thead>
                <tbody>
                  {uploadHistory.map((u) => (
                    <tr key={`${u.upload_id}-${u.timestamp}`} style={{ borderBottom: "1px solid #e5e7eb" }}>
                      <td style={{ padding: "8px 10px", fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}>
                        {u.upload_id}
                      </td>
                      <td style={{ padding: "8px 10px" }}>{u.collection}</td>
                      <td style={{ padding: "8px 10px" }}>{u.filename}</td>
                      <td style={{ padding: "8px 10px" }}>
                        {u.timestamp ? new Date(u.timestamp).toLocaleString() : "-"}
                      </td>
                      <td style={{ padding: "8px 10px" }}>{u.count}</td>
                      <td style={{ padding: "8px 10px" }}>
                        <button
                          onClick={() => handleDeleteUpload(u.upload_id)}
                          disabled={deleteBusyId === u.upload_id}
                          style={{
                            padding: "4px 8px",
                            border: "none",
                            borderRadius: "4px",
                            background: deleteBusyId === u.upload_id ? "#9ca3af" : "#ef4444",
                            color: "#fff",
                            cursor: deleteBusyId === u.upload_id ? "not-allowed" : "pointer",
                            fontSize: "13px",
                          }}
                        >
                          {deleteBusyId === u.upload_id ? "กำลังลบ..." : "Delete"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
