"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./login.module.css";

export default function AdminLogin() {
  const r = useRouter();
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
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
        setErr("role not allow");
      }
    } catch (err) {
      setErr(err.message || "Login failed");
    }
  };

  return (
    <div className={styles.container}>
      <form onSubmit={submit} className={styles.form}>
        <h1 className={styles.title}>Healtcare++ Admin Login</h1>
        <input
          className={styles.input}
          placeholder="username"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          className={styles.input}
          type="password"
          placeholder="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {err && <p className={styles.error}>{err}</p>}
        <button className={styles.button}>Sign in</button>
      </form>
    </div>
  );
}
