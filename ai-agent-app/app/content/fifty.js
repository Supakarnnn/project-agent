"use client";

import Link from "next/link";
import styles from "./fifty.module.css";

export default function FiftyFiftySection() {
    return (
        <section className={styles.section}>
            <div className={styles.grid}>
                <div className={styles.card}>
                    <Link href="/" className={styles.link}>
                        <div className={styles.imageWrap}>
                            <img
                                src="/vitamin.jpeg"
                                alt=""
                                className={styles.image}
                            />
                        </div>
                    </Link>

                    <div className={styles.textWrap}>
                        <h3 className={styles.title}>Supplements Vitamins</h3>
                        <p className={styles.desc}>
                            Premium botanical supplements for daily vitality
                        </p>
                    </div>
                </div>

                <div className={styles.card}>
                    <Link href="/" className={styles.link}>
                        <div className={styles.imageWrap}>
                            <img
                                src="/natural.png"
                                alt=""
                                className={styles.image}
                            />
                        </div>
                    </Link>

                    <div className={styles.textWrap}>
                        <h3 className={styles.title}>Natural Skincare</h3>
                        <p className={styles.desc}>
                            Plant-based serums and creams for radiant skin
                        </p>
                    </div>
                </div>
            </div>
        </section>
    );
}
