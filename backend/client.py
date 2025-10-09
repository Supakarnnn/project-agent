import asyncio, logging
from typing import Any, Dict, List, Optional
from fastapi import Request, Depends, HTTPException, APIRouter, Header
from fastapi import FastAPI, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage,AIMessage,SystemMessage
from agent.react import react_agent
from agent.module import RequestMessage,ConfigUpdate, LoginIn, IntentCreate
from agent.model import get_current_llm_setting
from connect_milvus import connect_milvus, collection_summary, primary_key_field
from pymilvus import utility, Collection
from agent.tool_call import get_registered_tools, track_order_tool, for_list_collections, product_search, create_order, cancel_order, product_detail_search, promotion_search
from intents.intent_matcher import load_intents, resolve_intent_with_context
from intents.runtime import get_session_state, save_session_state
from log_func.session import autoclose_inactive_sessions, get_or_create_session, update_session_activity, close_session_now
from sentiment_model.s_model import detect_sentiment
from auth_admin.auth import verify_password, hash_password
from agent.confident_cal import extract_token_logprobs, cal_confidence
from contextlib import asynccontextmanager, suppress
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_pg_conn, get_db_session, get_maria_session, get_maria_conn

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import dotenv
dotenv.load_dotenv()

AUTO_CLOSE_EVERY_SEC = 60
async def _auto_close_loop(app):
    while True:
        try:
            db = get_db_session()
            try:
                autoclose_inactive_sessions(db)
            finally:
                db.close()
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

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
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
    return {"ok": True, "name": row["name"], "role": row["role"]}

@auth_router.post("/logout")
def logout(response: Response):
    response.delete_cookie("a_user")
    return {"ok": True}

@auth_router.get("/check")
def check(request: Request):
    user = request.cookies.get("a_user")
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    return {"name": user}

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
def get_tp(db: Session = Depends(get_pg_conn)):
    res = db.execute(text("SELECT tp_id, intent_id, phrase FROM training_phrases")).mappings().all()
    if not res:
        return "Not Found"
    return [dict(r) for r in res]

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
    
@router.get("/collections/{name}")
def get_collection_summary(name: str):
    """สรุปข้อมูลของ collection นั้น (schema, indexes, partitions, loaded, num_entities)"""
    connect_milvus()
    try:
        if not utility.has_collection(name):
            raise HTTPException(404, f"Collection '{name}' not found")
        return collection_summary(name)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"get_collection_summary error: {e}")
    
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

    rows = c.query(
        expr=expr,
        output_fields=[f.name for f in c.schema.fields],
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
 
app.include_router(router)

@app.post("/chat")
async def chat(chatmessage: RequestMessage, db: Session = Depends(get_pg_conn), external_session_id: Optional[str] = Header(None, alias="X-Session-Id"), close_now: Optional[str] = Header(None, alias="X-Close-Session")):
    messages = []
    humanmes = []

    print("X-Session-Id received =", external_session_id)
    autoclose_inactive_sessions(db)
    session_id = get_or_create_session(db, external_session_id)
    
    last_human_message = ""
    for m in reversed(chatmessage.messages):
        if m.role == 'human' and m.content.strip():
            last_human_message = m.content.strip()
            break

    for chat in chatmessage.messages:
        if chat.role == 'ai':
            messages.append(AIMessage(content=chat.content))
        elif chat.role == 'human':
            messages.append(HumanMessage(content=chat.content))
            humanmes.append(chat.content.strip())
        elif chat.role == 'system':
            messages.append(SystemMessage(content=chat.content))

    #========================================================================================================#
    intent_data = load_intents(db)
    state = get_session_state(db, session_id)
    intent_name, tool_name, score, source = resolve_intent_with_context(humanmes, intent_data, state)

    tool_registry = {
        "for_list_collections": for_list_collections,
        "track_order_tool": track_order_tool,
        "create_order": create_order,
        "cancel_order": cancel_order,
        "product_search": product_search,
        "product_detail_search": product_detail_search,
        "promotion_search": promotion_search
    }

    chosen_tools = [tool_registry["product_search"], tool_registry["product_detail_search"], tool_registry["promotion_search"]]
    if tool_name and tool_name in tool_registry:
        chosen_tools.append(tool_registry[tool_name])

    # print(humanmes)
    # print(source)
    # print(score)
    # print(chosen_tools)

    llm, system_prompt = get_current_llm_setting(db)
    tool_names = ", ".join(_tool_name(t) for t in chosen_tools) if chosen_tools else "None"

    intent_prompt_template = f"""[INTENT] {intent_name or 'None'} (confidence={score:.2f}) [ALLOWED_TOOLS] {tool_names}
    [BEHAVIOR RULES]
    - หากตรวจจับได้ว่าเป็นงานเฉพาะ ควรพิจารณาใช้เครื่องมือเฉพาะทางก่อน
    - หากเป็นคำถามทั่วไปหรือยังไม่ชัดเจน ให้ใช้ เครื่องมืออื่น หรือ ถามย้ำเพื่อให้ชัดเจนก่อน
    - หากข้อมูลไม่พอ ให้ถามลูกค้าอย่างสั้น กระชับ และเฉพาะเจาะจงก่อนเรียกใช้เครื่องมือ
    - หลีกเลี่ยงการเดาข้อมูล หากไม่แน่ใจต้องถามย้ำด้วยถ้อยคำสุภาพ
    """.strip()
    #========================================================================================================#

    sentiment = detect_sentiment(last_human_message)
    sentiment_content = ""

    if sentiment == "negative":
        sentiment_content = "ลูกค้าอยู่ในอารมณ์ไม่ดี กรุณาตอบกลับด้วยความสุภาพและช่วยให้เขาใจเย็นลง"
    elif sentiment == "positive":
        sentiment_content = "ลูกค้าอารมณ์ดี สามารถใช้ภาษากระชับหรือแสดงความยินดีได้"
    else:
        sentiment_content = "ลูกค้าอารมณ์ปกติ ตอบกลับได้ตามปกติ"

    messages.insert(1, SystemMessage(content=f"ระบบจับอารมณ์อัตโนมัติ: [SENTIMENT] {sentiment_content}"))
    messages.insert(2, SystemMessage(content=intent_prompt_template))

    #================================================================================#
    agent = react_agent(llm, chosen_tools, system_prompt)
    result = await agent.ainvoke({"messages": messages})
    final_msg: AIMessage = result["messages"][-1]
    final_result: str = final_msg.content
    token_logprobs = extract_token_logprobs(final_msg)
    cal_confidence_from_logprobs = cal_confidence(token_logprobs, drop_punct=True)
    #================================================================================#
    
    state.update({
        "active_intent": intent_name,
        "status": "in_progress" if intent_name else "idle"
    })
    save_session_state(db, session_id, state)

    update_session_activity(db, session_id, add_msg_count=2)
    if (close_now or "").lower() == "true":
        close_session_now(db, session_id)

    return {
        "session_id": str(session_id),
        "human_message": last_human_message,
        "sentiment_model_message": sentiment_content,
        "response": final_result,
        "sentiment": sentiment,
        "intent": intent_name,
        "intent_score": float(score) if score else None,
        "logprobs_summary": {
            "avg_prob": cal_confidence_from_logprobs["avg"],
            "min_prob": cal_confidence_from_logprobs["min"],
            "geom_prob": cal_confidence_from_logprobs["geom"],
            "token_count_used": cal_confidence_from_logprobs["n_used"]
        },
    }

@app.get("/")
async def health_check():
    return {"status": "healthy"}

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

    return out


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,host='0.0.0.0',port=8001)