"use client";
import styles from "./nav.module.css";

export default function Navbar() {
  return (
    <nav className={styles.navbar}>
      <div className={styles.brand}>Admin Panel</div>
      <ul className={styles.menu}>
        <li><a href="/admin">Admin Dashboard</a></li>
        <li><a href="/admin/rag_system_v2">Ai Knowledge</a></li>
        <li><a href="/admin/intent">Ai Tool</a></li>
        <li><a href="/admin/session">Open Chat Session</a></li>
        <li><a href="/admin/session_log">Chat log</a></li>
        <li><a href="/admin/ticket">Ticket</a></li>
        <li><a href="/admin/config_ai">Settings Ai</a></li>
      </ul>
    </nav>
  );
}
