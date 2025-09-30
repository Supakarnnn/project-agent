"use client";

import Navbar from "./component/nav";
import { LogoutButton } from "./component/logout";
import styles from "./page.module.css";

export default function Home() {
  return (
    <div className={styles.layout}>
      <Navbar />

      <main className={styles.main}>
        <div className={styles.header}>
          <h1 className={styles.title}>Admin Dashboard</h1>
          <LogoutButton>Logout</LogoutButton>
        </div>
        <p>welcome admin</p>
      </main>
    </div>
  );
}
