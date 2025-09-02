import re
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

# ===== Config =====
GLOBAL_MIN_CONFIDENCE = 0.65
STICKY_MIN_CONFIDENCE = 0.50
OVERRIDE_MARGIN = 0.08
SESSION_TIMEOUT_MIN = 15
MAX_CTX_UTTERANCES = 5
RECENCY_ALPHA = 0.70

intent_model = SentenceTransformer("BAAI/bge-m3")

def load_intents(db) -> List[Dict]:
    intents = db.execute(text("""
        SELECT intent_id, name, tool_name
        FROM intents
        ORDER BY intent_id
    """)).mappings().all()

    out = []
    for it in intents:
        phrases = db.execute(text("""
            SELECT phrase
            FROM training_phrases
            WHERE intent_id = :iid
        """), {"iid": it["intent_id"]}).scalars().all()
        if not phrases:
            continue

        vecs = intent_model.encode(
            phrases,
            normalize_embeddings=True,
            convert_to_numpy=True
        )
        intent_vec = np.mean(vecs, axis=0)
        out.append({
            "intent": it["name"],
            "tool": it["tool_name"],
            "embedding": intent_vec
        })
    return out

def match_intent_single(
    user_inputs: List[str],
    intent_data: List[Dict]
) -> Tuple[Optional[str], Optional[str], float]:
    """
    รับเฉพาะ list[str] ของข้อความ human (ล่าสุดก่อน)
    คืน (intent_name | None, tool_name | None, score)
    """
    if not intent_data:
        return None, None, 0.0

    texts = [t.strip() for t in (user_inputs or []) if isinstance(t, str) and t.strip()]
    if not texts:
        return None, None, 0.0

    # ใช้เฉพาะข้อความล่าสุด N อัน
    texts = texts[-MAX_CTX_UTTERANCES:]

    # เข้ารหัสทั้งหมด (ได้เวกเตอร์ normalized)
    vecs = intent_model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)

    # รวมแบบ recency-weighted mean (ใหม่สุดน้ำหนักมากสุด)
    if len(vecs) == 1:
        q = vecs[0]
    else:
        n = len(vecs)
        weights = np.array([RECENCY_ALPHA ** (n - 1 - i) for i in range(n)], dtype=np.float32)
        s = weights.sum()
        if s > 0:
            weights = weights / s
        q = (vecs * weights[:, None]).sum(axis=0)
        # re-normalize กันพลาด
        norm = np.linalg.norm(q)
        if norm > 0:
            q = q / norm

    # เทียบกับ intent embeddings (ควร normalized แล้ว) → ใช้ dot = cosine
    best_score, best_idx = -1.0, None
    for idx, item in enumerate(intent_data):
        s = float(np.dot(q, item["embedding"]))
        if s > best_score:
            best_score, best_idx = s, idx

    if best_idx is None:
        return None, None, 0.0

    item = intent_data[best_idx]
    if best_score >= GLOBAL_MIN_CONFIDENCE:
        return item["intent"], item["tool"], best_score
    return None, None, best_score


def resolve_intent_with_context(
    user_inputs: List[str],
    intent_data: List[Dict],
    session_state: Dict
) -> Tuple[Optional[str], Optional[str], float, str]:
    """
    รับเฉพาะ list[str] ; คืน (intent_name, tool_name, score, source)
    source: "candidate" | "stickiness" | "override"
    """
    # timeout → รีเซ็ต intent เดิม
    last = session_state.get("last_updated")
    if last and isinstance(last, datetime):
        if datetime.now(timezone.utc) - last > timedelta(minutes=SESSION_TIMEOUT_MIN):
            session_state.update({"active_intent": None, "status": "idle"})

    # 1) หาผลผู้สมัคร (candidate)
    cand_intent, cand_tool, cand_score = match_intent_single(user_inputs, intent_data)
    active_intent = session_state.get("active_intent")

    # 2) ถ้ายังไม่มี intent เดิม → ใช้ candidate
    if not active_intent:
        return cand_intent, cand_tool, cand_score, "candidate"

    # 3) หา embedding ของ intent เดิม
    active_tool, active_emb = None, None
    for it in intent_data:
        if it["intent"] == active_intent:
            active_tool, active_emb = it["tool"], it["embedding"]
            break

    # 4) คำนวณเวกเตอร์ q จาก list เดิม (ลอจิกเดียวกับด้านบน)
    texts = [t.strip() for t in (user_inputs or []) if isinstance(t, str) and t.strip()]
    if texts:
        texts = texts[-MAX_CTX_UTTERANCES:]
        vecs = intent_model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        if len(vecs) == 1:
            q = vecs[0]
        else:
            n = len(vecs)
            weights = np.array([RECENCY_ALPHA ** (n - 1 - i) for i in range(n)], dtype=np.float32)
            s = weights.sum()
            if s > 0:
                weights = weights / s
            q = (vecs * weights[:, None]).sum(axis=0)
            norm = np.linalg.norm(q)
            if norm > 0:
                q = q / norm
    else:
        q = None

    baseline = float(np.dot(q, active_emb)) if (q is not None and active_emb is not None) else 0.0

    # 5) กรณีไม่พบ candidate → ยึด intent เดิมเสมอ (stickiness)
    if cand_intent is None:
        return active_intent, active_tool, baseline, "stickiness"

    # 6) มี candidate และคะแนนพอใช้ → ชนะชัดเจนกว่าฐานเดิมค่อย override
    if cand_score >= STICKY_MIN_CONFIDENCE:
        if cand_score >= baseline + OVERRIDE_MARGIN:
            return cand_intent, cand_tool, cand_score, "override"
        else:
            return active_intent, active_tool, max(baseline, cand_score), "stickiness"

    # 7) คะแนนยังไม่ถึง → คง intent เดิม
    return active_intent, active_tool, baseline, "stickiness"