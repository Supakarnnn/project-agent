import math
import re
from langchain_core.messages import AIMessage
from typing import List, Dict, Any, Optional

def extract_token_logprobs(ai_msg: AIMessage) -> List[Dict[str, Any]]:
    md = getattr(ai_msg, "response_metadata", {}) or {}
    out: List[Dict[str, Any]] = []

    choices = md.get("choices") or []
    if choices and isinstance(choices, list):
        lp = (choices[0] or {}).get("logprobs") or {}
        content = lp.get("content") or []
        for t in content:
            tok = t.get("token"); lpv = t.get("logprob")
            if tok is None or lpv is None: continue
            row = {"token": tok, "logprob": float(lpv), "prob": math.exp(float(lpv))}
            tops = t.get("top_logprobs") or []
            if tops:
                row["top_logprobs"] = [
                    {
                        "token": tt.get("token"),
                        "logprob": float(tt.get("logprob")),
                        "prob": math.exp(float(tt.get("logprob"))),
                    }
                    for tt in tops
                    if tt.get("token") is not None and tt.get("logprob") is not None
                ]
            out.append(row)

    if not out and isinstance(md.get("logprobs"), dict):
        content = md["logprobs"].get("content") or []
        for t in content:
            tok = t.get("token"); lpv = t.get("logprob")
            if tok is None or lpv is None: continue
            row = {"token": tok, "logprob": float(lpv), "prob": math.exp(float(lpv))}
            tops = t.get("top_logprobs") or []
            if tops:
                row["top_logprobs"] = [
                    {
                        "token": tt.get("token"),
                        "logprob": float(tt.get("logprob")),
                        "prob": math.exp(float(tt.get("logprob"))),
                    }
                    for tt in tops
                    if tt.get("token") is not None and tt.get("logprob") is not None
                ]
            out.append(row)
    return out

PUNCT = {"!", "?", ".", ",", ":", ";", "…", "(", ")", "“", "”", '"', "'"}
def cal_confidence(token_items, drop_punct=True):
    used = []
    for t in token_items:
        tok = (t.get("token") or "").strip()
        p = t.get("prob")
        if tok == "" or p is None:
            continue
        if drop_punct and tok in PUNCT:
            continue
        used.append(float(p))

    if not used:
        return {"avg": None, "min": None, "geom": None, "n_used": 0}

    avg = sum(used) / len(used)
    mn  = min(used)
    geom = math.exp(sum(math.log(x) for x in used) / len(used))
    return {"avg": avg, "min": mn, "geom": geom, "n_used": len(used)}