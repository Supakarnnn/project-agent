"use client";

import { useRef } from "react";
import styles from "./page.module.css";
import Hero from "./content/hero";
import FiftyFiftySection from "./content/fifty";
import FeaturedProducts from "./content/featured";
import ChatBox from "./content/aichat";
import Navbar from "./navbar";
import Footer from "./content/footer";

export default function Home() {

  const chatRef = useRef(null);
  return (
    <div className={styles.page}>
      <Navbar />

      <main className={styles.main}>
        <Hero />
        <FiftyFiftySection />
        <FeaturedProducts />
        <ChatBox />
      </main>
      <Footer />
    </div>
  );
}
