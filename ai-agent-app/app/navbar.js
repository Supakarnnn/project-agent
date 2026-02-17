"use client";

import Link from "next/link";
import styles from "./navbar.module.css";

export default function Navbar() {
    return (
        <nav className={styles.navbar}>
            <div className={styles.container}>
                <div className={styles.left}>
                    <Link href="/payment" className={styles.link}>
                        Payment
                    </Link>
                    <Link href="/about" className={styles.link}>
                        About Us
                    </Link>
                </div>

                <div className={styles.center}>
                    <Link href="/" className={styles.brand}>
                        VITALIS
                    </Link>
                </div>

                <div className={styles.right}>
                    <button className={styles.iconButton} aria-label="chat">
                        <svg xmlns="http://www.w3.org/2000/svg"
                            width="24"
                            height="24"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            class="lucide lucide-message-circle-icon lucide-message-circle">
                            <path d="M2.992 16.342a2 2 0 0 1 .094 1.167l-1.065 3.29a1 1 0 0 0 1.236 1.168l3.413-.998a2 2 0 0 1 1.099.092 10 10 0 1 0-4.777-4.719" /></svg>
                    </button>
                </div>
            </div>
        </nav>
    );
}
