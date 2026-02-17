'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import styles from './page.module.css';
import Navbar from "../navbar";
import Footer from "../content/footer";

export default function AboutPage() {
    const [activeSection, setActiveSection] = useState('about-us');

    const handleScroll = (e, id) => {
        e.preventDefault();
        const element = document.getElementById(id);
        if (element) {
            const yOffset = -100; // Offset for sticky header
            const y = element.getBoundingClientRect().top + window.pageYOffset + yOffset;
            window.scrollTo({ top: y, behavior: 'smooth' });
        }
    };

    useEffect(() => {
        const observerOptions = {
            root: null,
            rootMargin: '-20% 0px -35% 0px', // Adjust detection area
            threshold: 0.1
        };

        const observerCallback = (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    setActiveSection(entry.target.id);
                }
            });
        };

        const observer = new IntersectionObserver(observerCallback, observerOptions);

        const sections = ['about-us', 'mission-vision', 'what-we-do', 'disclaimer'];
        sections.forEach(id => {
            const element = document.getElementById(id);
            if (element) observer.observe(element);
        });

        return () => observer.disconnect();
    }, []);

    const navItems = [
        { id: 'about-us', label: 'About Us' },
        { id: 'mission-vision', label: 'Mission & Vision' },
        { id: 'what-we-do', label: 'What We Do' },
        { id: 'disclaimer', label: 'Medical Disclaimer' },
    ];

    return (
        <div>
            <Navbar />
            <div className={styles.container}>
                {/* Sidebar Navigation */}
                <aside className={styles.sidebar}>
                    <nav className={styles.nav}>
                        <ul className={styles.navList}>
                            {navItems.map((item) => (
                                <li key={item.id} className={styles.navItem}>
                                    <a
                                        href={`#${item.id}`}
                                        onClick={(e) => handleScroll(e, item.id)}
                                        className={`${styles.navLink} ${activeSection === item.id ? styles.active : ''}`}
                                    >
                                        {item.label}
                                    </a>
                                </li>
                            ))}
                        </ul>
                    </nav>
                </aside>

                {/* Main Content */}
                <main className={styles.mainContent}>
                    {/* About Us Section */}
                    <section id="about-us" className={styles.section}>
                        <h1 className={styles.title}>About Us</h1>
                        <p className={styles.subtitle}>The name Vitalis comes from the Latin word “Vital,”
                            meaning life, vitality, and what is essential.
                            It represents the core elements that support a healthy, balanced way of living.</p>
                        <p className={styles.subtitle}>At Vitalis, we are dedicated to supporting everyday health and well-being through thoughtfully crafted healthcare and wellness products.</p>

                        <div className={styles.imageContainer}>
                            <Image
                                src="/skincare.jpg"
                                alt="Vitalis Skincare"
                                width={800}
                                height={500}
                                className={styles.image}
                                priority
                            />
                        </div>

                        <h2 className={styles.sectionTitle}>Founded on Passion</h2>
                        <p className={styles.text}>
                            We believe that taking care of your health should be simple, transparent, and accessible. Our focus is on delivering products that complement a healthy lifestyle while maintaining high standards of quality, safety, and integrity.
                        </p>
                    </section>

                    {/* Mission & Vision Section */}
                    <section id="mission-vision" className={styles.section}>
                        <h1 className={styles.title}>Our Mission & Vision</h1>

                        <div className={styles.gridTwoCols}>
                            <div className={styles.card}>
                                <h2 className={styles.sectionTitle}>Our Mission</h2>
                                <p className={styles.text}>
                                    To thoughtfully curate trusted health, beauty, and wellness brands,
                                    empowering individuals to care for themselves with confidence, clarity,
                                    and access to products that truly support everyday well-being.
                                </p>
                            </div>

                            <div className={styles.card}>
                                <h2 className={styles.sectionTitle}>Our Vision</h2>
                                <p className={styles.text}>
                                    To become a refined destination for modern wellness—
                                    where trusted brands, informed choices, and preventive care come together
                                    to support healthier lives, today and in the long term.
                                </p>
                            </div>
                        </div>
                    </section>

                    {/* What We Do Section */}
                    <section id="what-we-do" className={styles.section}>
                        <h1 className={styles.title}>What We Do</h1>
                        <p className={styles.subtitle}>
                            Vitalis is a curated multi-brand wellness store,
                            bringing together trusted healthcare, beauty, and everyday wellness products in one place.

                            We carefully select brands that meet our standards for quality, safety, and effectiveness—
                            so customers can shop with confidence and ease.

                            From daily essentials to long-term well-being,
                            Vitalis makes better health choices simple and accessible.
                        </p>
                    </section>

                    {/* Disclaimer Section */}
                    <section id="disclaimer" className={styles.section}>
                        <h1 className={styles.title}>Medical & Wellness Disclaimer</h1>
                        <p className={`${styles.subtitle} ${styles.disclaimerText}`}>
                            Vitalis provides healthcare and wellness products for general well-being purposes only.
                            Information presented on this website or through our services is not intended to replace professional medical advice, diagnosis, or treatment.
                        </p>
                    </section>
                </main>
            </div>
            <Footer />
        </div>
    );
}
