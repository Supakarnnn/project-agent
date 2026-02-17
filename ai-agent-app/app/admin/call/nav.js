"use client";
import styles from "./nav.module.css";

export default function Navbar() {
  return (
    <nav className={styles.navbar}>
      <div className={styles.brand}>Call Center Panel</div>
      <ul className={styles.menu}>
        <li><a href="/admin/call">Call center Dashboard</a></li>
        <li><a href="/admin/call/session">Open Chat Session</a></li>
        <li><a href="/admin/call/session_log">Chat log</a></li>
        <li><a href="/admin/call/ticket">Ticket</a></li>
      </ul>
    </nav>
  );
}
