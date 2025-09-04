import asyncio, logging
import os, tempfile, uuid, requests
from datetime import datetime, timezone
from typing import Annotated, Optional
from fastapi import Request, Depends, HTTPException, APIRouter, Header
from fastapi.responses import JSONResponse
from bs4 import BeautifulSoup
from fastapi import FastAPI, UploadFile, File, Form, Response
from langchain_community.document_loaders import PyPDFLoader, TextLoader, WebBaseLoader
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage,AIMessage,SystemMessage
from agent.react import react_agent
from agent.module import RequestMessage, CollectionCreate, WebURL, ConfigUpdate, LoginIn
from langchain.text_splitter import RecursiveCharacterTextSplitter
from agent.model import embedding_model, get_current_llm_setting
from langchain_milvus import Milvus
from connect_milvus import connect_milvus
from pymilvus import FieldSchema, CollectionSchema, DataType, Collection, utility
from agent.tool_call import get_registered_tools, track_order_tool, for_list_collections, rag_search, create_order
from intents.intent_matcher import load_intents, resolve_intent_with_context, GLOBAL_MIN_CONFIDENCE
from intents.runtime import get_session_state, save_session_state
from log_func.session import autoclose_inactive_sessions, get_or_create_session, update_session_activity, close_session_now
from sentiment_model.s_model import detect_sentiment
from auth_admin.auth import verify_password,hash_password

from contextlib import asynccontextmanager, suppress
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_pg_conn, get_db_session

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

@router.post("/create_collections")
def create_collection(req: CollectionCreate, db: Session = Depends(get_pg_conn)):

    desc = req.description if req.description else f"Collection {req.name}"
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="upload_id", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=req.dim),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=5000),
    ]
    schema = CollectionSchema(fields, description=desc)
    Collection(name=req.name, schema=schema)

    result = db.execute(text("""
        INSERT INTO collections (name, dim, description, created_at)
        VALUES (:name, :dim, :desc, :created_at)
        RETURNING id
    """), {
        "name": req.name,
        "dim": req.dim,
        "desc": desc,
        "created_at": datetime.now(timezone.utc)
    })

    new_id = result.scalar()
    db.commit()

    return {"status": "success", "collection": req.name, "id": new_id, "description": desc}

@router.get("/get-collections")
def list_collections(db: Session = Depends(get_pg_conn)):
    result = db.execute(text("SELECT id, name, dim, description, created_at FROM collections ORDER BY created_at DESC"))
    collections = [dict(row) for row in result.mappings().all()]
    return {"collections": collections}

@router.get("/get-collections-ai")
def list_collections(db: Session = Depends(get_pg_conn)):
    result = db.execute(text("SELECT name, description FROM collections"))
    collections = [dict(row) for row in result.mappings().all()]
    return {"collections": collections}

@router.get("/get-upload_history")
def list_upload_history(collection: str = None, db: Session = Depends(get_pg_conn)):
    if collection:
        result = db.execute(text("""
            SELECT upload_id, collection, filename, timestamp, count
            FROM upload_history
            WHERE collection = :collection
            ORDER BY timestamp DESC
        """), {"collection": collection})
    else:
        result = db.execute(text("""
            SELECT upload_id, collection, filename, timestamp, count
            FROM upload_history
            ORDER BY timestamp DESC
        """))

    uploads = [dict(row) for row in result.mappings().all()]
    return {"upload_history": uploads}

@router.delete("/delete_collections/{name}")
def drop_collection(name: str, db: Session = Depends(get_pg_conn)):
    if utility.has_collection(name):
        utility.drop_collection(name)
    db.execute(text("DELETE FROM upload_history WHERE collection = :name"), {"name": name})
    db.execute(text("DELETE FROM collections WHERE name = :name"), {"name": name})
    db.commit()

    return {"status": "deleted", "collection": name}

@router.delete("/delete_file/{upload_id}")
def delete_uploaded_file(upload_id: str, db: Session = Depends(get_pg_conn)):

    result = db.execute(text("""
        SELECT collection, filename FROM upload_history WHERE upload_id = :upload_id
    """), {"upload_id": upload_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Upload not found")

    collection_name, filename = result

    if utility.has_collection(collection_name):
            collection = Collection(collection_name)
            collection.delete(expr=f"upload_id == '{upload_id}'")

    db.execute(text("DELETE FROM upload_history WHERE upload_id = :upload_id"), {"upload_id": upload_id})
    db.commit()

    return {"status": "deleted", "upload_id": upload_id, "file": filename, "collection": collection_name}

@router.get("/intents/{intent_id}")
def get_intent(intend_id: int, db: Session = Depends(get_pg_conn)):
    res = db.execute(text("SELECT intent_id, name, description, tool_name FROM intents WHERE intent_id = :intent_id"),{"intent_id": intend_id}).mappings().first()
    if not res:
        return "Not Found"
    return dict(res)

@router.get("/training-phrases/{intent_id}")
def get_tp(intent_id: int, db: Session = Depends(get_pg_conn)):
    res = db.execute(text("SELECT tp_id, intent_id, phrase FROM training_phrases WHERE intent_id = :intent_id"),{"intent_id": intent_id}).mappings().all()
    if not res:
        return "Not Found"
    return [dict(r) for r in res]

@router.post("/create-intents")
def create_intent(name: str, tool_name: str, description: str, db: Session = Depends(get_pg_conn)):
    try:
        res = db.execute(
            text("""
                INSERT INTO intents (name, description, tool_name)
                VALUES (:name, :description, :tool_name)
                RETURNING intent_id
            """),
            {"name": name, "description": description, "tool_name": tool_name},
        )
        intent_id = res.scalar()
        db.commit()
        return {"intent_id": intent_id, "name": name, "description": description, "tool_name": tool_name}
        
    except Exception as e:
        db.rollback()
        return f"Cant Update intents {e}"

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

@router.post("/upload-file")
async def upload_file(file: UploadFile = File(...), file_type: str = Form(...), collection_name: str = Form("docs"), db: Session = Depends(get_pg_conn)):
    suffix = ".pdf" if file_type == "pdf" else ".txt"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    if file_type == "pdf":
        loader = PyPDFLoader(tmp_path)
    elif file_type == "text":
        loader = TextLoader(tmp_path, encoding="utf-8")
    else:
        os.remove(tmp_path)
        return {"error": "Unsupported file_type"}

    documents = loader.load()
    os.remove(tmp_path)

    splitter = RecursiveCharacterTextSplitter(chunk_size=1024, chunk_overlap=200)
    chunks = splitter.split_documents(documents)

    upload_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc)

    for c in chunks:
        c.metadata["upload_id"] = upload_id
        c.metadata["filename"] = file.filename

    vectorstore = Milvus(
        embedding_function=embedding_model,
        collection_name=collection_name,
        connection_args={"alias": "default"}
    )
    vectorstore.add_documents(chunks)

    db.execute(text("""
        INSERT INTO upload_history (upload_id, collection, filename, timestamp, count)
        VALUES (:upload_id, :collection, :filename, :timestamp, :count)
    """), {
        "upload_id": upload_id,
        "collection": collection_name,
        "filename": file.filename,
        "timestamp": timestamp,
        "count": len(chunks)
    })

    db.commit()

    return {
        "status": "uploaded",
        "upload_id": upload_id,
        "file": file.filename,
        "chunks": len(chunks)
    }

@router.get("/tools-in-server")
async def tools_in_server():
    return {"available_tools": get_registered_tools()}

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
        "rag_search": rag_search,
        "create_order": create_order,
    }

    chosen_tools = [tool_registry["rag_search"]]
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
    - คุณสามารถใช้เฉพาะเครื่องมือในรายการที่อนุญาต (Allowed Tools) เท่านั้น
    - หากตรวจจับได้ว่าเป็นงานเฉพาะ ควรพิจารณาใช้เครื่องมือเฉพาะทางก่อน
    - หากเป็นคำถามทั่วไปหรือยังไม่ชัดเจน ให้ใช้ rag_search หรือถามย้ำเพื่อให้ชัดเจนก่อน
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

    agent = react_agent(llm, chosen_tools, system_prompt)
    result = await agent.ainvoke({"messages": messages})
    final_result = result["messages"][-1].content
    
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
        "full_messages": result["messages"]
    }

@app.get("/")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,host='0.0.0.0',port=8001)