"use client";

import { useState } from "react";
import styles from "./page.module.css";

export default function Home() {
    const [orderCode, setOrderCode] = useState("");
    const [orderData, setOrderData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const handleCheckPayment = async () => {
        if (!orderCode.trim()) return;

        setLoading(true);
        setError("");
        setOrderData(null);

        try {
            const res = await fetch(
                "https://crm-a02.protollcall.com/aichat/webservice.php/getso",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + process.env.NEXT_PUBLIC_CRM_TOKEN,
                    },
                    body: JSON.stringify({
                        code: orderCode.trim(),
                    }),
                }
            );

            const json = await res.json().catch(() => null);

            if (!res.ok) {
                const msg =
                    json?.detail || json?.message || `เกิดข้อผิดพลาด (code ${res.status})`;
                throw new Error(msg);
            }

            if (!json?.success) {
                const msg = json?.message || "ไม่พบข้อมูลคำสั่งซื้อ หรือระบบตอบกลับไม่ถูกต้อง";
                throw new Error(msg);
            }

            setOrderData(json.value || null);
        } catch (err) {
            setError(err?.message || "เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์");
        } finally {
            setLoading(false);
        }
    };

    const handleConfirmPayment = async () => {
        if (!orderData?.code) return;

        try {
            const res = await fetch(process.env.NEXT_PUBLIC_CRM_API_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + process.env.NEXT_PUBLIC_CRM_TOKEN,
                },
                body: JSON.stringify({
                    code: orderData.code,
                    status: "ชำระเงินแล้ว",
                }),
            });

            const json = await res.json();

            if (!res.ok) {
                throw new Error(json?.message || "อัปเดตสถานะไม่สำเร็จ");
            }

            setOrderData((prev) => ({
                ...prev,
                postatus: json.status || "ชำระเงินแล้ว",
            }));

            alert("ยืนยันการชำระเงินสำเร็จ!");
        } catch (err) {
            console.error(err);
            alert("เกิดข้อผิดพลาดระหว่างยืนยันการชำระเงิน");
        }
    };

    const formatCurrency = (amount) => {
        return new Intl.NumberFormat("th-TH", {
            style: "currency",
            currency: "THB",
        }).format(amount);
    };

    return (
        <div className={styles.page}>
            {/* Top Nav */}
            <header className={styles.nav}>
                <div className={styles.logo}>HealthCare++</div>
                <nav className={styles.navLinks}>
                    <a href="/payment">Payment</a>
                    <a href="#whyus">Why Us</a>
                    <a href="#faq">FAQ</a>
                </nav>
            </header>

            {/* Main content */}
            <main className={styles.main}>
                <section className={styles.card}>
                    <h1 className={styles.title}>ชำระเงินคำสั่งซื้อ</h1>
                    <p className={styles.subtitle}>
                        กรุณากรอกหมายเลขคำสั่งซื้อของคุณ เพื่อดำเนินการตรวจสอบสถานะ
                    </p>

                    <div className={styles.formRow}>
                        <label className={styles.label} htmlFor="orderCode">
                            หมายเลขคำสั่งซื้อ
                        </label>
                        <input
                            id="orderCode"
                            type="text"
                            className={styles.input}
                            placeholder="เช่น SO20251202-001"
                            value={orderCode}
                            onChange={(e) => setOrderCode(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleCheckPayment()}
                        />
                    </div>

                    <button
                        className={styles.primaryButton}
                        type="button"
                        onClick={handleCheckPayment}
                        disabled={!orderCode.trim() || loading}
                    >
                        {loading ? "กำลังตรวจสอบ..." : "ตรวจสอบสถานะ"}
                    </button>

                    {error && <div className={styles.errorBox}>{error}</div>}

                    {orderData && (
                        <OrderDetailSection
                            orderData={orderData}
                            onConfirm={handleConfirmPayment}
                            formatCurrency={formatCurrency}
                            styles={styles}
                        />
                    )}
                </section>
            </main>

            {/* Footer */}
            <footer className={styles.footer}>
                <div>© {new Date().getFullYear()} HealthCare++ Shop</div>
                <div className={styles.footerLinks}>
                    <a href="#">Privacy</a>
                    <a href="#">Terms</a>
                    <a href="#">Contact</a>
                </div>
            </footer>
        </div>
    );
}

function OrderDetailSection({ orderData, onConfirm, formatCurrency, styles }) {
    const isPending = orderData.postatus === "รอชำระเงิน";
    const shipping = Number(orderData.shipping ?? 0);
    const payAmount = Number(orderData.pay_amount ?? 0);
    const total = shipping + payAmount;

    // Check if status implies success/paid
    const isPaid = orderData.postatus === "ชำระเงินแล้ว" || orderData.postatus === "Completed";
    const statusColor = isPending ? "#d97706" : isPaid ? "#059669" : "#2563eb";

    return (
        <section className={styles.resultCard}>
            <h2 className={styles.resultTitle}>
                {isPending ? "รายละเอียดคำสั่งซื้อ (รอชำระเงิน)" : "รายละเอียดคำสั่งซื้อ"}
            </h2>

            <div className={styles.resultGrid}>
                <div className={styles.resultRow}>
                    <span className={styles.resultLabel}>ชื่อลูกค้า</span>
                    <span className={styles.resultValue}>{orderData.name}</span>
                </div>
                <div className={styles.resultRow}>
                    <span className={styles.resultLabel}>เบอร์โทร</span>
                    <span className={styles.resultValue}>{orderData.tel}</span>
                </div>
                <div className={styles.resultRow}>
                    <span className={styles.resultLabel}>หมายเลขคำสั่งซื้อ</span>
                    <span className={styles.resultValue}>{orderData.code}</span>
                </div>
                <div className={styles.resultRow}>
                    <span className={styles.resultLabel}>สถานะ</span>
                    <span
                        className={styles.resultValue}
                        style={{ color: statusColor, fontWeight: 700 }}
                    >
                        {orderData.postatus}
                    </span>
                </div>

                <div className={styles.resultRowFull}>
                    <div style={{ height: '1px', background: '#e2e8f0', margin: '0.5rem 0' }} />
                </div>

                <div className={styles.resultRow}>
                    <span className={styles.resultLabel}>ค่าส่ง</span>
                    <span className={styles.resultValue}>{formatCurrency(shipping)}</span>
                </div>
                <div className={styles.resultRow}>
                    <span className={styles.resultLabel}>ส่วนลด</span>
                    <span className={styles.resultValue}>{orderData.discountdetail || "-"}</span>
                </div>
                <div className={styles.resultRowFull}>
                    <div className={styles.resultRow} style={{ alignItems: 'flex-end', marginTop: '0.5rem' }}>
                        <span className={styles.resultLabel} style={{ fontSize: '0.85rem' }}>ยอดชำระสุทธิ</span>
                        <span className={styles.resultValue} style={{ fontSize: '1.25rem', color: 'var(--primary)' }}>
                            {formatCurrency(payAmount)}
                        </span>
                    </div>
                </div>

                <div className={styles.resultRowFull}>
                    <div style={{ height: '1px', background: '#e2e8f0', margin: '0.5rem 0' }} />
                </div>

                <div className={styles.resultRowFull}>
                    <span className={styles.resultLabel}>ที่อยู่จัดส่ง</span>
                    <span className={styles.resultValue} style={{ lineHeight: '1.5' }}>
                        {orderData.address} {orderData.subdistrict} {orderData.district} {orderData.province} {orderData.zipcode}
                    </span>
                </div>
                <div className={styles.resultRow}>
                    <span className={styles.resultLabel}>เลขพัสดุ</span>
                    <span className={styles.resultValue}>{orderData.shipping_code || "-"}</span>
                </div>

                <div className={styles.resultRowFull}>
                    <span className={styles.resultLabel} style={{ marginTop: '0.5rem' }}>รายการสินค้า</span>
                    <div className={styles.productList}>
                        {Array.isArray(orderData.sodetail) &&
                            orderData.sodetail.map((item, idx) => (
                                <div key={idx} className={styles.productItem}>
                                    <div className={styles.productName}>{item.ProductName}</div>
                                    <div className={styles.productMeta}>
                                        {item.QTY} x {formatCurrency(item.PricePerUnit)}
                                    </div>
                                </div>
                            ))}
                    </div>
                </div>

                {/* Show QR Code ONLY if Pending */}
                {isPending && (
                    <div className={styles.resultRowFull}>
                        <span className={styles.resultLabel} style={{ marginTop: '1rem', textAlign: 'center' }}>
                            สแกน QR Code เพื่อชำระเงิน
                        </span>
                        <div className={styles.imageCenter}>
                            <img
                                className={styles.paymentImage}
                                src="/payment_oo.jpg"
                                alt="payment QR"
                            />
                        </div>
                        <div className={styles.confirmWrapper}>
                            <button
                                type="button"
                                className={styles.confirmButton}
                                onClick={onConfirm}
                            >
                                แจ้งชำระเงินเรียบร้อยแล้ว
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </section>
    );
}
