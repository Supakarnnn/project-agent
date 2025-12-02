// createso.js
"use client";

import { useState, useEffect } from "react";
import Modal from "react-modal";
import styles from "./createso.module.css";

export default function CreateSO() {
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [wantTaxInvoice, setWantTaxInvoice] = useState(false);

  useEffect(() => {
    if (typeof document !== "undefined") {
      Modal.setAppElement("body");
    }
  }, []);

  //state
  const [form, setForm] = useState({
    // 1. ข้อมูลลูกค้า
    customerName: "",
    customerPhone: "",

    // 2. ชำระเงิน
    paymentMethod: "โอนเงิน",

    // 3. ข้อมูลการจัดส่ง
    shippingAddress: "",
    shippingProvince: "",
    shippingDistrict: "",
    shippingSubDistrict: "",
    shippingPostcode: "",

    // 4. ใบกำกับภาษี (optional)
    taxAddress: "",
    taxProvince: "",
    taxDistrict: "",
    taxSubDistrict: "",
    taxPostcode: "",
    taxId: "",
    taxName: "",
  });

  const clearForm = () => {
    setForm({
      customerName: "",
      customerPhone: "",
      paymentMethod: "โอนเงิน",

      shippingAddress: "",
      shippingProvince: "",
      shippingDistrict: "",
      shippingSubDistrict: "",
      shippingPostcode: "",

      taxAddress: "",
      taxProvince: "",
      taxDistrict: "",
      taxSubDistrict: "",
      taxPostcode: "",
      taxId: "",
      taxName: "",
    });

    setWantTaxInvoice(false);
  };


  const openModal = () => setIsOpen(true);
  const closeModal = () => {
    if (!loading) setIsOpen(false);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    const agentPrompt = buildAgentPrompt(form, wantTaxInvoice);

    console.log(agentPrompt);

    try {
      const resp = await fetch(process.env.NEXT_PUBLIC_API_URL + "/agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: agentPrompt,
        }),
      });

      const data = await resp.json();
      console.log("agent response:", data);

      setIsOpen(false);
    } catch (err) {
      console.error(err);
    }

    setLoading(false);
  };

  function buildAgentPrompt(form, wantTaxInvoice) {
    return `
ลูกค้าต้องการสร้างคำสั่งซื้อใหม่ กรุณาใช้เครื่องมือ create_order ในการสร้างออเดอร์ตามข้อมูลด้านล่างนี้:

[ข้อมูลลูกค้า]
- ชื่อผู้สั่งซื้อ: ${form.customerName}
- เบอร์โทรศัพท์: ${form.customerPhone}

[การชำระเงิน]
- วิธีชำระเงิน: ${form.paymentMethod}

[ข้อมูลการจัดส่ง]
- ที่อยู่จัดส่ง: ${form.shippingAddress}
- จังหวัด: ${form.shippingProvince}
- เขต/อำเภอ: ${form.shippingDistrict}
- แขวง/ตำบล: ${form.shippingSubDistrict}
- รหัสไปรษณีย์: ${form.shippingPostcode}

[ใบกำกับภาษี]
${wantTaxInvoice ? `
- ชื่อออกใบกำกับภาษี: ${form.taxName}
- เลขประจำตัวผู้เสียภาษี: ${form.taxId}
- ที่อยู่: ${form.taxAddress}
- จังหวัด: ${form.taxProvince}
- เขต/อำเภอ: ${form.taxDistrict}
- แขวง/ตำบล: ${form.taxSubDistrict}
- รหัสไปรษณีย์: ${form.taxPostcode}
` : "ลูกค้าไม่ต้องการใบกำกับภาษี"}

กรุณาสร้างคำสั่งซื้อให้สมบูรณ์และตอบกลับเฉพาะผลลัพธ์จากการใช้เครื่องมือเท่านั้น
`.trim();
  }


  return (
    <>
      <button
        className={styles.button}
        disabled={loading}
        aria-busy={loading}
        type="button"
        onClick={openModal}
      >
        {loading ? "..." : "Create Order"}
      </button>

      {/* Modal */}
      <Modal
        isOpen={isOpen}
        onRequestClose={closeModal}
        overlayClassName={styles.modalOverlay}
        className={styles.modalContent}
        contentLabel="สร้างคำสั่งซื้อ"
      >
        <div className={styles.modalHeader}>
          <h2>สร้างคำสั่งซื้อ</h2>
          <button
            type="button"
            className={styles.closeButton}
            onClick={closeModal}
            disabled={loading}
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          {/* 1. ข้อมูลลูกค้า */}
          <section className={styles.section}>
            <h3>1. ข้อมูลลูกค้า</h3>
            <div className={styles.fieldGroup}>
              <label>
                ชื่อผู้สั่งซื้อ
                <input
                  name="customerName"
                  type="text"
                  value={form.customerName}
                  onChange={handleChange}
                  required
                />
              </label>
              <label>
                เบอร์โทรศัพท์
                <input
                  name="customerPhone"
                  type="tel"
                  value={form.customerPhone}
                  onChange={handleChange}
                  required
                />
              </label>
            </div>
          </section>

          {/* 2. ชำระเงิน */}
          <section className={styles.section}>
            <h3>2. ชำระเงิน</h3>
            <div className={styles.fieldGroup}>
              <label>
                วิธีการชำระเงิน
                <select
                  name="paymentMethod"
                  value={form.paymentMethod}
                  onChange={handleChange}
                >
                  <option value="โอนเงิน">โอนเงิน</option>
                  <option value="บัตรเครดิต">บัตรเครดิต</option>
                  <option value="ปลายทาง">เก็บเงินปลายทาง</option>
                </select>
              </label>
            </div>
          </section>

          {/* 3. ข้อมูลการจัดส่ง */}
          <section className={styles.section}>
            <h3>3. ข้อมูลการจัดส่ง</h3>
            <div className={styles.fieldGroup}>
              <label>
                ที่อยู่จัดส่ง
                <textarea
                  name="shippingAddress"
                  rows={2}
                  value={form.shippingAddress}
                  onChange={handleChange}
                  required
                />
              </label>
            </div>
            <div className={styles.grid2}>
              <label>
                จังหวัด
                <input
                  name="shippingProvince"
                  type="text"
                  value={form.shippingProvince}
                  onChange={handleChange}
                  required
                />
              </label>
              <label>
                เขต / อำเภอ
                <input
                  name="shippingDistrict"
                  type="text"
                  value={form.shippingDistrict}
                  onChange={handleChange}
                  required
                />
              </label>
            </div>
            <div className={styles.grid2}>
              <label>
                แขวง / ตำบล
                <input
                  name="shippingSubDistrict"
                  type="text"
                  value={form.shippingSubDistrict}
                  onChange={handleChange}
                  required
                />
              </label>
              <label>
                รหัสไปรษณีย์
                <input
                  name="shippingPostcode"
                  type="text"
                  value={form.shippingPostcode}
                  onChange={handleChange}
                  required
                />
              </label>
            </div>
          </section>

          {/* 4. ใบกำกับภาษี (optional) */}
          <section className={styles.section}>
            <div className={styles.sectionHeaderRow}>
              <h3>4. ใบกำกับภาษี (optional)</h3>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={wantTaxInvoice}
                  onChange={(e) => setWantTaxInvoice(e.target.checked)}
                />
                ต้องการใบกำกับภาษี
              </label>
            </div>

            {wantTaxInvoice && (
              <>
                <div className={styles.fieldGroup}>
                  <label>
                    ที่อยู่ออกใบกำกับภาษี
                    <textarea
                      name="taxAddress"
                      rows={2}
                      value={form.taxAddress}
                      onChange={handleChange}
                    />
                  </label>
                </div>
                <div className={styles.grid2}>
                  <label>
                    จังหวัด
                    <input
                      name="taxProvince"
                      type="text"
                      value={form.taxProvince}
                      onChange={handleChange}
                    />
                  </label>
                  <label>
                    เขต / อำเภอ
                    <input
                      name="taxDistrict"
                      type="text"
                      value={form.taxDistrict}
                      onChange={handleChange}
                    />
                  </label>
                </div>
                <div className={styles.grid2}>
                  <label>
                    แขวง / ตำบล
                    <input
                      name="taxSubDistrict"
                      type="text"
                      value={form.taxSubDistrict}
                      onChange={handleChange}
                    />
                  </label>
                  <label>
                    รหัสไปรษณีย์
                    <input
                      name="taxPostcode"
                      type="text"
                      value={form.taxPostcode}
                      onChange={handleChange}
                    />
                  </label>
                </div>
                <div className={styles.grid2}>
                  <label>
                    เลขประจำตัวผู้เสียภาษี
                    <input
                      name="taxId"
                      type="text"
                      value={form.taxId}
                      onChange={handleChange}
                    />
                  </label>
                  <label>
                    ชื่อออกใบกำกับภาษี
                    <input
                      name="taxName"
                      type="text"
                      value={form.taxName}
                      onChange={handleChange}
                    />
                  </label>
                </div>
              </>
            )}
          </section>

          <div className={styles.footer}>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={clearForm}
              disabled={loading}
            >
              ลบทั้งหมด
            </button>

            <button
              type="button"
              className={styles.secondaryButton}
              onClick={closeModal}
              disabled={loading}
            >
              ยกเลิก
            </button>

            <button
              type="submit"
              className={styles.primaryButton}
              disabled={loading}
            >
              {loading ? "กำลังบันทึก..." : "ยืนยันสร้างคำสั่งซื้อ"}
            </button>
          </div>

        </form>
      </Modal>
    </>
  );
}
