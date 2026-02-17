"use client";

import { useEffect } from "react";
import Navbar from "../navbar";
import Footer from "../content/footer";
import styles from "./page.module.css";

const PrivacyPolicy = () => {
    useEffect(() => {
        document.title = "Privacy Policy - Vitalis";
    }, []);

    return (
        <div className={styles.page}>
            <Navbar />

            <main className={styles.main}>
                <div className={styles.container}>
                    <header className={styles.hero}>
                        <h1 className={styles.title}>Privacy Policy</h1>
                        <p className={styles.updated}>Last updated: February 27, 2026</p>
                    </header>

                    <div className={styles.content}>
                        <section className={styles.section}>
                            <h2 className={styles.h2}>Introduction</h2>
                            <p className={styles.p}>
                                At Vitalis ("we," "our," or "us"), we respect your privacy and are committed to
                                protecting your personal data. This Privacy Policy explains how we collect, use, disclose,
                                and safeguard your information when you visit our website, make a purchase, or interact with
                                our services.
                            </p>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>Information We Collect</h2>

                            <div className={styles.stack}>
                                <div>
                                    <h3 className={styles.h3}>Personal Information</h3>
                                    <p className={styles.p}>
                                        We may collect personal information that you provide directly to us, including:
                                    </p>
                                    <ul className={styles.list}>
                                        <li>Name, email address, phone number, and contact information</li>
                                        <li>Billing and shipping addresses</li>
                                        <li>Payment information (processed securely through third-party providers)</li>
                                        <li>Account preferences and communication settings</li>
                                    </ul>
                                </div>

                                <div>
                                    <h3 className={styles.h3}>Health-Related Information (Limited)</h3>
                                    <p className={styles.p}>
                                        In certain cases, you may voluntarily provide limited health-related information, such as:

                                        Product preferences related to wellness goals

                                        Allergy or ingredient concerns (for product suitability only)

                                        This information is used solely to improve product recommendations and customer support and is not considered medical advice or diagnosis.
                                    </p>
                                </div>
                            </div>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>How We Use Your Information</h2>
                            <p className={styles.p}>
                                We use your information for the following purposes:
                            </p>
                            <ul className={styles.list}>
                                <li>Processing and delivering orders</li>
                                <li>Providing customer service and support</li>
                                <li>Responding to inquiries and feedback</li>
                                <li>Improving our website functionality and user experience</li>
                                <li>Sending updates, promotions, or newsletters (with your consent)</li>
                                <li>Complying with legal obligations</li>
                            </ul>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>Medical Disclaimer</h2>
                            <p className={styles.p}>
                                Vitalis provides healthcare and wellness products only.
                                Information provided on our website or through customer communication:
                            </p>
                            <ul className={styles.list}>
                                <li>Is not a substitute for professional medical advice</li>
                                <li>Does not constitute diagnosis or treatment</li>
                                <li>Should not be relied upon for medical decisions</li>
                            </ul>
                            <p className={styles.p}>Please consult a licensed healthcare professional before using any healthcare or wellness product, especially if you have underlying medical conditions.</p>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>Information Sharing and Disclosure</h2>
                            <p className={styles.p}>
                                We do not sell or rent your personal information.
                                We may share information only with:
                            </p>
                            <ul className={styles.list}>
                                <li>Trusted service providers (payment processing, shipping, IT services)</li>
                                <li>Legal or regulatory authorities when required by law</li>
                                <li>Business partners strictly necessary to fulfill your order</li>
                                <li>Third parties with your explicit consent</li>
                            </ul>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>Data Security</h2>
                            <p className={styles.p}>
                                We implement appropriate technical and organizational safeguards to protect your personal data, including:
                            </p>
                            <ul className={styles.list}>
                                <li>Secure servers and encrypted connections</li>
                                <li>Limited access to personal information</li>
                                <li>Regular system monitoring and updates</li>
                            </ul>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>Your Rights and Choices</h2>
                            <p className={styles.p}>
                                Depending on your location, you may have certain rights regarding your personal information:
                            </p>
                            <ul className={styles.list}>
                                <li>Access to your personal information</li>
                                <li>Correction of inaccurate or incomplete information</li>
                                <li>Deletion of your personal information</li>
                                <li>Objection to or restriction of processing</li>
                                <li>Data portability</li>
                                <li>Withdrawal of consent (where applicable)</li>
                            </ul>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>Cookies and Tracking</h2>
                            <p className={styles.p}>
                                We use cookies and similar tracking technologies to enhance your browsing experience, analyze
                                website traffic, and personalize content. You can control cookie settings through your
                                browser preferences, though this may affect website functionality.
                            </p>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>Changes to This Policy</h2>
                            <p className={styles.p}>
                                We may update this Privacy Policy periodically.
                                Any changes will be posted on this page with an updated “Last updated” date. Continued use of our services constitutes acceptance of the revised policy.
                            </p>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>Contact Us</h2>
                            <p className={styles.p}>
                                If you have any questions about this Privacy Policy or our privacy practices, please contact
                                us at:
                            </p>
                            <div className={styles.contact}>
                                <p>Email: connect2us@vitalis.com</p>
                                <p>Phone: +66 09817172626</p>
                                <p>Address: 67/1 ถนนสุขุมวิท แขวงคลองตันเหนือ เขตวัฒนา กรุงเทพมหานคร 10110 ประเทศไทย</p>
                            </div>
                        </section>
                    </div>
                </div>
            </main>

            <Footer />
        </div>
    );
};

export default PrivacyPolicy;
