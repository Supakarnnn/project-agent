"use client";

import Link from "next/link";
import styles from "./featured.module.css";

const PRODUCTS = [
    {
        id: 1,
        title: "VISTRA Acerola Cherry",
        category: "Supplements",
        price: 219,
        image: "/cherry.png",
        link: "/"
    },
    {
        id: 2,
        title: "MizuMi UV Water Serum",
        category: "Skincare",
        price: 444,
        image: "/uv_water.png",
        link: "/"
    },
    {
        id: 3,
        title: "AloEx Shampoo",
        category: "Hair Care",
        price: 595,
        image: "/aloex.png",
        link: "/"
    },
    {
        id: 4,
        title: "CLEAR NOSE Moist Skin Barrier",
        category: "Skincare",
        price: 585,
        image: "/skin_bar.png",
        link: "/"
    }
];

export default function FeaturedProducts() {
    return (
        <section className={styles.section}>
            <div className={styles.header}>
                <div>
                    <h2 className={styles.heading}>Example Products</h2>
                    <p className={styles.subHeading}>Curated for your wellness journey</p>
                </div>
            </div>

            <div className={styles.grid}>
                {PRODUCTS.map((product) => (
                    <div key={product.id} className={styles.card}>
                        <Link href={product.link} className={styles.link}>
                            <div className={styles.imageWrap}>
                                <img
                                    src={product.image}
                                    alt={product.title}
                                    className={styles.image}
                                />
                            </div>
                        </Link>

                        <div className={styles.textWrap}>
                            <p className={styles.category}>{product.category}</p>
                            <div className={styles.row}>
                                <h3 className={styles.title}>{product.title}</h3>
                                <p className={styles.price}>฿{product.price}</p>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </section>
    );
}
