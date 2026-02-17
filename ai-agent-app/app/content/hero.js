"use client";

import { useEffect, useRef } from "react";
import styles from "./hero.module.css";

export default function Hero() {
    const titleRef = useRef(null);

    useEffect(() => {
        const title = titleRef.current;
        if (!title) return;

        const handleMouseMove = (e) => {
            const { clientX, clientY } = e;
            const { left, top, width, height } = title.getBoundingClientRect();
            const x = (clientX - left) / width;
            const y = (clientY - top) / height;

            title.style.setProperty("--x", x);
            title.style.setProperty("--y", y);
        };

        window.addEventListener("mousemove", handleMouseMove);
        return () => window.removeEventListener("mousemove", handleMouseMove);
    }, []);

    return (
        <section className={styles.hero}>
            <div className={styles.content}>
                <h1 ref={titleRef} className={styles.title}>
                    The Intelligence<br />
                    <span className={styles.highlight}>of Nature </span>
                </h1>
                <p className={styles.subtitle}>
                    Harmonizing nature with advanced AI agents
                </p>
                <div className={styles.scrollIndicator}>
                    <span>Scroll to explore</span>
                    <div className={styles.arrow}>↓</div>
                </div>
            </div>
            <div className={styles.backgroundBlur} />
        </section>
    );
}
