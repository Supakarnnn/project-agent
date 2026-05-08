"use client";

import { useState } from "react";
import Navbar from "../Component/nav";
import { LogoutButton } from "../Component/logout";
import styles from "./page.module.css";
import SingleProductForm from "./single";
import BulkProductUpload from "./bulk";

export default function Add_new_product() {
    const [mode, setMode] = useState(null);

    if (mode === "single") {
        return <SingleProductForm onBack={() => setMode(null)} />;
    }

    if (mode === "bulk") {
        return <BulkProductUpload onBack={() => setMode(null)} />;
    }

    return (
        <div className={styles.layout}>
            <Navbar />
            <main className={styles.main}>
                <div className={styles.header}>
                    <div>
                        <h1 className={styles.title}>Add Product</h1>
                        <p className={styles.subtitle}>เลือกวิธีการเพิ่มสินค้า</p>
                    </div>
                    <LogoutButton>Logout</LogoutButton>
                </div>

                <div className={styles.modeSelector}>
                    <button className={styles.modeCard} onClick={() => setMode("single")}>
                        <div className={styles.modeIcon}>
                            <svg width="32" height="32" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                                    d="M20 7H4a2 2 0 00-2 2v6a2 2 0 002 2h16a2 2 0 002-2V9a2 2 0 00-2-2z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 12h.01" />
                            </svg>
                        </div>
                        <div className={styles.modeLabel}>เพิ่มทีละชิ้น</div>
                        <div className={styles.modeDesc}>กรอกข้อมูลเอง หรือ extract จากไฟล์ (pdf, txt) หรือ google docs</div>
                        <div className={styles.modeArrow}>→</div>
                    </button>

                    <div className={styles.modeDivider}>
                        <span>หรือ</span>
                    </div>

                    <button className={`${styles.modeCard} ${styles.modeCardBulk}`} onClick={() => setMode("bulk")}>
                        <div className={styles.modeIcon}>
                            <svg width="32" height="32" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                                    d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                        </div>
                        <div className={styles.modeLabel}>เพิ่มหลายชิ้น (Bulk)</div>
                        <div className={styles.modeDesc}>นำเข้าจากไฟล์ .xlsx เท่านั้น</div>
                        <div className={styles.modeArrow}>→</div>
                    </button>
                </div>
            </main>
        </div>
    );
}