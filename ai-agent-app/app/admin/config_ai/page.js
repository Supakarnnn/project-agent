"use client";

import { useEffect, useState } from "react";
import Navbar from "../Component/nav";
import { LogoutButton } from "../Component/logout";
import styles from "./page.module.css";

export default function ConfigAI() {
  const API = process.env.NEXT_PUBLIC_API_URL;

  const [model, setModel] = useState("");
  const [temperature, setTemperature] = useState();
  const [topP, setTopP] = useState();
  const [systemPrompt, setSystemPrompt] = useState("");

  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [currentConfig, setCurrentConfig] = useState(null);

  async function save(e) {
    e.preventDefault();
    setMsg("");
    setErr("");
    try {
      const r = await fetch(`${API}/admin/update-config`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: model.trim(),
          temperature: Number(temperature),
          top_p: Number(topP),
          system_prompt: systemPrompt,
        }),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(j.detail || j.message || "บันทึกไม่สำเร็จ");
      setMsg(j.message || "บันทึกแล้ว");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "บันทึกไม่สำเร็จ");
    }
  }

  useEffect(() => {
    let cancelled = false;
    setMsg("");
    setErr("");

    (async () => {
      try {
        const r = await fetch(`${API}/admin/config`, { credentials: "include" });
        const j = await r.json();
        if (!j || !j.model) throw new Error("ไม่พบ config");
        if (cancelled) return;
        setCurrentConfig(j);
        setMsg("Current AI config");
      } catch (e) {
        if (!cancelled) setErr(e instanceof Error ? e.message : "ทดสอบไม่สำเร็จ");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [API]); // พึ่งพาเฉพาะ API

  return (
    <div className={styles.layout}>
      <Navbar />
      <main className={styles.main}>
        <div className={styles.header}>
          <h1 className={styles.title}>Config AI</h1>
          <LogoutButton>Logout</LogoutButton>
        </div>

        {msg && <div style={{ marginTop: 10, color: "green" }}>{msg}</div>}
        {err && <div style={{ marginTop: 10, color: "red" }}>{err}</div>}

        {currentConfig && (
          <div style={{ marginTop: 16, padding: 12, border: "1px solid #ddd", borderRadius: 8, background: "#fff" }}>
            <h3>Current AI config</h3>
            <p><b>Model:</b> {currentConfig.model}</p>
            <p><b>Temperature:</b> {currentConfig.temperature}</p>
            <p><b>Top P:</b> {currentConfig.top_p}</p>
            <p><b>System Prompt:</b></p>
            <pre style={{ whiteSpace: "pre-wrap", background: "#f7fafc", padding: 8, borderRadius: 4 }}>
              {currentConfig.system_prompt}
            </pre>
          </div>
        )}

        <form id="configForm" onSubmit={save} style={{ display: "grid", gap: 12, maxWidth: 600, marginTop: 16 }}>
          <label>
            <div>Model</div>
            <select name="model" value={model} onChange={(e) => setModel(e.target.value)} style={{ width: "100%", padding: 6 }}>
              <option value="gpt-4o-mini">gpt-4o-mini</option>
              <option value="gpt-4.1-nano">gpt-4.1-nano</option>
            </select>
          </label>

          <label>
            <div>Temperature (0-2) (ค่าน้อย = ตอบตรง, ค่าสูง = ตอบสร้างสรรค์)</div>
            <input
              type="number"
              step="0.01"
              placeholder="0.2"
              min={0}
              max={2}
              value={temperature ?? ""}
              onChange={(e) => setTemperature(e.target.value)}
              style={{ width: 200, padding: 6 }}
            />
          </label>

          <label>
            <div>Top P (0-1) (ค่าน้อย = ตอบจำกัด, ค่าสูง = ตอบกว้าง)</div>
            <input
              type="number"
              step="0.01"
              placeholder="0"
              min={0}
              max={1}
              value={topP ?? ""}
              onChange={(e) => setTopP(e.target.value)}
              style={{ width: 200, padding: 6 }}
            />
          </label>

          <label>
            <div>System Prompt (คำสั่งเริ่มต้นของระบบ / บทบาทหรือบุคลิก ของ AI)</div>
            <textarea
              rows={6}
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="ใส่ system prompt ที่นี่"
              style={{ width: "100%", padding: 6 }}
            />
          </label>
          <div style={{ display: "flex", gap: 8 }}>
            <button type="submit" form="configForm">Save</button>
          </div>
        </form>
      </main>
    </div>
  );
}
