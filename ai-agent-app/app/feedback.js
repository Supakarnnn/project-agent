"use client";

import { useState } from "react";
import styles from "./feedback.module.css";

const MAX_STARS = 5;

export default function Feedback({ messageId, onRate }) {
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [submitted, setSubmitted] = useState(false);

  const handleClick = async (value) => {
    setRating(value);
    setSubmitted(true);

    if (onRate) {
      onRate({ messageId, rating: value });
    }

    // await fetch("/api/feedback", {
    //   method: "POST",
    //   headers: { "Content-Type": "application/json" },
    //   body: JSON.stringify({ messageId, rating: value }),
    // });
  };

  return (
    <div className={styles.feedbackWrap}>
      <span className={styles.feedbackLabel}>ให้คะแนนคำตอบนี้:</span>
      <div className={styles.stars}>
        {Array.from({ length: MAX_STARS }, (_, idx) => {
          const value = idx + 1;
          const isActive = value <= (hover || rating);
          return (
            <button
              key={value}
              type="button"
              className={`${styles.star} ${isActive ? styles.active : ""}`}
              onClick={() => handleClick(value)}
              onMouseEnter={() => setHover(value)}
              onMouseLeave={() => setHover(0)}
              aria-label={`ให้ ${value} ดาว`}
            >
              {isActive ? "★" : "☆"}
            </button>
          );
        })}
      </div>

      {submitted && (
        <div className={styles.thankyou}>ขอบคุณสำหรับการให้คะแนนค่ะ</div>
      )}
    </div>
  );
}
