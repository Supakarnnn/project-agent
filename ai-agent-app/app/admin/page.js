"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "./Component/nav";
import { LogoutButton } from "./Component/logout";
import styles from "./page.module.css";

export default function AdminPage() {
  const r = useRouter();
  const [loading, setLoading] = useState(true);
  const [me, setMe] = useState(null);

  useEffect(() => {
    const check = async () => {
      try {
        const resp = await fetch(process.env.NEXT_PUBLIC_API_URL + "/auth/check", {
          credentials: "include",
        });
        if (!resp.ok) throw new Error("unauth");
        const data = await resp.json();

        if (data.role !== "admin") {
          if (data.role === "call_center") r.replace("/admin/call");
          return;
        }
        setMe(data);
      } catch {
        r.replace("/admin/login");
      } finally {
        setLoading(false);
      }
    };
    check();
  }, [r]);

  if (loading) return <p>Checking authorization...</p>;
  if (!me) return null;

  return (
    <div className={styles.layout}>
      <Navbar />
      <main className={styles.main}>
        <div className={styles.header}>
          <h1 className={styles.title}>Admin Dashboard</h1>
          <LogoutButton>Logout</LogoutButton>
        </div>
        <p>Welcome, {me.name}</p>
      </main>
    </div>
  );
}
