"use client";

import { useEffect } from "react";
import Navbar from "../navbar";
import Footer from "../content/footer";
import styles from "./page.module.css";

const TermsOfService = () => {
    useEffect(() => {
        document.title = "Terms of Service - Vitalis";
    }, []);

    return (
        <div className={styles.page}>
            <Navbar />

            <main className={styles.main}>
                <div className={styles.container}>
                    <header className={styles.hero}>
                        <h1 className={styles.title}>Terms of Service</h1>
                        <p className={styles.updated}>Last updated: February 27, 2026</p>
                    </header>

                    <div className={styles.content}>
                        <section className={styles.section}>
                            <h2 className={styles.h2}>Agreement to Terms</h2>
                            <p className={styles.p}>
                                By accessing and using the Vitalis website and services, you accept and agree to be bound by the terms and provision of this agreement. These Terms of Service govern your use of our website, products, and services.
                            </p>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>Eligibility</h2>
                            <p className={styles.p}>
                                You must be at least 18 years old to use our services and purchase products from Vitalis.
                                By using this website, you represent that you are legally capable of entering into a binding agreement.
                            </p>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>Products and Services</h2>
                            <p className={styles.p}>
                                Vitalis offers healthcare and wellness products intended for general well-being.
                                Product descriptions, pricing, and availability are subject to change without notice.
                                We reserve the right to discontinue any product at any time.
                            </p>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>Medical Disclaimer</h2>
                            <p className={styles.p}>
                                Vitalis does not provide medical advice, diagnosis, or treatment.
                                All information provided on this website is for informational purposes only.
                            </p>
                            <ul className={styles.list}>
                                <li>Our products are not intended to diagnose, treat, cure, or prevent any disease</li>
                                <li>Information on this website is not a substitute for professional medical advice</li>
                                <li>You should consult a qualified healthcare professional before using any product</li>
                            </ul>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>Orders and Payments</h2>
                            <p className={styles.p}>
                                By placing an order, you agree to provide accurate and complete payment and shipping information.
                                All payments are processed securely through third-party payment providers.
                                Vitalis reserves the right to cancel or refuse any order at its discretion.
                            </p>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>Shipping and Delivery</h2>
                            <p className={styles.p}>
                                Delivery times are estimates and may vary due to external factors.
                                Vitalis is not responsible for delays caused by shipping carriers or events beyond our control.
                            </p>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>Returns and Refunds</h2>
                            <p className={styles.p}>
                                Returns and refunds are subject to our Return Policy.
                                Certain healthcare and wellness products may not be eligible for return due to safety and hygiene reasons.
                            </p>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>User Responsibilities</h2>
                            <p className={styles.p}>
                                You agree not to misuse the website or engage in any activity that could damage, disable,
                                or impair our services, including unauthorized access or data scraping.
                            </p>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>Intellectual Property</h2>
                            <p className={styles.p}>
                                All content on this website, including text, images, logos, and designs,
                                is the property of Vitalis and protected by intellectual property laws.
                                Unauthorized use of any content is strictly prohibited.
                            </p>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>Limitation of Liability</h2>
                            <p className={styles.p}>
                                To the fullest extent permitted by law, Vitalis shall not be liable for any indirect,
                                incidental, or consequential damages arising from the use or inability to use our products or services.
                            </p>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>Indemnification</h2>
                            <p className={styles.p}>
                                You agree to indemnify and hold harmless Vitalis from any claims, damages,
                                or expenses arising from your use of the website or violation of these Terms.
                            </p>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>Governing Law</h2>
                            <p className={styles.p}>
                                These Terms of Service shall be governed by and construed in accordance with
                                the laws of Thailand, without regard to its conflict of law principles.
                            </p>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>Changes to Terms</h2>
                            <p className={styles.p}>
                                Vitalis reserves the right to update or modify these Terms of Service at any time.
                                Continued use of the website after changes constitutes acceptance of the revised terms.
                            </p>
                        </section>

                        <section className={styles.section}>
                            <h2 className={styles.h2}>Contact Information</h2>
                            <p className={styles.p}>
                                If you have any questions regarding these Terms of Service, please contact us:
                            </p>
                            <div className={styles.contact}>
                                <p>Email: connect2us@vitalis.com</p>
                                <p>Phone: +66 098 171 7262</p>
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

export default TermsOfService;
