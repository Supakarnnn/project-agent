import os, re
import asyncio, logging
import json, httpx, random, string
from typing import Any, Dict, List, Optional
from datetime import date, datetime, time, timedelta
from fastapi import Request, Depends, HTTPException, APIRouter, Header, File, UploadFile
from fastapi import FastAPI, Response, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage,AIMessage,SystemMessage,ToolMessage
from agent.react import react_agent
from agent.module import RequestMessage,ConfigUpdate, LoginIn, IntentCreate, feedbackget, AddProductInput, BulkAddProductInput, REQUIRED_FIELDS
from agent.model import get_current_llm_setting, ChatSession, summary_llm, file_llm
from connect_milvus import connect_milvus
from pymilvus import utility, Collection, connections
from agent.tool_call import (get_brands,create_ticket, get_registered_tools, track_order_tool, suggest_product_search, create_order, cancel_order, product_detail_search, promotion_search)
from intents.intent_matcher import load_intents, resolve_intent_with_context
from intents.runtime import get_session_state, save_session_state
from log_func.session import autoclose_inactive_sessions, get_or_create_session, update_session_activity, close_session_now, chat_message_log
from log_func.sql_text import ORDER_COMPLETION_SQL, TICKET_CREATE_SQL,AVG_AI_CON_SQL, UNPROCESSED_MESSAGES, INSERT_MESSAGE_INSIGHT, KEYWORD_TOPIC, AVG_SESSION_TIME_SQL, UPSERT_FEEDBACK, ORDER_COMPLETION_ALL_SQL, TICKET_CREATE_ALL_SQL
from log_func.sql_text import AVG_AI_CON_ALL_SQL, AVG_SESSION_TIME_ALL_SQL
from log_func.message_insight import extract_insight_with_llm, normalize_insight
from sentiment_model.s_model import detect_sentiment
from auth_admin.auth import verify_password, hash_password
from agent.confident_cal import cal_confidence
from agent.file_ex import extract_text_from_file, ProductList
from ingest_data_v2 import ingest_promotion_product, ingest_all_product, ingest_detail_product
from contextlib import asynccontextmanager, suppress
from sqlalchemy.orm import Session
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_pg_conn, get_db_session, get_maria_session, get_maria_conn, async_get_pg_conn, AsyncSessionLocal
from admin_function.live_chat import manager
import threading
import urllib3
# from test_ragas.test_ragas import log_ragas_row
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import dotenv
dotenv.load_dotenv()

AUTO_CLOSE_EVERY_SEC = 60
_ingest_lock = threading.Lock()

async def _auto_close_loop(app):
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await autoclose_inactive_sessions(db)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("autoclose loop error")

        await asyncio.sleep(AUTO_CLOSE_EVERY_SEC)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.autoclose_task = asyncio.create_task(_auto_close_loop(app))
    try:
        yield
    finally:
        app.state.autoclose_task.cancel()
        with suppress(asyncio.CancelledError):
            await app.state.autoclose_task

app = FastAPI(lifespan=lifespan)
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])
auth_router = APIRouter(prefix="/auth",tags=["admin-auth"])
connect_milvus()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _tool_name(t) -> str:
    return getattr(t, "__name__", getattr(t, "name", "tool"))

@auth_router.post("/register")
def register(name: str, password: str, role: str = "admin", db: Session = Depends(get_pg_conn)):
    exists = db.execute(text("SELECT 1 FROM a_user WHERE name=:n"), {"n": name}).first()
    if exists:
        return "Username already exists"

    hashed = hash_password(password)
    db.execute(
        text("INSERT INTO a_user (name, password, role, is_active) VALUES (:n, :p, :r, TRUE)"),
        {"n": name, "p": hashed, "r": role}
    )
    db.commit()
    return {"ok": True, "msg": f"User {name} registered successfully"}

@auth_router.post("/login")
def login(data: LoginIn, response: Response, db: Session = Depends(get_pg_conn)):
    row = db.execute(
        text("SELECT * FROM a_user WHERE name=:n AND is_active=TRUE"),
        {"n": data.name}
    ).mappings().first()

    if not row or not verify_password(data.password, row["password"]):
        return "Invalid credentials"

    response.set_cookie("a_user", row["name"], httponly=True, samesite="lax")
    response.set_cookie("a_role", row["role"], httponly=True, samesite="lax")
    return {"ok": True, "name": row["name"], "role": row["role"]}

@auth_router.post("/logout")
def logout(response: Response):
    response.delete_cookie("a_user")
    response.delete_cookie("a_role")
    return {"ok": True}

@auth_router.get("/check")
def check(request: Request):
    user = request.cookies.get("a_user")
    role = request.cookies.get("a_role")
    if not user or not role:
        raise HTTPException(status_code=401, detail="Not logged in")
    return {"name": user, "role": role}

app.include_router(auth_router)

@router.get("/config")
def get_config(db: Session = Depends(get_pg_conn)):
    config = db.execute(text("SELECT * FROM llm_configs ORDER BY id DESC LIMIT 1")).mappings().first()
    return config

@router.post("/update-config")
def update_config(req: ConfigUpdate, db: Session = Depends(get_pg_conn)):
    last = db.execute(text("""
        SELECT model, temperature, top_p, system_prompt, fallback_score, fallback_message
        FROM llm_configs
        ORDER BY id DESC
        LIMIT 1
    """)).mappings().first()

    def pick_str(new, old):
        return old if (new is None or new == "") else new

    def pick_num(new, old):
        return old if (new is None) else new

    payload = {
        "m": pick_str(req.model, last["model"]),
        "t": pick_num(req.temperature, last["temperature"]),
        "tp": pick_num(req.top_p, last["top_p"]),
        "p": pick_str(req.system_prompt, last["system_prompt"]),
        "fs": pick_num(req.fallback_score, last["fallback_score"]),
        "fm": pick_str(req.fallback_message, last["fallback_message"]),
    }

    db.execute(text("""
        INSERT INTO llm_configs (model, temperature, top_p, system_prompt, fallback_score, fallback_message)
        VALUES (:m, :t, :tp, :p, :fs, :fm)
    """), payload)

    db.commit()
    return {"message": "updated successfully"}



@router.get("/test-llm")
def test_llm(db: Session = Depends(get_pg_conn)):
    try:
        llm, system_prompt = get_current_llm_setting(db)
        return {
            "status": "success",
            "model": llm.model_name,
            "system_prompt_preview": system_prompt[:100]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/intents")
def get_intent(db: Session = Depends(get_pg_conn)):
    res = db.execute(text("SELECT intent_id, name, description, tool_name FROM intents")).mappings().all()
    if not res:
        return "Not Found"
    return [dict(r) for r in res]

@router.get("/training-phrases")
def get_tp(db: Session = Depends(get_pg_conn), page: int = 1, limit: int = 10):
    offset = (page - 1) * limit
    res = db.execute(text("SELECT tp_id, intent_id, phrase FROM training_phrases LIMIT :limit OFFSET :offset"),
        {
            "limit": limit,
            "offset": offset,
        },).mappings().all()
    
    total = db.execute(
        text("SELECT COUNT(*) FROM training_phrases")
    ).scalar()
    if not res:
        return "Not Found"
    return {
        "page": page,
        "limit": limit,
        "total": total,
        "items": [dict(r) for r in res],
    }

@router.post("/create-intents")
def create_intent(req: IntentCreate, db: Session = Depends(get_pg_conn)):
    try:
        res = db.execute(
            text("""
                INSERT INTO intents (name, description, tool_name)
                VALUES (:name, :description, :tool_name)
                RETURNING intent_id
            """),
            {"name": req.name, "description": req.description, "tool_name": req.tool_name},
        )
        intent_id = res.scalar()
        db.commit()
        return {"intent_id": intent_id, "name": req.name, "description": req.description, "tool_name": req.tool_name}
        
    except Exception as e:
        db.rollback()
        return f"Cant Update intents {e}"
    
@router.delete("/delete-intents/{intent_id}")
def delete_intent(intent_id: int, db: Session = Depends(get_pg_conn)):
    try:
        res = db.execute(
            text("DELETE FROM intents WHERE intent_id = :id RETURNING intent_id"),
            {"id": intent_id},
        ).scalar()

        db.commit()
        return {"deleted": True, "intent_id": res}
    
    except Exception as e:
        db.rollback()
        return f"Cant delete intents {e}"

@router.post("/create-training-phrases")
def create_training_phrases(intent_id: int, phrase: str, db: Session = Depends(get_pg_conn)):
    intent = db.execute(text("SELECT intent_id FROM intents WHERE intent_id = :intent_id"),{"intent_id": intent_id}).first()
    if not intent:
        return "intent id Not exist"
    else:
        res = db.execute(text("INSERT INTO training_phrases (intent_id, phrase) VALUES (:intent_id, :phrase) RETURNING tp_id"),{"intent_id": intent_id, "phrase": phrase})
        tp_id = res.scalar()
        db.commit()
        return {"tp_id": tp_id, "intent_id": intent_id, "phrase": phrase}

@router.delete("/delete-training-phrases/{tp_id}")
def delete_training_phrase(tp_id: int, db: Session = Depends(get_pg_conn)):
    try:
        res = db.execute(
            text("DELETE FROM training_phrases WHERE tp_id = :tp_id"),
            {"tp_id": tp_id},
        )

        db.commit()
        return {"deleted": True, "tp_id": res}
    
    except Exception as e:
        db.rollback()
        return f"Cant delete tp {e}"

@router.get("/tools-in-server")
async def tools_in_server():
    return {"available_tools": get_registered_tools()}

@router.get("/collections")
def list_collections():
    connect_milvus()
    try:
        cols = utility.list_collections()
        return {"collections": cols}
    except Exception as e:
        return {"status": "error", "message": str(e)}
        
@router.get("/collections/{name}/rows")
def get_collection_rows(name: str, page: int = 1, page_size: int = 20):
    connect_milvus()
    if not utility.has_collection(name):
        raise HTTPException(404, f"Collection '{name}' not found")

    c = Collection(name)
    try:
        c.load()
    except Exception:
        pass

    expr = 'pk != ""'

    all_fields = [f.name for f in c.schema.fields]
    exclude = {"raw", "vector"}
    output_fields = [f for f in all_fields if f not in exclude]

    rows = c.query(
        expr=expr,
        output_fields=output_fields,
        limit=page_size,
        offset=(page - 1) * page_size,
    )

    for r in rows:
        v = r.get("vector")
        if isinstance(v, (list, tuple)):
            r["vector_len"] = len(v)
            r["vector"] = list(v[:5])

    return {
        "collection": name,
        "page": page,
        "page_size": page_size,
        "total": c.num_entities,
        "rows": rows,
    }

@router.post("/ingest_promotion")
def ingest_promotion():
    acquired = _ingest_lock.acquire(blocking=False)
    if not acquired:
        raise HTTPException(status_code=409, detail="Ingestion is already running")
    try:
        n = ingest_promotion_product()
        return {"response":"success", "update": n}
    except Exception as e:
        raise e
    finally:
        _ingest_lock.release()
    
@router.post("/ingest_product")
def ingest_product():
    acquired = _ingest_lock.acquire(blocking=False)
    if not acquired:
        raise HTTPException(status_code=409, detail="Ingestion is already running")
    try:
        n = ingest_all_product()
        return {"response":"success", "update": n}
    except Exception as e:
        raise e
    finally:
        _ingest_lock.release()
    
@router.post("/ingest_detail")
def ingest_datail():
    acquired = _ingest_lock.acquire(blocking=False)
    if not acquired:
        raise HTTPException(status_code=409, detail="Ingestion is already running")
    try:
        n = ingest_detail_product()
        return {"response":"success", "update": n}
    except Exception as e:
        raise e
    finally:
        _ingest_lock.release()
    
@router.post("/sessions/{session_id}/takeover")
def takeover_session(session_id: str, db: Session = Depends(get_pg_conn)):
    session: ChatSession | None = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id)
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.mode = "human"
    db.commit()

    return {"success": True, "mode": session.mode}

@router.post("/sessions/{session_id}/back-to-ai")
def back_to_ai(session_id: str, db: Session = Depends(get_pg_conn)):
    session: ChatSession | None = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id)
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.mode = "ai"
    db.commit()

    return {"success": True, "mode": session.mode}

@router.get("/tickets")
def get_tickets(db: Session = Depends(get_pg_conn), page: int = 1, limit: int = 10):
    offset = (page - 1) * limit
    res = db.execute(
        text("""
            SELECT *
            FROM tickets
            WHERE is_active = true
            ORDER BY id DESC
            LIMIT :limit OFFSET :offset
        """),
        {
            "limit": limit,
            "offset": offset,
        },
    ).mappings().all()

    total = db.execute(
        text("SELECT COUNT(*) FROM tickets WHERE is_active = true")
    ).scalar()

    if not res:
        return "Not Found"
    return {
        "page": page,
        "limit": limit,
        "total": total,
        "items": [dict(r) for r in res],
    }

@router.post("/tickets/{ticket_id}/close")
def close_ticket(ticket_id: int, db: Session = Depends(get_pg_conn)):
    res = db.execute(
        text("""
            UPDATE tickets
            SET is_active = false
            WHERE id = :id
            RETURNING id
        """),
        {"id": ticket_id},
    ).fetchone()

    if not res:
        raise HTTPException(status_code=404, detail="Ticket not found")

    db.commit()
    return {"ok": True, "ticket_id": ticket_id}

@router.get("/open-session")
def open_session(db: Session = Depends(get_pg_conn), page: int = 1, limit: int = 10):
    offset = (page - 1) * limit
    res = db.execute(
        text("""
            SELECT *
            FROM chat_sessions
            ORDER BY id DESC
            LIMIT :limit OFFSET :offset
        """),
        {
            "limit": limit,
            "offset": offset,
        },
    ).mappings().all()

    total = db.execute(
        text("SELECT COUNT(*) FROM chat_sessions")
    ).scalar()

    if not res:
        return "Not Found"
    return {
        "page": page,
        "limit": limit,
        "total": total,
        "items": [dict(r) for r in res],
    }

@router.get("/chat_log")
def chat_log(db: Session = Depends(get_pg_conn), page: int = 1, limit: int = 20):
    offset = (page - 1) * limit
    res = db.execute(
        text("""
            SELECT *
            FROM chat_messages
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {
            "limit": limit,
            "offset": offset,
        },
    ).mappings().all()

    total = db.execute(
        text("SELECT COUNT(*) FROM chat_messages")
    ).scalar()

    if not res:
        return "Not Found"
    return {
        "page": page,
        "limit": limit,
        "total": total,
        "items": [dict(r) for r in res],
    }

@router.get("/get_order_complete")
def get_order_complete(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_pg_conn),
):
    if not start_date or not end_date:
        row = db.execute(ORDER_COMPLETION_ALL_SQL).mappings().first()
    else:
        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time(23, 59, 59))

        row = db.execute(
            ORDER_COMPLETION_SQL,
            {
                "start_date": start_dt,
                "end_date": end_dt,
            },
        ).mappings().first()

    return {
        "intent_sessions": int(row["intent_sessions"] or 0),
        "ai_create_order": int(row["ai_create_order"] or 0),
        "complete_rate": float(row["complete_rate"] or 0.0),
    }

@router.get("/get_handoff")
def get_handoff(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_pg_conn),
):
    if not start_date or not end_date:
        row = db.execute(TICKET_CREATE_ALL_SQL).mappings().first()
    else:
        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time(23, 59, 59))

        row = db.execute(
            TICKET_CREATE_SQL,
            {
                "start_date": start_dt,
                "end_date": end_dt,
            },
        ).mappings().first()

    return {
        "total_sessions": int(row["total_sessions"] or 0),
        "handoff_sessions": int(row["handoff_sessions"] or 0),
        "handoff_rate": float(row["handoff_rate"] or 0.0),
    }

@router.get("/avg_ai_con")
def avg_ai_con(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_pg_conn),
):
    if not start_date or not end_date:
        row = db.execute(AVG_AI_CON_ALL_SQL).mappings().first()
    else:
        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time(23, 59, 59))

        row = db.execute(
            AVG_AI_CON_SQL,
            {
                "start_date": start_dt,
                "end_date": end_dt,
            },
        ).mappings().first()

    avg_ai_confident = float((row["avg_ai_confident"] or 0.0) * 100)

    return {
        "ai_message_count": int(row["ai_message_count"] or 0),
        "avg_ai_confident": avg_ai_confident,
    }

@router.get("/avg_session_time")
def avg_session_time(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_pg_conn),
):
    if not start_date or not end_date:
        row = db.execute(AVG_SESSION_TIME_ALL_SQL).mappings().first()
    else:
        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time(23, 59, 59))

        row = db.execute(
            AVG_SESSION_TIME_SQL,
            {
                "start_date": start_dt,
                "end_date": end_dt,
            },
        ).mappings().first()

    return {
        "session_used": int(row["session_used"] or 0),
        "avg_message_count": float(row["avg_message_count"] or 0.0),
        "avg_session_duration_sec": float(row["avg_session_duration_sec"] or 0.0),
        "avg_session_duration_min": float(row["avg_session_duration_min"] or 0.0),
    }

@router.get("/get_key_top")
def get_key_top(db: Session = Depends(get_pg_conn)):
    row = db.execute(KEYWORD_TOPIC).mappings().first()
    return{
        "a_topic": row["topic"],
        "a_key": row["keywords"]
    }

@router.post("/run_llm_insight")
def run_llm_insight(
    db: Session = Depends(get_pg_conn),
    limit: int = Query(300, ge=1, le=500),
    model_name: str = Query("gpt-4o-mini"),
):
    rows = db.execute(UNPROCESSED_MESSAGES, {"limit": limit}).mappings().all()

    print("rows from db =", len(rows))

    messages = [(r.get("human_message") or "").strip() for r in rows]
    messages = [m for m in messages if m]

    if not messages:
        return {"ok": True, "raw": None}

    combined = "\n\n---\n\n".join(messages)
    raw = extract_insight_with_llm(combined)
    insight = normalize_insight(raw)

    db.execute(
        INSERT_MESSAGE_INSIGHT,
        {
            "topic": json.dumps(insight["topic"], ensure_ascii=False),
            "keywords": json.dumps(insight["keywords"], ensure_ascii=False),
            "model_name": model_name,
        },
    )

    db.commit()
    return {"ok": True, "raw": raw}

@router.post("/give_feedback")
def give_feedback(data: feedbackget, db: Session = Depends(get_pg_conn)):
    print(data)
    try:
        row = db.execute(
            UPSERT_FEEDBACK,
            {
                "message_id": data.message_id,
                "rating": data.rating,
                "session_id": data.session_id,
            }
        ).mappings().first()
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    
    return {"ok": True, "feedback": dict(row)}

@router.post("/extract_file", response_model=ProductList)
async def extract_file(file: UploadFile = File(...)):
    
    if not (file.filename.lower().endswith(".pdf") or file.filename.lower().endswith(".txt")):
        raise HTTPException(status_code=400, detail="รองรับเฉพาะไฟล์ .pdf และ .txt เท่านั้น")
    
    raw_text = await extract_text_from_file(file)
    # print(raw_text)
    
    if not raw_text:
        raise HTTPException(status_code=400, detail="ไม่พบข้อความในไฟล์นี้ หรือไฟล์ว่างเปล่า")

    prompt = f"""You are a product data extraction specialist. Carefully read the text below and extract every product mentioned.

Important rules:
- All output must be in Thai, except name_eng which must be in English.
- name: Product name (Thai only).
- name_eng: Product name (English only).
- detail: Full product description — write comprehensively, do not shorten.
- category_l1: Main category (e.g. skincare, makeup, supplement)
- category_l2: Sub-category (e.g. serum, sunscreen, cleanser)
- key_features: **CRITICAL — must be thorough and detailed.** List ALL key features, highlights, benefits, and selling points mentioned in the document. Do NOT summarize briefly.
- Do NOT fabricate or hallucinate any data. If information is not found in the document, use "-".
- Extract as completely as possible from the document. Do NOT truncate, abbreviate, or summarize.
- Do NOT use bullet points, dashes, numbering, or any special symbols in the output. Write in plain text only, use ", " (comma and space) to separate multiple items.
- notes: Any additional notes (if available)

---
{raw_text}"""

    # print(raw_text)
    
    try:
        structured_llm = file_llm.with_structured_output(ProductList)
        result = structured_llm.invoke(prompt)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดจาก AI: {str(e)}")

def parse_google_url(url: str):
    """Extract doc_id and doc_type (docs/sheets) from a Google Docs/Sheets URL."""
    docs_match = re.search(r"docs\.google\.com/document/d/([a-zA-Z0-9_-]+)", url)
    if docs_match:
        return docs_match.group(1), "docs"

    sheets_match = re.search(r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if sheets_match:
        return sheets_match.group(1), "sheets"

    return None, None

@router.post("/google_extract_file", response_model=ProductList)
async def google_extract_file(url: str = Query(..., description="Google Docs or Sheets URL")):
    doc_id, doc_type = parse_google_url(url)

    if not doc_id:
        raise HTTPException(status_code=400, detail="URL ไม่ถูกต้อง กรุณาใส่ลิงก์ Google Docs หรือ Google Sheets")

    if doc_type == "docs":
        export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    else:
        export_url = f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv"

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        try:
            res = await client.get(export_url)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"ไม่สามารถเชื่อมต่อ Google ได้: {str(e)}")

    if res.status_code != 200:
        raise HTTPException(status_code=400, detail=f"ไม่สามารถดึงข้อมูลจากลิงก์นี้ได้ (status {res.status_code}) — กรุณาตรวจสอบว่าไฟล์เปิดสาธารณะ")

    raw_text = res.text.strip()

    if not raw_text:
        raise HTTPException(status_code=400, detail="ไม่พบข้อความในเอกสารนี้ หรือเอกสารว่างเปล่า")

    prompt = f"""You are a product data extraction specialist. Carefully read the text below and extract every product mentioned.

Important rules:
- All output must be in Thai, except name_eng which must be in English.
- name: Product name (Thai only).
- name_eng: Product name (English only).
- detail: Full product description — write comprehensively, do not shorten.
- category_l1: Main category (e.g. skincare, makeup, supplement)
- category_l2: Sub-category (e.g. serum, sunscreen, cleanser)
- key_features: **CRITICAL — must be thorough and detailed.** List ALL key features, highlights, benefits, and selling points mentioned in the document. Do NOT summarize briefly.
- Do NOT fabricate or hallucinate any data. If information is not found in the document, use "-".
- Extract as completely as possible from the document. Do NOT truncate, abbreviate, or summarize.
- Do NOT use bullet points, dashes, numbering, or any special symbols in the output. Write in plain text only, use ", " (comma and space) to separate multiple items.
- notes: Any additional notes (if available)

---
{raw_text}"""

    try:
        structured_llm = file_llm.with_structured_output(ProductList)
        result = structured_llm.invoke(prompt)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดจาก AI: {str(e)}")

def generate_product_code() -> str:
    part1 = ''.join(random.choices(string.ascii_uppercase, k=3))
    part2 = ''.join(random.choices(string.ascii_uppercase, k=3))
    part3 = ''.join(random.choices(string.digits, k=3))
    return f"{part1}-{part2}-{part3}"

@router.post("/add_product")
async def add_product(data: AddProductInput):
    code = generate_product_code()

    payload_api1 = {
        "ProductName": data.name,
        "ProductName_Eng": data.name_eng,
        "PricePerUnit": data.cost,
        "ProductDetail": data.detail,
        "is_stock": "T",
        "is_overstock": "F",
        "code": code,
        "barcode": code,
    }

    payload_api2 = {
        "store_id": 1,
        "name": data.name,
        "name_eng": data.name_eng,
        "cost": data.cost,
        "detail": data.detail,
        "code": code,
        "barcode": code,
        "stock_qty": data.stock_qty,
        "brand": data.brand,
        "category_l1": data.category_l1,
        "category_l2": data.category_l2,
        "key_features": data.key_features,
        "key_ingredients": data.key_ingredients,
        "suitable_for_concern": data.suitable_for_concern,
        "size_volume": data.size_volume,
        "usage_instructions": data.usage_instructions,
        "notes": data.notes,
    }

    headers = {
        "Authorization": f"Bearer {os.getenv("SAVE_TOKEN")}",
        "Content-Type": "application/json",
    }

    results = {}
    
    # print("=== payload_api1 ===", json.dumps(payload_api1, ensure_ascii=False, indent=2))
    # print("=== payload_api2 ===", json.dumps(payload_api2, ensure_ascii=False, indent=2))
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            res1 = await client.post(os.getenv("SAVE_PRODUCT_API"), json=payload_api1, headers=headers)
            # print("=== res_api1 ===", res1.status_code, res1.text)
            results["api1"] = {"status": res1.status_code, "body": res1.json() if res1.status_code == 200 else res1.text}
        except Exception as e:
            results["api1"] = {"status": "error", "body": str(e)}

        try:
            res2 = await client.post(os.getenv("SAVE_MAT_API"), json=payload_api2, headers=headers)
            # print("=== res_api2 ===", res2.status_code, res2.text)
            results["api2"] = {"status": res2.status_code, "body": res2.json() if res2.status_code == 200 else res2.text}
        except Exception as e:
            results["api2"] = {"status": "error", "body": str(e)}

    return {
        "ok": True,
        "code": code,
        "results": results,
    }
@router.post("/bulk_add_products")
async def bulk_add_products(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
 
    products_raw = body if isinstance(body, list) else body.get("products")
    if not isinstance(products_raw, list) or len(products_raw) == 0:
        raise HTTPException(status_code=400, detail="Body must be a non-empty list of products")
 
    errors = []
    for i, row in enumerate(products_raw):
        missing = REQUIRED_FIELDS - set(row.keys())
        if missing:
            errors.append({"row": i + 1, "missing_fields": sorted(missing)})
 
    if errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "Missing required fields", "errors": errors},
        )
 
    try:
        data = BulkAddProductInput(products=products_raw)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
 
    headers = {
        "Authorization": f"Bearer {os.getenv('SAVE_TOKEN')}",
        "Content-Type": "application/json",
    }
 
    results = []
 
    async with httpx.AsyncClient(timeout=30) as client:
        for item in data.products:
            code = generate_product_code()
 
            payload_api1 = {
                "ProductName": item.name,
                "ProductName_Eng": item.name_eng,
                "PricePerUnit": item.cost,
                "ProductDetail": item.detail,
                "is_stock": "T",
                "is_overstock": "F",
                "code": code,
                "barcode": code,
            }
 
            payload_api2 = {
                "store_id": 1,
                "name": item.name,
                "name_eng": item.name_eng,
                "cost": item.cost,
                "detail": item.detail,
                "code": code,
                "barcode": code,
                "stock_qty": item.stock_qty,
                "brand": item.brand,
                "category_l1": item.category_l1,
                "category_l2": item.category_l2,
                "key_features": item.key_features,
                "key_ingredients": item.key_ingredients,
                "suitable_for_concern": item.suitable_for_concern,
                "size_volume": item.size_volume,
                "usage_instructions": item.usage_instructions,
                "notes": item.notes,
            }
 
            item_result = {"name": item.name, "code": code, "api1": {}, "api2": {}}
 
            try:
                res1 = await client.post(os.getenv("SAVE_PRODUCT_API"), json=payload_api1, headers=headers)
                item_result["api1"] = {"status": res1.status_code, "body": res1.json() if res1.status_code == 200 else res1.text}
            except Exception as e:
                item_result["api1"] = {"status": "error", "body": str(e)}
 
            try:
                res2 = await client.post(os.getenv("SAVE_MAT_API"), json=payload_api2, headers=headers)
                item_result["api2"] = {"status": res2.status_code, "body": res2.json() if res2.status_code == 200 else res2.text}
            except Exception as e:
                item_result["api2"] = {"status": "error", "body": str(e)}
 
            ok = item_result["api1"].get("status") == 200 and item_result["api2"].get("status") == 200
            item_result["ok"] = ok
            results.append(item_result)
 
    return {
        "ok": True,
        "total": len(results),
        "success": sum(1 for r in results if r["ok"]),
        "failed": sum(1 for r in results if not r["ok"]),
        "results": results,
    }

app.include_router(router)

@app.post("/chat")
async def chat(
    chatmessage: RequestMessage,
    db: AsyncSession = Depends(async_get_pg_conn),
    external_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    close_now: Optional[str] = Header(None, alias="X-Close-Session"),
):
        
    messages = []
    humanmes = []
    aimanmes = []
    await autoclose_inactive_sessions(db)
    session_id = await get_or_create_session(db, external_session_id)
    log_session_id = str(session_id)
    
    last_human_message = ""
    for m in reversed(chatmessage.messages):
        if m.role == 'human' and m.content.strip():
            last_human_message = m.content.strip()
            break

    for chat in chatmessage.messages:
        if chat.role == 'ai':
            messages.append(AIMessage(content=chat.content))
            aimanmes.append(chat.content.strip())
        elif chat.role == 'human':
            messages.append(HumanMessage(content=chat.content))
            humanmes.append(chat.content.strip())
        elif chat.role == 'system':
            messages.append(SystemMessage(content=chat.content))

    print("api message recived")
    #================================ CHECK CALL_CENTER OR AI PATH =====================#
    session_row_result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session_row = session_row_result.scalars().first()
    ws_room_id = external_session_id or str(session_id)
    session_mode = session_row.mode if session_row and session_row.mode else "ai"

    # ถ้าอยู่ในโหมด human → ไม่เรียก AI, broadcast ให้ agent อย่างเดียว
    if session_mode == "human":
        print(f"[SESSION {session_id}] mode = human → skip LLM")

        # broadcast ข้อความของลูกค้าให้ agent ผ่าน WebSocket
        if last_human_message:
            await manager.broadcast(ws_room_id, {
                "sender": "user",
                "content": last_human_message,
                "source": "http",
            })

        sentiment = await detect_sentiment(humanmes)
        if sentiment == "negative":
            sentiment_content = "ลูกค้าอยู่ในอารมณ์ไม่ดี กรุณาตอบกลับด้วยความสุภาพและช่วยให้เขาใจเย็นลง"
        elif sentiment == "positive":
            sentiment_content = "ลูกค้าอารมณ์ดี สามารถใช้ภาษากระชับหรือแสดงความยินดีได้"
        else:
            sentiment_content = "ลูกค้าอารมณ์ปกติ ตอบกลับได้ตามปกติ"

        return {
            "session_id": str(session_id),
            "human_message": last_human_message,
            "sentiment_model_message": sentiment_content,
            "response": None,
            "sentiment": sentiment,
            "intent": None,
            "tool_used": [],
            "intent_score": None,
            "ai confident (avg probability)": None,
            "mode": "human"
        }

    #================================ INTENT & TOOLS =====================#
    print("intent load start")
    intent_data = await load_intents(db)
    print("intent load end")
    state = await get_session_state(db, session_id)
    print("resolve_intent_with_context start")
    intent_name, tool_name, score, source = await asyncio.to_thread(resolve_intent_with_context, humanmes, intent_data, state)
    print("resolve_intent_with_context end")

    tool_registry = {
        "track_order_tool": track_order_tool,
        "create_order": create_order,
        "cancel_order": cancel_order,
        "suggest_product_search": suggest_product_search,
        "product_detail_search": product_detail_search,
        "promotion_search": promotion_search,
        "create_ticket": create_ticket,
        "get_brands": get_brands
    }

    chosen_tools = [
        tool_registry["create_ticket"],
        tool_registry["track_order_tool"],
        tool_registry["suggest_product_search"],
        tool_registry["product_detail_search"],
        tool_registry["promotion_search"],
        tool_registry["create_order"],
        tool_registry["get_brands"]
    ]

    if tool_name and tool_name in tool_registry:
        chosen_tools.append(tool_registry[tool_name])

    # print("session received =", external_session_id)
    #=====================================================================#

    #=============================== SENTIMENT ===========================#
    print("sentiment start")
    sentiment = await detect_sentiment(humanmes)
    print("sentiment = ", sentiment)
    print("sentiment end")
    if sentiment == "negative":
        sentiment_content = "ลูกค้าอยู่ในอารมณ์ไม่ดี กรุณาตอบกลับด้วยความสุภาพและช่วยให้ลูกค้าใจเย็นลง"
    elif sentiment == "positive":
        sentiment_content = "ลูกค้าอารมณ์ดี"
    else:
        sentiment_content = "ลูกค้าอารมณ์ปกติ ตอบกลับได้ตามปกติ"

    intent_prompt_template = ( f"""ระบบจับ Intent อัตโนมัติ: [INTENT MATCHER] {intent_name or 'None'}""").strip()
    messages.insert(1, SystemMessage(content=f"ระบบจับอารมณ์อัตโนมัติ: [SENTIMENT] {sentiment_content}"))
    messages.insert(2, SystemMessage(content=intent_prompt_template))
    messages.insert(3, SystemMessage(content=f"SESSION_ID FOR THIS CONVERSATION = {session_id}"))
    #=====================================================================#

    #============================= LLM AGENT =============================#
    cfg = await get_current_llm_setting(db)
    llm = cfg["llm"]
    system_prompt = cfg["system_prompt"]
    fallback_score = cfg["fallback_score"]
    fallback_message = cfg["fallback_message"]
    print("react_agent start")
    agent = react_agent(llm, chosen_tools, system_prompt)
    result = await agent.ainvoke({"messages": messages, "used_tools": []})
    used_tools = result.get("used_tools", [])

    final_msg: AIMessage = result["messages"][-1]
    final_result: str = final_msg.content
    print("react_agent end")
    #============================RAGAS====================================#
    # RAG_TOOLS = {"suggest_product_search", "product_detail_search", "promotion_search"}
    # retrieved_contexts = []
    # for msg in result["messages"]:
    #     if isinstance(msg, ToolMessage) and msg.name in RAG_TOOLS:
    #         retrieved_contexts.append(msg.content)
            
    # tool_queries = {}
    # for msg in result["messages"]:
    #     if hasattr(msg, "tool_calls"):
    #         for tc in msg.tool_calls:
    #             if tc["name"] in RAG_TOOLS:
    #                 tool_queries[tc["name"]] = tc["args"].get("query") or tc["args"].get("name", "")
            
    # if retrieved_contexts:
    #     await log_ragas_row(
    #         user_input=last_human_message,
    #         ai_query=tool_queries,
    #         retrieved_contexts=retrieved_contexts,
    #         response=final_result
    #     )
    #=====================================================================#
    
    #======================CHECK TOKEN===================================#
    # print("usage_metadata:", final_msg.usage_metadata)
    #=====================================================================#

    #=========================== CONFIDENCE ==============================#
    single_log = final_msg.response_metadata["logprobs"]["content"]
    num_tokens = len(single_log)
    total_logprob = sum(t["logprob"] for t in single_log)
    avg_logprob = total_logprob / num_tokens
    prob = cal_confidence(avg_logprob)
    #=====================================================================#
    
    state.update({
        "active_intent": intent_name,
        "status": "in_progress" if intent_name else "idle"
    })
    await save_session_state(db, session_id, state)

    await update_session_activity(db, session_id, add_msg_count=2)
    if (close_now or "").lower() == "true":
        await close_session_now(db, session_id)
        
    #fallback message
    if fallback_score > prob:
        final_result = fallback_message
        
    ai_message_id = await chat_message_log(
        db,
        session_id=log_session_id,
        human_message=last_human_message,
        ai_message=final_result,
        sentiment=sentiment,
        intent_name=intent_name,
        intent_score=float(score),
        used_tools=used_tools or [],
        ai_confident=float(prob)
    )
    
    return {
        "session_id": str(session_id),
        "human_message": last_human_message,
        "sentiment_model_message": sentiment_content,
        "ai_message_id": ai_message_id,
        "response": final_result,
        "sentiment": sentiment,
        "intent": intent_name,
        "tool_used": used_tools,
        "intent_score": float(score) if score else None,
        "ai confident (avg probability)" : float(prob),
    }

@app.get("/")
async def health_check():
    return {"status": "healthy"}

@app.get("/check_payment")
async def check_payment(
    code: str = Query(..., description="หมายเลขคำสั่งซื้อ"),
    db: Session = Depends(get_maria_conn),):
    sql = text("""
        SELECT 
            name,
            tel,
            code,
            discountdetail,
            shipping,
            pay_amount,
            shipping_code,
            address,
            province,
            district,
            subdistrict,
            zipcode,
            postatus
        FROM tbl_so
        WHERE code = :code
        LIMIT 1
    """)

    result = db.execute(sql, {"code": code}).mappings().first()

    if not result:
        raise HTTPException(status_code=404, detail="ไม่พบหมายเลขคำสั่งซื้อในระบบ")

    return {
        "success": True,
        "data": dict(result),
    }

@app.get("/test-db")
def test_both(pg: Session = Depends(get_pg_conn), maria: Session = Depends(get_maria_conn)):
    out = {}
    # PG
    try:
        ver = pg.execute(text("SELECT version()")).scalar()
        out["postgres"] = {"ok": True, "version": ver}
    except Exception as e:
        out["postgres"] = {"ok": False, "error": str(e)}

    # MariaDB
    try:
        ver = maria.execute(text("SELECT VERSION()")).scalar()
        out["mariadb"] = {"ok": True, "version": ver}
    except Exception as e:
        out["mariadb"] = {"ok": False, "error": str(e)}

    # GPU
    try:
        import torch
        if torch.cuda.is_available():
            out["gpu"] = {
                "ok": True,
                "device_count": torch.cuda.device_count(),
                "name": torch.cuda.get_device_name(0),
                "torch_version": torch.__version__,
            }
        else:
            out["gpu"] = {"ok": False, "error": "CUDA not available"}
    except Exception as e:
        out["gpu"] = {"ok": False, "error": str(e)}

    # Milvus
    try:
        connect_milvus()
        cols = utility.list_collections()
        out["milvus"] = {"ok": True, "collections": cols[:5]}
    except Exception as e:
        out["milvus"] = {"ok": False, "error": str(e)}
    finally:
        try:
            connections.disconnect("default")
        except Exception:
            pass

    return out

@app.websocket("/ws/{session_id}/{role}")
async def ws_endpoint(websocket: WebSocket, session_id: str, role: str):
    if role not in ("user", "agent"):
        await websocket.close()
        return

    await manager.connect(session_id, role, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            content = data.get("content", "")
            sender = data.get("sender", role)

            msg = {
                "session_id": session_id,
                "sender": sender,  # user / agent / ai
                "content": content,
                "source": "ws",
            }
            await manager.broadcast(session_id, msg)

    except WebSocketDisconnect:
        manager.disconnect(session_id, role, websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,host='0.0.0.0',port=8001)