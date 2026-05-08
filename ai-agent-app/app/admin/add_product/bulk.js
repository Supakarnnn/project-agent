"use client";

import { useState, useCallback, useRef } from "react";
import * as XLSX from "xlsx";
import Navbar from "../Component/nav";
import { LogoutButton } from "../Component/logout";
import styles from "./page.module.css";

const REQUIRED_COLUMNS = [
    "name", "name_eng", "cost", "detail", "brand",
    "category_l1", "category_l2", "key_features", "key_ingredients",
    "suitable_for_concern", "size_volume", "usage_instructions", "notes"
];

const COL_LABELS = {
    name: "ชื่อ (TH)", name_eng: "ชื่อ (EN)", cost: "ราคา", detail: "รายละเอียด",
    brand: "แบรนด์", category_l1: "หมวด 1", category_l2: "หมวด 2",
    key_features: "คุณสมบัติ", key_ingredients: "ส่วนผสม",
    suitable_for_concern: "เหมาะสำหรับ", size_volume: "ขนาด",
    usage_instructions: "วิธีใช้", notes: "หมายเหตุ",
};

export default function BulkProductUpload({ onBack }) {
    const API = process.env.NEXT_PUBLIC_API_URL;
    const [products, setProducts] = useState([]);
    const [parseErrors, setParseErrors] = useState([]);
    const [fileName, setFileName] = useState("");
    const [step, setStep] = useState("upload");
    const [results, setResults] = useState([]);
    const [expandedRow, setExpandedRow] = useState(null);
    const [isDragging, setIsDragging] = useState(false);
    const fileRef = useRef();

    const parseFile = (file) => {
        if (!file.name.endsWith(".xlsx")) {
            setParseErrors(["รองรับเฉพาะไฟล์ .xlsx เท่านั้น"]);
            return;
        }
        const reader = new FileReader();
        reader.onload = (e) => {
            const wb = XLSX.read(e.target.result, { type: "binary" });
            const ws = wb.Sheets[wb.SheetNames[0]];
            const raw = XLSX.utils.sheet_to_json(ws, { defval: "" });
            if (raw.length === 0) { setParseErrors(["ไฟล์ไม่มีข้อมูล"]); return; }
            const missing = REQUIRED_COLUMNS.filter(c => !Object.keys(raw[0]).includes(c));
            if (missing.length > 0) { setParseErrors([`Column ที่หายไป: ${missing.join(", ")}`]); return; }
            const rowErrors = [];
            raw.forEach((row, i) => {
                if (!row.name) rowErrors.push(`แถว ${i + 2}: ไม่มีชื่อสินค้า`);
                if (!row.cost || isNaN(Number(row.cost))) rowErrors.push(`แถว ${i + 2}: ราคาไม่ถูกต้อง`);
            });
            if (rowErrors.length > 0) { setParseErrors(rowErrors); return; }
            setParseErrors([]);
            setProducts(raw.map((r, i) => ({ ...r, _id: i })));
            setFileName(file.name);
            setStep("preview");
        };
        reader.readAsBinaryString(file);
    };

    const handleDrop = useCallback((e) => {
        e.preventDefault(); setIsDragging(false);
        const file = e.dataTransfer.files[0];
        if (file) parseFile(file);
    }, []);

    const handleFile = (e) => { const file = e.target.files[0]; if (file) parseFile(file); };

    const handleSubmit = async () => {
        if (step === "uploading") return;
        setStep("uploading");

        try {
            const resp = await fetch(`${API}/admin/bulk_add_products`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(products.map(({ _id, ...p }) => ({
                    ...p,
                    cost: Number(p.cost),
                    stock_qty: Number(p.stock_qty || 0),
                }))),
            });

            const json = await resp.json();

            if (!resp.ok) {
                alert(json.detail?.message || "เกิดข้อผิดพลาด");
                setStep("preview");
                return;
            }

            const res = products.map((p, i) => {
                const r = json.results?.[i];
                return {
                    _id: p._id,
                    name: p.name,
                    ok: r?.ok ?? false,
                    code: r?.code ?? null,
                    error: r?.ok ? null : "ล้มเหลว",
                };
            });

            setResults(res);
        } catch (err) {
            alert(`Network error: ${err.message}`);
            setStep("preview");
            return;
        }

        setStep("done");
    };

    const reset = () => { setStep("upload"); setProducts([]); setResults([]); setFileName(""); setParseErrors([]); setExpandedRow(null); };
    const successCount = results.filter(r => r.ok).length;
    const failCount = results.filter(r => !r.ok).length;

    return (
        <div className={styles.layout}>
            <Navbar />
            <main className={styles.main}>
                <div className={styles.header}>
                    <div>
                        <button className={styles.backBtn} onClick={step === "upload" ? onBack : reset}>
                            ← {step === "upload" ? "เลือกวิธีเพิ่มสินค้า" : "อัปโหลดไฟล์ใหม่"}
                        </button>
                        <h1 className={styles.title}>Bulk Import</h1>
                        <p className={styles.subtitle}>
                            {step === "upload" && "นำเข้าสินค้าจากไฟล์ .xlsx"}
                            {step === "preview" && `${fileName} — ${products.length} รายการ`}
                            {step === "uploading" && `กำลังนำเข้า ${results.length}/${products.length} รายการ...`}
                            {step === "done" && `เสร็จสิ้น — สำเร็จ ${successCount} / ล้มเหลว ${failCount}`}
                        </p>
                    </div>
                    <div className={styles.headerRight}>
                        <LogoutButton>Logout</LogoutButton>
                    </div>
                </div>

                {/* UPLOAD */}
                {step === "upload" && (
                    <div>
                        <div
                            className={`${styles.dropZone} ${styles.dropZoneLarge} ${isDragging ? styles.dragging : ""}`}
                            onDrop={handleDrop}
                            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                            onDragLeave={() => setIsDragging(false)}
                            onClick={() => fileRef.current.click()}
                        >
                            <input ref={fileRef} type="file" accept=".xlsx" className={styles.hiddenInput} onChange={handleFile} />
                            <div className={styles.dropZoneContent}>
                                <svg className={styles.uploadIcon} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                                <p className={styles.dropZoneText}>วางไฟล์ .xlsx ที่นี่</p>
                                <span className={styles.dropZoneSubtext}>หรือคลิกเพื่อเลือกไฟล์</span>
                            </div>
                        </div>

                        {parseErrors.length > 0 && (
                            <div className={styles.extractError} style={{ marginTop: 16 }}>
                                {parseErrors.map((e, i) => <div key={i}>⚠ {e}</div>)}
                            </div>
                        )}

                    </div>
                )}

                {/* PREVIEW */}
                {step === "preview" && (
                    <div className={styles.contentCard} style={{ padding: 0, overflow: "hidden" }}>
                        <div className={styles.bulkTable}>
                            <div className={styles.bulkTableHeader}>
                                <div className={styles.bulkColNum}>#</div>
                                <div className={styles.bulkColMain}>ชื่อสินค้า</div>
                                <div className={styles.bulkColMain}>ชื่อ EN</div>
                                <div className={styles.bulkColMuted}>ราคา</div>
                                <div className={styles.bulkColMuted}>แบรนด์</div>
                                <div className={styles.bulkColMuted}>หมวด 1</div>
                                <div className={styles.bulkColMuted}>หมวด 2</div>
                                <div className={styles.bulkColExpand}></div>
                            </div>

                            {products.map((p, i) => (
                                <div key={p._id}>
                                    <div className={`${styles.bulkTableRow} ${expandedRow === p._id ? styles.bulkRowExpanded : ""}`}>
                                        <div className={styles.bulkColNum}>{i + 1}</div>
                                        <div className={styles.bulkColMain} title={p.name}>{p.name}</div>
                                        <div className={`${styles.bulkColMain} ${styles.bulkColMuted}`} title={p.name_eng}>{p.name_eng}</div>
                                        <div className={styles.bulkColSm}><span className={styles.priceTag}>฿{Number(p.cost).toLocaleString()}</span></div>
                                        <div className={styles.bulkColSm}>{p.brand}</div>
                                        <div className={styles.bulkColSm}><span className={styles.catTag}>{p.category_l1}</span></div>
                                        <div className={styles.bulkColSm}><span className={`${styles.catTag} ${styles.catTagSub}`}>{p.category_l2}</span></div>
                                        <div className={styles.bulkColExpand}>
                                            <button className={styles.expandBtn} onClick={() => setExpandedRow(expandedRow === p._id ? null : p._id)}>
                                                {expandedRow === p._id ? "−" : "+"}
                                            </button>
                                        </div>
                                    </div>
                                    {expandedRow === p._id && (
                                        <div className={styles.bulkRowDetail}>
                                            {["detail", "key_features", "key_ingredients", "suitable_for_concern", "size_volume", "usage_instructions", "notes"].map(k => (
                                                <div key={k} className={`${styles.bulkDetailItem} ${["detail", "usage_instructions"].includes(k) ? styles.bulkDetailFull : ""}`}>
                                                    <div className={styles.bulkDetailLabel}>{COL_LABELS[k]}</div>
                                                    <div className={styles.bulkDetailValue}>{p[k] || <span className={styles.bulkColMuted}>—</span>}</div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* UPLOADING */}
                {step === "uploading" && (
                    <div className={styles.contentCard}>
                        <div className={styles.progressBar}>
                            <div className={styles.progressFill} style={{ width: `${(results.length / products.length) * 100}%` }} />
                        </div>
                        <div className={styles.uploadingList}>
                            {results.map((r, i) => (
                                <div key={r._id} className={styles.uploadingItem}>
                                    <span className={r.ok ? styles.statusOk : styles.statusFail}>{r.ok ? "✓" : "✗"}</span>
                                    <span className={styles.uploadingName}>{r.name}</span>
                                    {r.ok && <span className={styles.uploadingCode}>{r.code}</span>}
                                    {!r.ok && <span className={styles.uploadingError}>{r.error}</span>}
                                </div>
                            ))}
                            {results.length < products.length && (
                                <div className={styles.uploadingPending}>กำลังประมวลผล {results.length + 1}/{products.length}...</div>
                            )}
                        </div>
                    </div>
                )}

                {/* DONE */}
                {step === "done" && (
                    <div className={styles.contentCard}>
                        <div className={styles.doneSummary}>
                            <div className={styles.doneCount}>
                                <span className={styles.doneCountNum} style={{ color: "var(--color-success)" }}>{successCount}</span>
                                <span className={styles.doneCountLabel}>สำเร็จ</span>
                            </div>
                            {failCount > 0 && (
                                <div className={styles.doneCount}>
                                    <span className={styles.doneCountNum} style={{ color: "var(--color-danger)" }}>{failCount}</span>
                                    <span className={styles.doneCountLabel}>ล้มเหลว</span>
                                </div>
                            )}
                        </div>
                        <div className={styles.files}>
                            {results.map((r) => (
                                <div key={r._id} className={styles.fileItem}>
                                    <span className={r.ok ? styles.statusOk : styles.statusFail}>{r.ok ? "Yes" : "No"}</span>
                                    <span className={styles.fileName} style={{ color: r.ok ? undefined : "#e53e3e" }}>{r.name}</span>
                                    {r.ok && <span className={styles.uploadingCode}>{r.code || "OK"}</span>}
                                    {!r.ok && <span className={styles.uploadingError}>{r.error || "ERROR"}</span>}
                                </div>
                            ))}
                        </div>

                        <div className={styles.actions}>
                            <button className={styles.cancelBtn} onClick={onBack}>กลับหน้าหลัก</button>
                            <button className={styles.submitBtn} onClick={reset}>นำเข้าไฟล์ใหม่</button>
                        </div>
                    </div>
                )}

                <div className={styles.underactions}>
                    {step === "preview" && (
                        <button className={styles.submitBtn} onClick={handleSubmit}>
                            นำเข้าทั้งหมด {products.length} อย่าง
                        </button>
                    )}
                </div>

            </main>
        </div>
    );
}