"use client";
import styles from "./nav.module.css";

export default function Navbar() {
  return (
    <nav className={styles.navbar}>
      <div className={styles.brand}>Admin Panel</div>
      <ul className={styles.menu}>
        <li><a href="/admin">Admin Dashboard</a></li>
        <li><a href="/admin/Rag_system_v2">Ai Knowledge</a></li>
        <li><a href="/admin/Intent">Ai Tool</a></li>
        <li><a href="/admin/session">Open Chat Session (NOT DONE)</a></li>
        <li><a href="/admin/session_log">Chat log (NOT DONE)</a></li>
        <li><a href="/admin/ticket">Ticket (NOT DONE)</a></li>
        <li><a href="/admin/Config_ai">Settings Ai</a></li>
      </ul>
    </nav>
  );
}
