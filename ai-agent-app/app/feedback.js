"use client";

import { useState } from "react";
import styles from "./feedback.module.css";

const MAX_STARS = 5;

export default function Feedback({ messageId, sessionId }) {
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleClick = async (value) => {
    if (submitted || loading || !messageId) return;

    setLoading(true);
    setRating(value);

    try {
      await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/admin/give_feedback`,
        {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message_id: messageId,
            rating: value,
            session_id: sessionId,
          }),
        }
      );

      setSubmitted(true);
      setHover(0);
    } catch (err) {
      console.error("give_feedback error:", err);
    } finally {
      setLoading(false);
    }
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
              disabled={submitted || loading || !messageId}
              className={`${styles.star} ${isActive ? styles.active : ""}`}
              onClick={() => handleClick(value)}
              onMouseEnter={() => !submitted && setHover(value)}
              onMouseLeave={() => !submitted && setHover(0)}
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
