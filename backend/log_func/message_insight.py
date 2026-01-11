import json, dotenv, os
from typing import Any, Dict, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from log_func.sql_text import SYS_PROMPT

dotenv.load_dotenv()

def extract_insight_with_llm(human_message: str) -> Dict[str, Any]:
    hm = (human_message or "").strip()
    # print(hm)
    if not hm:
        return {"topic": [], "keywords": []}

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=os.environ.get("OPENAI_KEY"),
        temperature=0,
        model_kwargs={"response_format": {"type": "json_object"}}
    )

    prompt = (
        "สรุปข้อความทั้งหมดของลูกค้า:\n"
        f"{hm}\n\n"
        'ตอบ JSON ตาม schema เท่านั้น: {"topic":["string"],"keywords":["string"]}'
    )
    resp = llm.invoke([
        SystemMessage(content=SYS_PROMPT.strip()),
        HumanMessage(content=prompt),
    ])
    content = (resp.content or "").strip()
    data = json.loads(content)

    return normalize_insight(data)



def normalize_insight(obj: dict) -> dict:
    topic = obj.get("topic") or []
    keywords = obj.get("keywords") or []

    clean = []
    for k in keywords:
        if not isinstance(k, str):
            continue
        kk = k.strip()
        if not kk:
            continue
        if kk in clean:
            continue
        clean.append(kk)

    clean_topic = []
    for t in topic:
        if not isinstance(t, str):
            continue
        tt = t.strip()
        if not tt:
            continue
        if tt in clean_topic:
            continue
        clean_topic.append(tt)

    clean = clean[:5]
    clean_topic = clean_topic[:5]

    return {"topic": clean_topic, "keywords": clean}