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
                process.env.NEXT_PUBLIC_API_URL +
                `/check_payment?code=${encodeURIComponent(orderCode.trim())}`
            );
            const json = await res.json().catch(() => null);

            if (!res.ok) {
                const msg =
                    json?.detail || json?.message || `เกิดข้อผิดพลาด (code ${res.status})`;
                throw new Error(msg);
            }

            setOrderData(json.data || null);
        } catch (err) {
            setError(err.message || "เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์");
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

            console.log("API result:", json);

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
                        กรุณากรอกหมายเลขคำสั่งซื้อของคุณ เพื่อดำเนินการตรวจสอบการชำระเงิน
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
                        />
                    </div>

                    <button
                        className={styles.primaryButton}
                        type="button"
                        onClick={handleCheckPayment}
                        disabled={!orderCode.trim() || loading}
                    >
                        {loading ? "กำลังตรวจสอบ..." : "ตรวจสอบการชำระเงิน"}
                    </button>

                    {error && <div className={styles.errorBox}>{error}</div>}

                    {orderData &&
                        (() => {
                            const isPending = orderData.postatus === "รอชำระเงิน";

                            const shipping = Number(orderData.shipping ?? 0);
                            const payAmount = Number(orderData.pay_amount ?? 0);
                            const total = shipping + payAmount;

                            if (isPending) {
                                return (
                                    <section className={styles.resultCard}>
                                        <h2 className={styles.resultTitle}>
                                            รายละเอียดคำสั่งซื้อ (รอชำระเงิน)
                                        </h2>
                                        <div className={styles.resultGrid}>
                                            <div className={styles.resultRow}>
                                                <span className={styles.resultLabel}>ชื่อลูกค้า</span>
                                                <span className={styles.resultValue}>
                                                    {orderData.name}
                                                </span>
                                            </div>
                                            <div className={styles.resultRow}>
                                                <span className={styles.resultLabel}>เบอร์โทร</span>
                                                <span className={styles.resultValue}>
                                                    {orderData.tel}
                                                </span>
                                            </div>
                                            <div className={styles.resultRow}>
                                                <span className={styles.resultLabel}>
                                                    หมายเลขคำสั่งซื้อ
                                                </span>
                                                <span className={styles.resultValue}>
                                                    {orderData.code}
                                                </span>
                                            </div>
                                            <div className={styles.resultRow}>
                                                <span className={styles.resultLabel}>ส่วนลด</span>
                                                <span className={styles.resultValue}>
                                                    {orderData.discountdetail}
                                                </span>
                                            </div>
                                            <div className={styles.resultRow}>
                                                <span className={styles.resultLabel}>
                                                    ค่าส่ง + ยอดสุทธิ
                                                </span>
                                                <span className={styles.resultValue}>
                                                    {shipping} + {payAmount} = {total}
                                                </span>
                                            </div>
                                            <div className={styles.resultRow}>
                                                <span className={styles.resultLabel}>เลขพัสดุ</span>
                                                <span className={styles.resultValue}>
                                                    {orderData.shipping_code || "-"}
                                                </span>
                                            </div>
                                            <div className={styles.resultRowFull}>
                                                <span className={styles.resultLabel}>
                                                    ที่อยู่จัดส่ง
                                                </span>
                                                <span className={styles.resultValue}>
                                                    {orderData.address}{" "}
                                                    {orderData.subdistrict} {orderData.district}{" "}
                                                    {orderData.province} {orderData.zipcode}
                                                </span>
                                            </div>
                                            <div className={styles.resultRow}>
                                                <span className={styles.resultLabel}>
                                                    สถานะคำสั่งซื้อ
                                                </span>
                                                <span className={styles.resultValue}>
                                                    {orderData.postatus}
                                                </span>
                                            </div>

                                            <div className={styles.resultRowFull}>
                                                <span className={styles.resultLabel}>การชำระเงิน</span>

                                                <div className={styles.imageCenter}>
                                                    <img
                                                        className={styles.paymentImage}
                                                        src="/payment_oo.jpg"
                                                        alt="payment slip"
                                                    />
                                                </div>
                                            </div>
                                        </div>

                                        <div className={styles.confirmWrapper}>
                                            <button
                                                type="button"
                                                className={styles.confirmButton}
                                                onClick={handleConfirmPayment}
                                            >
                                                ยืนยันการชำระเงิน
                                            </button>
                                        </div>
                                    </section>
                                );
                            }

                            return (
                                <section className={styles.resultCard}>
                                    <h2 className={styles.resultTitle}>รายละเอียดคำสั่งซื้อ</h2>
                                    <div className={styles.resultGrid}>
                                        <div className={styles.resultRow}>
                                            <span className={styles.resultLabel}>ชื่อลูกค้า</span>
                                            <span className={styles.resultValue}>
                                                {orderData.name}
                                            </span>
                                        </div>
                                        <div className={styles.resultRow}>
                                            <span className={styles.resultLabel}>เบอร์โทร</span>
                                            <span className={styles.resultValue}>
                                                {orderData.tel}
                                            </span>
                                        </div>
                                        <div className={styles.resultRow}>
                                            <span className={styles.resultLabel}>
                                                หมายเลขคำสั่งซื้อ
                                            </span>
                                            <span className={styles.resultValue}>
                                                {orderData.code}
                                            </span>
                                        </div>
                                        <div className={styles.resultRow}>
                                            <span className={styles.resultLabel}>ส่วนลด</span>
                                            <span className={styles.resultValue}>
                                                {orderData.discountdetail}
                                            </span>
                                        </div>
                                        <div className={styles.resultRow}>
                                            <span className={styles.resultLabel}>ค่าส่ง</span>
                                            <span className={styles.resultValue}>
                                                {orderData.shipping}
                                            </span>
                                        </div>
                                        <div className={styles.resultRow}>
                                            <span className={styles.resultLabel}>ยอดสุทธิ</span>
                                            <span className={styles.resultValue}>
                                                {orderData.pay_amount}
                                            </span>
                                        </div>
                                        <div className={styles.resultRow}>
                                            <span className={styles.resultLabel}>เลขพัสดุ</span>
                                            <span className={styles.resultValue}>
                                                {orderData.shipping_code || "-"}
                                            </span>
                                        </div>
                                        <div className={styles.resultRowFull}>
                                            <span className={styles.resultLabel}>ที่อยู่จัดส่ง</span>
                                            <span className={styles.resultValue}>
                                                {orderData.address}{" "}
                                                {orderData.subdistrict} {orderData.district}{" "}
                                                {orderData.province} {orderData.zipcode}
                                            </span>
                                        </div>
                                        <div className={styles.resultRow}>
                                            <span className={styles.resultLabel}>
                                                สถานะคำสั่งซื้อ
                                            </span>
                                            <span className={styles.resultValue}>
                                                {orderData.postatus}
                                            </span>
                                        </div>
                                    </div>
                                </section>
                            );
                        })()}
                </section>
            </main>

            {/* Footer */}
            <footer className={styles.footer}>
                <div>© {new Date().getFullYear()} HealthCare++ Shop</div>
                <div className={styles.footerLinks}>
                    <a href="#">123</a>
                    <a href="#">456</a>
                    <a href="#">789</a>
                </div>
            </footer>
        </div>
    );
}
