"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./login.module.css";
import { Eye, EyeOff, Lock, Mail, ShieldCheck, User } from "lucide-react";

export default function AdminLogin() {
  const r = useRouter();
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setErr("");

    try {
      const resp = await fetch(process.env.NEXT_PUBLIC_API_URL + "/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ name, password }),
      });

      if (!resp.ok) {
        const j = await resp.json().catch(() => ({ detail: "Login failed" }));
        throw new Error(j.detail || "Login failed");
      }

      const data = await resp.json();

      if (data.role === "admin") {
        r.replace("/admin");
      } else if (data.role === "call_center") {
        r.replace("/admin/call");
      } else {
        setErr("username or password is wrong");
      }
    } catch (err) {
      setErr(err.message || "Login failed");
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.leftPanel}>
        <div className={styles.leftBg} />

        <div className={styles.leftContent}>
          <div className={styles.brandIcon}>
            <ShieldCheck className={styles.brandIconSvg} />
          </div>

          <h1 className={styles.brandTitle}>VITALIS</h1>

          <p className={styles.brandDesc}>
            Admin Dashboard — Manage products, orders, and customer insights in one place.
          </p>

          <div className={styles.dotsRow}>
            {[1, 2, 3].map((i) => (
              <div key={i} className={styles.dot} />
            ))}
          </div>
        </div>
        <div className={styles.circleBottomLeft} />
        <div className={styles.circleTopRight} />
      </div>

      <div className={styles.rightPanel}>
        <div className={styles.card}>
          {/* Mobile branding */}
          <div className={styles.mobileBrand}>
            <div className={styles.mobileIcon}>
              <ShieldCheck className={styles.mobileIconSvg} />
            </div>
            <h1 className={styles.mobileTitle}>VITALIS</h1>
          </div>

          <div className={styles.header}>
            <h2 className={styles.h2}>Welcome back</h2>
            <p className={styles.sub}>
              Sign in to your admin account to continue
            </p>
          </div>

          <form onSubmit={submit} className={styles.form}>
            {/* Email */}
            <div className={styles.field}>
              <label className={styles.label}>USERNAME</label>
              <div className={styles.inputWrap}>
                <User className={styles.inputIcon} />
                <input
                  className={styles.input}
                  placeholder="admin"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
            </div>

            {/* Password */}
            <div className={styles.field}>
              <label className={styles.label}>PASSWORD</label>
              <div className={styles.inputWrap}>
                <Lock className={styles.inputIcon} />
                <input
                  className={styles.input}
                  type={showPassword ? "text" : "password"}
                  placeholder="********"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className={styles.eyeBtn}
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            {err && <p className={styles.error}>{err}</p>}

            {/* Submit */}
            <button className={styles.submitBtn}>SIGN IN</button>
          </form>

          <p className={styles.footerNote}>
            Protected area. Authorized personnel only.
          </p>
        </div>
      </div>
    </div>
  );
}


