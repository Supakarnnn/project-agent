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
    const resp = await fetch(process.env.NEXT_PUBLIC_API_URL + "/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ name, password }),
    });
    if (resp.ok) {
      r.replace("/admin");
    } else {
      const j = await resp.json().catch(() => ({ detail: "Login failed" }));
      setErr(j.detail || "Login failed");
    }
  };

  return (
    <div className={styles.container}>
      <form onSubmit={submit} className={styles.form}>
        <h1 className={styles.title}>Admin Login</h1>
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
