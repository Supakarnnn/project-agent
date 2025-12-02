"use client";

import Navbar from "./nav";
import { LogoutButton } from "../Component/logout";
import styles from "./page.module.css";

export default function Home() {
  return (
    <div className={styles.layout}>
      <Navbar />

      <main className={styles.main}>
        <div className={styles.header}>
          <h1 className={styles.title}>Call center Dashboard</h1>
          <LogoutButton>Logout</LogoutButton>
        </div>
        <p>welcome call center</p>
      </main>
    </div>
  );
}
