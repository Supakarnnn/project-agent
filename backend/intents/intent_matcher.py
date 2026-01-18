import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from sentence_transformers import SentenceTransformer
from sqlalchemy.ext.asyncio import AsyncSession
from agent.model import embedding_model

GLOBAL_MIN_CONFIDENCE = 0.60
STICKY_MIN_CONFIDENCE = 0.50
OVERRIDE_MARGIN = 0.08
SESSION_TIMEOUT_MIN = 15
MAX_CTX_UTTERANCES = 5
RECENCY_ALPHA = 0.70

intent_model = embedding_model

async def load_intents(db: AsyncSession) -> List[Dict]:

    query = text("""
        SELECT i.intent_id, i.name, i.tool_name, tp.phrase
        FROM intents i
        JOIN training_phrases tp ON i.intent_id = tp.intent_id
        ORDER BY i.intent_id
    """)
    result = await db.execute(query)
    rows = result.mappings().all()

    temp_data = {}
    for r in rows:
        iid = r["intent_id"]
        if iid not in temp_data:
            temp_data[iid] = {
                "name": r["name"],
                "tool": r["tool_name"],
                "phrases": []
            }
        if r["phrase"] and r["phrase"].strip():
            temp_data[iid]["phrases"].append(r["phrase"])

    if not temp_data:
        return []

    all_phrases = []
    intent_map = []

    sorted_keys = sorted(temp_data.keys())
    
    for key in sorted_keys:
        phrases = temp_data[key]["phrases"]
        if not phrases:
            continue
        all_phrases.extend(phrases)
        intent_map.append((key, len(phrases)))

    if not all_phrases:
        return []

    list_of_vectors = intent_model.embed_documents(all_phrases)
    all_vecs = np.array(list_of_vectors, dtype=np.float32)

    out: List[Dict] = []
    cursor = 0
    
    for (iid, count) in intent_map:
        vecs_chunk = all_vecs[cursor : cursor + count]
        cursor += count

        intent_vec = np.mean(vecs_chunk, axis=0)

        norm = np.linalg.norm(intent_vec)
        if norm > 0:
            intent_vec = intent_vec / norm

        item = temp_data[iid]
        out.append({
            "intent": item["name"],
            "tool": item["tool"],
            "embedding": intent_vec,
        })

    return out

def match_intent_single(
    user_inputs: List[str],
    intent_data: List[Dict]
) -> Tuple[Optional[str], Optional[str], float]:

    if not intent_data or not user_inputs:
        return None, None, 0.0

    last_text = user_inputs[-1]
    if not isinstance(last_text, str) or not last_text.strip():
        return None, None, 0.0

    vecs = intent_model.embed_documents([last_text])
    query_vec = np.array(vecs[0], dtype=np.float32)

    #Compare with all intents (Dot Product)
    best_score = -1.0
    best_item = None

    for item in intent_data:
        score = float(np.dot(query_vec, item["embedding"]))
        if score > best_score:
            best_score = score
            best_item = item

    if best_item and best_score >= GLOBAL_MIN_CONFIDENCE:
        return best_item["intent"], best_item["tool"], best_score
        
    return None, None, best_score

def resolve_intent_with_context(
    user_inputs: List[str],
    intent_data: List[Dict],
    session_state: Dict
) -> Tuple[Optional[str], Optional[str], float, str]:
    """
    Simplified Logic:
    1. Check Timeout
    2. Try to match NEW message
    3. If High Score -> Switch Intent
    4. If Low Score -> Keep Old Intent (if exists)
    """
    
    last = session_state.get("last_updated")
    if last and isinstance(last, datetime):
        if datetime.now(timezone.utc) - last > timedelta(minutes=SESSION_TIMEOUT_MIN):
            session_state.update({"active_intent": None})

    active_intent = session_state.get("active_intent")

    cand_intent, cand_tool, cand_score = match_intent_single(user_inputs, intent_data)

    if cand_intent:
        return cand_intent, cand_tool, cand_score, "new_match"

    if active_intent:
        old_tool = next((i["tool"] for i in intent_data if i["intent"] == active_intent), None)
        return active_intent, old_tool, 0.0, "continue"

    return None, None, 0.0, "unknown"