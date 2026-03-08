"use client";
import styles from "./nav.module.css";

export default function Navbar() {
  return (
    <nav className={styles.navbar}>
      <div className={styles.brand}>Admin Panel</div>
      <ul className={styles.menu}>
        <li><a href="/admin">Admin Dashboard</a></li>
        <li><a href="/admin/add_product">Add New Product</a></li>
        <li><a href="/admin/Rag_system_v2">Ai Knowledge</a></li>
        <li><a href="/admin/Intent">Ai Tool</a></li>
        <li><a href="/admin/open_session">Open Chat Session</a></li>
        <li><a href="/admin/chat_message_log">Chat message log</a></li>
        <li><a href="/admin/ticket_admin">Ticket</a></li>
        <li><a href="/admin/Config_ai">Settings Ai</a></li>
      </ul>
    </nav>
  );
}
