"use client";

import { useEffect, useState, useMemo, useRef } from "react";
import Navbar from "../Component/nav";
import { LogoutButton } from "../Component/logout";
import styles from "./page.module.css";

export default function Home() {
  const API = process.env.NEXT_PUBLIC_API_URL;
  const [tools, setTools] = useState({});
  const [loadingTools, setLoadingTools] = useState(true);

  const [intents, setIntents] = useState([]);
  const [loadingIntents, setLoadingIntents] = useState(true);
  const [errIntents, setErrIntents] = useState("");

  const [phrase, setPhrase] = useState([]);
  const [loadingPhrase, setLoadingPhrase] = useState(true);
  const [errPhrase, setErrPhrase] = useState("");

  const [showAdd, setShowAdd] = useState(false);
  const [nameI, setNameI] = useState("");
  const [toolI, setToolI] = useState("");
  const [descI, setDescI] = useState("");

  const [showDel, setShowDel] = useState(false);
  const [delId, setDelId] = useState("");

  const [showAddTP, setShowAddTP] = useState(false);
  const [tpIntentId, setTpIntentId] = useState("");
  const [tpText, setTpText] = useState("");
  const [tpLoading, setTpLoading] = useState(false);
  const [tpErr, setTpErr] = useState("");

  const dlgRef = useRef(null);
  useEffect(() => {
    if (!dlgRef.current) return;
    if (showAdd) dlgRef.current.showModal();
    else dlgRef.current.close();
  }, [showAdd]);

  useEffect(() => {
    (async () => {
      try {
        const resp = await fetch(`${API}/admin/tools-in-server`);
        const data = await resp.json();
        setTools(data.available_tools || {});
      } catch (e) {
        console.error("โหลด tools ไม่สำเร็จ", e);
      } finally {
        setLoadingTools(false);
      }
    })();

    (async () => {
      try {
        const resp = await fetch(`${API}/admin/intents`, {
          headers: { Accept: "application/json" },
        });
        if (!resp.ok) {
          const j = await resp.json().catch(() => ({}));
          throw new Error(j.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        if (Array.isArray(data)) {
          setIntents(data);
        } else {
          setIntents([]);
          setErrIntents(typeof data === "string" ? data : "No data");
        }
      } catch (e) {
        setErrIntents(e.message || "โหลด intents ไม่สำเร็จ");
      } finally {
        setLoadingIntents(false);
      }
    })();

    (async () => {
      try {
        const resp = await fetch(`${API}/admin/training-phrases`, {
          headers: { Accept: "application/json" },
        });
        if (!resp.ok) {
          const p = await resp.json().catch(() => ({}));
          throw new Error(p.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        if (Array.isArray(data)) {
          setPhrase(data);
        } else {
          setPhrase([]);
          setErrPhrase(typeof data === "string" ? data : "No data");
        }
      } catch (e) {
        setErrPhrase(e.message || "โหลด Phrase ไม่สำเร็จ");
      } finally {
        setLoadingPhrase(false);
      }
    })();
  }, [API]);

  const toolByIntentId = useMemo(() => {
    const m = {};
    for (const it of intents) {
      m[it.intent_id] = it.tool_name || "";
    }
    return m;
  }, [intents]);

  const delDlgRef = useRef(null);
  useEffect(() => {
    if (!delDlgRef.current) return;
    showDel ? delDlgRef.current.showModal() : delDlgRef.current.close();
  }, [showDel]);

  //Add Training Phrases
  const addTPDlgRef = useRef(null);
  useEffect(() => {
    if (!addTPDlgRef.current) return;
    showAddTP ? addTPDlgRef.current.showModal() : addTPDlgRef.current.close();
  }, [showAddTP]);

  async function addIntent(e) {
    e.preventDefault();
    const qs = new URLSearchParams({
      name: nameI.trim(),
      tool_name: toolI.trim(),
      description: descI.trim(),
    }).toString();

    const resp = await fetch(`${API}/admin/create-intents?${qs}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ name: nameI, tool_name: toolI, description: descI }),
    });

    if (!resp.ok) {
      alert("สร้าง intent ไม่สำเร็จ");
      return;
    }
    const data = await resp.json();
    setIntents((prev) => [data, ...prev]);

    setNameI("");
    setToolI("");
    setDescI("");
    setShowAdd(false);
  }

  async function deleteSelectedIntent(e) {
    e.preventDefault();
    const id = Number(delId);
    if (!Number.isInteger(id)) {
      alert("กรุณาเลือก ID ให้ถูกต้อง");
      return;
    }

    if (!confirm(`ยืนยันลบ intent #${id}?`)) return;

    const resp = await fetch(`${API}/admin/delete-intents/${id}`, {
      method: "DELETE",
      credentials: "include",
      headers: { Accept: "application/json" },
    });

    const j = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      alert(j.detail || "ลบไม่สำเร็จ");
      return;
    }

    setIntents((prev) => prev.filter((it) => it.intent_id !== id));
    setDelId("");
    setShowDel(false);
  }

  async function addTrainingPhrases(e) {
    e.preventDefault();
    setTpErr("");
    const id = Number(tpIntentId);
    if (!Number.isInteger(id)) {
      setTpErr("กรุณาเลือก intent_id ให้ถูกต้อง");
      return;
    }

    const lines = tpText
      .split("\n")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    if (lines.length === 0) {
      setTpErr("กรุณาใส่ phrase อย่างน้อย 1 บรรทัด");
      return;
    }

    setTpLoading(true);
    let failCount = 0;
    const createdRows = [];

    for (const line of lines) {
      try {
        const qs = new URLSearchParams({
          intent_id: String(id),
          phrase: line,
        }).toString();

        const resp = await fetch(`${API}/admin/create-training-phrases?${qs}`, {
          method: "POST",
          headers: { Accept: "application/json" },
          credentials: "include",
        });

        const data = await resp.json().catch(() => ({}));
        if (!resp.ok || !data || typeof data !== "object" || data.tp_id == null) {
          failCount += 1;
          continue;
        }
        createdRows.push(data);
      } catch {
        failCount += 1;
      }
    }

    if (createdRows.length > 0) {
      setPhrase((prev) => [...createdRows, ...prev]);
    }

    setTpLoading(false);

    if (failCount > 0 && createdRows.length === 0) {
      setTpErr("เพิ่มไม่สำเร็จทุกบรรทัด");
      return;
    }
    if (failCount > 0) {
      setTpErr(`เพิ่มสำเร็จ ${createdRows.length} บรรทัด / ล้มเหลว ${failCount} บรรทัด`);
    } else {
      setShowAddTP(false);
      setTpIntentId("");
      setTpText("");
    }
  }

  return (
    <div className={styles.layout}>
      <Navbar />
      <main className={styles.main}>
        <div className={styles.header}>
          <h1 className={styles.title}>Tools in Server</h1>
          <LogoutButton>Logout</LogoutButton>
        </div>

        {/* -------- Tools Section -------- */}
        {loadingTools ? (
          <p>กำลังโหลด tools...</p>
        ) : (
          <table style={{ marginTop: 8, borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th style={{ borderBottom: "1px solid #ccc", textAlign: "left", padding: 8 }}>Tool name</th>
                {/* <th style={{ borderBottom: "1px solid #ccc", textAlign: "left", padding: 8 }}>Parameter</th> */}
                <th style={{ borderBottom: "1px solid #ccc", textAlign: "left", padding: 8 }}>Description</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(tools).map(([name, info]) => (
                <tr key={name}>
                  <td style={{ borderBottom: "1px solid #eee", padding: 8 }}>{name}</td>
                  {/* <td style={{ borderBottom: "1px solid #eee", padding: 8 }}>{info.parameter}</td> */}
                  <td style={{ borderBottom: "1px solid #eee", padding: 8 }}>{info.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* -------- Intents Section -------- */}
        <h2 style={{ marginTop: 24 }}>Intents</h2>
        <button onClick={() => setShowAdd(true)}>Add Intent</button>
        <button
          style={{ marginLeft: 5 }}
          onClick={() => setShowDel(true)}
          disabled={!intents || intents.length === 0}
        >
          Delete Intent
        </button>

        {/* -------- Intents Pop-up -------- */}
        <dialog ref={dlgRef} onClose={() => setShowAdd(false)} style={{ padding: 16, borderRadius: 12 }}>
          <form onSubmit={addIntent} style={{ display: "grid", gap: 8, minWidth: 320 }}>
            <h3 style={{ marginBottom: 6 }}>Add Intent</h3>

            <label>
              <div>Intent Name</div>
              <select
                value={nameI}
                onChange={(e) => {
                  const v = e.target.value;
                  setNameI(v);
                  setToolI(v);
                }}
                required
                disabled={!tools || Object.keys(tools).length === 0}
                style={{ width: "100%", padding: 8, border: "1px solid " + "#ddd", borderRadius: 8 }}
              >
                <option value="" disabled>
                  -- เลือกจาก Tool Name --
                </option>
                {Object.keys(tools || {}).map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              {(!tools || Object.keys(tools).length === 0) && (
                <small style={{ color: "#888" }}>ยังไม่มี tools ให้เลือก</small>
              )}
            </label>

            <label>
              <div>Tool Name</div>
              <select
                value={toolI}
                onChange={(e) => setToolI(e.target.value)}
                required
                disabled={!tools || Object.keys(tools).length === 0}
                style={{ width: "100%", padding: 8, border: "1px solid " + "#ddd", borderRadius: 8 }}
              >
                <option value="" disabled>
                  -- เลือกเครื่องมือ --
                </option>
                {Object.keys(tools || {}).map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              {(!tools || Object.keys(tools).length === 0) && (
                <small style={{ color: "#888" }}>ยังไม่มี tools ให้เลือก</small>
              )}
            </label>

            <label>
              <div>Description</div>
              <textarea rows={3} value={descI} onChange={(e) => setDescI(e.target.value)} />
            </label>

            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 8 }}>
              <button type="submit">Save</button>
              <button type="button" onClick={() => setShowAdd(false)}>
                Cancel
              </button>
            </div>
          </form>
        </dialog>

        <dialog ref={delDlgRef} onClose={() => setShowDel(false)} style={{ padding: 16, borderRadius: 12 }}>
          <form onSubmit={deleteSelectedIntent} style={{ display: "grid", gap: 10, minWidth: 320 }}>
            <h3 style={{ marginBottom: 6 }}>Delete Intent</h3>

            <label>
              <div>เลือก ID ที่ต้องการลบ</div>
              <select
                value={delId}
                onChange={(e) => setDelId(e.target.value)}
                required
                style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 8 }}
              >
                <option value="" disabled>
                  -- เลือก intent_id --
                </option>
                {intents.map((it) => (
                  <option key={it.intent_id} value={it.intent_id}>
                    #{it.intent_id} — {it.name} ({it.tool_name})
                  </option>
                ))}
              </select>
            </label>

            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 4 }}>
              <button type="submit">Delete</button>
              <button type="button" onClick={() => setShowDel(false)}>
                Cancel
              </button>
            </div>
          </form>
        </dialog>

        {loadingIntents ? (
          <p>กำลังโหลด intents...</p>
        ) : errIntents ? (
          <div style={{ color: "crimson", marginTop: 8 }}>{errIntents}</div>
        ) : (
          <table style={{ marginTop: 8, borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th style={{ borderBottom: "1px solid #ccc", textAlign: "left", padding: 8 }}>intent_id</th>
                <th style={{ borderBottom: "1px solid #ccc", textAlign: "left", padding: 8 }}>name</th>
                <th style={{ borderBottom: "1px solid #ccc", textAlign: "left", padding: 8 }}>description</th>
                <th style={{ borderBottom: "1px solid #ccc", textAlign: "left", padding: 8 }}>tool_name</th>
              </tr>
            </thead>
            <tbody>
              {intents.length === 0 ? (
                <tr>
                  <td colSpan={4} style={{ padding: 8 }}>
                    ไม่พบข้อมูล
                  </td>
                </tr>
              ) : (
                intents.map((it) => (
                  <tr key={it.intent_id}>
                    <td style={{ borderBottom: "1px solid #eee", padding: 8 }}>{it.intent_id}</td>
                    <td style={{ borderBottom: "1px solid #eee", padding: 8 }}>{it.name}</td>
                    <td style={{ borderBottom: "1px solid #eee", padding: 8 }}>{it.description}</td>
                    <td style={{ borderBottom: "1px solid #eee", padding: 8 }}>{it.tool_name}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}

        {/* -------- Training phrases Section -------- */}
        <h2 style={{ marginTop: 24 }}>Phrase</h2>

        <button onClick={() => setShowAddTP(true)} disabled={intents.length === 0}>
          Add Training phrases
        </button>
        <button style={{ marginLeft: 5 }}>Delete Training phrases</button>

        {/* Training Phrases Pop-up */}
        <dialog ref={addTPDlgRef} onClose={() => setShowAddTP(false)} style={{ padding: 16, borderRadius: 12 }}>
          <form onSubmit={addTrainingPhrases} style={{ display: "grid", gap: 8, minWidth: 360 }}>
            <h3 style={{ marginBottom: 6 }}>Add Training Phrases</h3>

            <label>
              <div>เลือก Intent</div>
              <select
                value={tpIntentId}
                onChange={(e) => setTpIntentId(e.target.value)}
                required
                style={{ width: "100%", padding: 8, border: "1px solid #ddd", borderRadius: 8 }}
              >
                <option value="" disabled>
                  -- เลือก intent_id --
                </option>
                {intents.map((it) => (
                  <option key={it.intent_id} value={it.intent_id}>
                    #{it.intent_id} — {it.name} ({it.tool_name})
                  </option>
                ))}
              </select>
            </label>

            <label>
              <div>Phrase (รองรับหลายบรรทัด)</div>
              <textarea
                rows={5}
                value={tpText}
                onChange={(e) => setTpText(e.target.value)}
                required
              />
            </label>

            {tpErr && <div style={{ color: "crimson" }}>{tpErr}</div>}

            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 8 }}>
              <button type="submit" disabled={tpLoading}>
                {tpLoading ? "Saving..." : "Save"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowAddTP(false);
                  setTpErr("");
                }}
                disabled={tpLoading}
              >
                Cancel
              </button>
            </div>
          </form>
        </dialog>

        {loadingPhrase ? (
          <p>กำลังโหลด Phrase...</p>
        ) : errPhrase ? (
          <div style={{ color: "crimson", marginTop: 8 }}>{errPhrase}</div>
        ) : (
          <table style={{ marginTop: 8, borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                {/* <th style={{ borderBottom: "1px solid #ccc", textAlign: "left", padding: 8 }}>tp_id</th>
                <th style={{ borderBottom: "1px solid #ccc", textAlign: "left", padding: 8 }}>intent_id</th> */}
                <th style={{ borderBottom: "1px solid #ccc", textAlign: "left", padding: 8 }}>tool_name</th>
                <th style={{ borderBottom: "1px solid #ccc", textAlign: "left", padding: 8 }}>Phrase</th>
              </tr>
            </thead>
            <tbody>
              {phrase.length === 0 ? (
                <tr>
                  <td colSpan={4} style={{ padding: 8 }}>
                    ไม่พบข้อมูล
                  </td>
                </tr>
              ) : (
                phrase.map((it) => (
                  <tr key={it.tp_id}>
                    {/* <td style={{ borderBottom: "1px solid #eee", padding: 8 }}>{it.tp_id}</td>
                    <td style={{ borderBottom: "1px solid #eee", padding: 8 }}>{it.intent_id}</td> */}
                    <td style={{ borderBottom: "1px solid #eee", padding: 8 }}>
                      {toolByIntentId[it.intent_id] || "-"}
                    </td>
                    <td style={{ borderBottom: "1px solid #eee", padding: 8 }}>{it.phrase}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </main>
    </div>
  );
}
