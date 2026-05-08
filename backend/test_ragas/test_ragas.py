import json
from datetime import datetime

RAGAS_LOG_PATH = "ragas_logsgpt4o-mini.jsonl"

async def log_ragas_row(
    user_input: str,
    retrieved_contexts: list[str],
    ai_query: str,
    response: str,
    reference: str = ""
):
    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_input": user_input,
        "retrieved_contexts": retrieved_contexts,
        "ai_query":ai_query,
        "response": response,
        "reference": reference
    }
    with open(RAGAS_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")