"use client";
import styles from "./nav.module.css";

export default function Navbar() {
  return (
    <nav className={styles.navbar}>
      <div className={styles.brand}>Admin Panel</div>
      <ul className={styles.menu}>
        <li><a href="/admin/call">Call center Dashboard</a></li>
        <li><a href="/admin/call/session">Open Chat Session (NOT DONE)</a></li>
        <li><a href="/admin/call/session_log">Chat log (NOT DONE)</a></li>
        <li><a href="/admin/call/ticket">Ticket (NOT DONE)</a></li>
      </ul>
    </nav>
  );
}
