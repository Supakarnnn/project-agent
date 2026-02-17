import React from "react";
import Link from "next/link";
import styles from "./footer.module.css";

const Footer = () => {
    return (
        <footer className={styles.footer}>
            <div>
                <div className={styles.footerGrid}>
                    {/* Brand */}
                    <div>
                        <span className={styles.footerBrand}>VITALIS</span>
                        <p className={styles.footerDesc}>
                            Premium natural healthcare & wellness
                        </p>
                        <p className={styles.footerDesc}>
                            Products crafted with botanical excellence
                        </p>

                        <div className={styles.footerContact}>
                            <div>
                                <p className={styles.footerContactTitle}>Contact</p>
                                <p>connect2us@vitalis.com</p>
                                <p>+66 09817172626</p>
                            </div>
                        </div>
                    </div>

                    {/* Links */}
                    <div className={styles.footerLinksGrid}>
                        <div>
                            <h4 className={styles.footerSectionTitle}>Shop</h4>
                            <ul className={styles.footerList}>
                                <li><Link href="/" className={styles.footerLink}>Supplements</Link></li>
                                <li><Link href="/" className={styles.footerLink}>Skincare</Link></li>
                                <li><Link href="/" className={styles.footerLink}>Herbal</Link></li>
                                <li><Link href="/" className={styles.footerLink}>Vitamins</Link></li>
                                <li><Link href="/" className={styles.footerLink}>Bundles</Link></li>
                            </ul>
                        </div>

                        <div>
                            <h4 className={styles.footerSectionTitle}>Support</h4>
                            <ul className={styles.footerList}>
                                <li><Link href="/" className={styles.footerLink}>Customer Care</Link></li>
                                <li><Link href="/" className={styles.footerLink}>Dosage Guide</Link></li>
                                <li><a href="#" className={styles.footerLink}>Shipping</a></li>
                                <li><a href="#" className={styles.footerLink}>Returns</a></li>
                            </ul>
                        </div>

                        <div>
                            <h4 className={styles.footerSectionTitle}>Connect</h4>
                            <ul className={styles.footerList}>
                                <li><a href="https://www.instagram.com/google/" className={styles.footerLink}>Instagram</a></li>
                                <li><a href="https://www.facebook.com/google/" className={styles.footerLink}>Facebook</a></li>
                                <li><a href="https://www.x.com/google/" className={styles.footerLink}>X</a></li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>

            <div className={styles.footerBottom}>
                <div className={styles.footerBottomInner}>
                    <p className={styles.footerCopy}>© 2025 Vitalis. All rights reserved.</p>
                    <div className={styles.footerLegal}>
                        <Link href="/privacy" className={styles.footerLink}>Privacy Policy</Link>
                        <Link href="/termser" className={styles.footerLink}>Terms of Service</Link>
                    </div>
                </div>
            </div>
        </footer>
    );
};

export default Footer;
