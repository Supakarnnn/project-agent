import asyncio, logging
import torch, json
from typing import Any, Dict, List, Optional
from fastapi import Request, Depends, HTTPException, APIRouter, Header
from fastapi import FastAPI, Response, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage,AIMessage,SystemMessage
from agent.react import react_agent
from agent.module import RequestMessage,ConfigUpdate, LoginIn, IntentCreate, feedbackget
from agent.model import get_current_llm_setting, ChatSession
from connect_milvus import connect_milvus
from pymilvus import utility, Collection, connections
from agent.tool_call import (create_ticket, get_registered_tools, track_order_tool, product_search, create_order, cancel_order, product_detail_search, promotion_search)
from intents.intent_matcher import load_intents, resolve_intent_with_context
from intents.runtime import get_session_state, save_session_state
from log_func.session import autoclose_inactive_sessions, get_or_create_session, update_session_activity, close_session_now, chat_message_log
from log_func.sql_text import ORDER_COMPLETION_SQL, TICKET_CREATE_SQL,AVG_AI_CON_SQL, UNPROCESSED_MESSAGES, INSERT_MESSAGE_INSIGHT, KEYWORD_TOPIC, AVG_SESSION_TIME, UPSERT_FEEDBACK
from log_func.message_insight import extract_insight_with_llm, normalize_insight
from sentiment_model.s_model import detect_sentiment
from auth_admin.auth import verify_password, hash_password
from agent.confident_cal import cal_confidence
from ingest_data_v2 import ingest_promotion_product, ingest_all_product, ingest_detail_product
from contextlib import asynccontextmanager, suppress
from sqlalchemy.orm import Session
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_pg_conn, get_db_session, get_maria_session, get_maria_conn, async_get_pg_conn, AsyncSessionLocal
from admin_function.live_chat import manager
import threading

import urllib3
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
    db.execute(
        text("INSERT INTO llm_configs (model, temperature, top_p, system_prompt) VALUES (:m, :t, :tp, :p)"),
        {"m": req.model, "t": req.temperature, "tp": req.top_p, "p": req.system_prompt}
    )
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
def get_order_complete(db: Session = Depends(get_pg_conn)):
    row = db.execute(ORDER_COMPLETION_SQL).mappings().first()
    return {
        "intent_sessions": int(row["intent_sessions"] or 0),
        "ai_create_order": int(row["ai_create_order"] or 0),
        "complete_rate": float(row["complete_rate"] or 0.0),
    }

@router.get("/get_handoff")
def get_handoff(db: Session = Depends(get_pg_conn)):
    row = db.execute(TICKET_CREATE_SQL).mappings().first()
    return {
        "total_sessions": int(row["total_sessions"] or 0),
        "handoff_sessions": int(row["handoff_sessions"] or 0),
        "handoff_rate": float(row["handoff_rate"] or 0.0),
    }

@router.get("/avg_ai_con")
def avg_ai_con(db: Session = Depends(get_pg_conn)):
    row = db.execute(AVG_AI_CON_SQL).mappings().first()
    return{
        "ai_message_count": int(row["ai_message_count"] or 0),
        "avg_ai_confident": float(row["avg_ai_confident"] * 100 or 0.0)
    }

@router.get("/avg_session_time")
def avg_session_time(db: Session = Depends(get_pg_conn)):
    row = db.execute(AVG_SESSION_TIME).mappings().first()
    return{
        "session_used": int(row["session_used"] or 0),
        "avg_message_count": int(row["avg_message_count"] or 0),
        "avg_session_duration_sec": int(row["avg_session_duration_sec"] or 0),
        "avg_session_duration_min": int(row["avg_session_duration_min"] or 0),
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
    limit: int = Query(50, ge=1, le=500),
    model_name: str = Query("gpt-4o-mini"),
):
    rows = db.execute(UNPROCESSED_MESSAGES, {"limit": limit}).mappings().all()

    messages = [(r.get("human_message") or "").strip() for r in rows]
    messages = [m for m in messages if m]
    if not messages:
        return {"ok": True,"raw": None}

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
    return {"ok": True,"raw": raw}

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

    # print("api message recived")
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

        sentiment = detect_sentiment(last_human_message)
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
    intent_data = await load_intents(db)
    state = await get_session_state(db, session_id)
    intent_name, tool_name, score, source = resolve_intent_with_context(humanmes, intent_data, state)

    tool_registry = {
        "track_order_tool": track_order_tool,
        "create_order": create_order,
        "cancel_order": cancel_order,
        "product_search": product_search,
        "product_detail_search": product_detail_search,
        "promotion_search": promotion_search,
        "create_ticket": create_ticket
    }

    chosen_tools = [
        tool_registry["create_ticket"],
        tool_registry["track_order_tool"],
        tool_registry["product_search"],
        tool_registry["product_detail_search"],
        tool_registry["promotion_search"],
        tool_registry["create_order"],
    ]

    if tool_name and tool_name in tool_registry:
        chosen_tools.append(tool_registry[tool_name])

    # print("session received =", external_session_id)
    #=====================================================================#

    #=============================== SENTIMENT ===========================#
    sentiment = detect_sentiment(last_human_message)
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
    llm, system_prompt = await get_current_llm_setting(db)
    agent = react_agent(llm, chosen_tools, system_prompt)
    result = await agent.ainvoke({"messages": messages, "used_tools": []})
    used_tools = result.get("used_tools", [])

    final_msg: AIMessage = result["messages"][-1]
    final_result: str = final_msg.content
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