import os, tempfile, uuid, requests
from datetime import datetime, timezone
from typing import Annotated
from fastapi import Request, Depends, HTTPException, APIRouter
from fastapi.responses import JSONResponse
from bs4 import BeautifulSoup
from fastapi import FastAPI, UploadFile, File, Form
from langchain_community.document_loaders import PyPDFLoader, TextLoader, WebBaseLoader
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage,AIMessage,SystemMessage
from agent.react import react_agent
from agent.module import RequestMessage, CollectionCreate, WebURL, ConfigUpdate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from agent.model import embedding_model, get_current_llm_setting
from langchain_milvus import Milvus
from connect_milvus import connect_milvus
from pymilvus import FieldSchema, CollectionSchema, DataType, Collection, utility
from agent.tool_call import get_registered_tools, track_order_tool, test_list_collections
from sentiment_model.s_model import detect_sentiment
from langchain.tools import Tool

from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_pg_conn
from intents.intent_matcher import load_intents, match_intent

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import dotenv
dotenv.load_dotenv()

app = FastAPI()
router = APIRouter(prefix="/admin", tags=["admin"])
connect_milvus()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@router.get("/config")
def get_config(db: Session = Depends(get_pg_conn)):
    config = db.execute(text("SELECT * FROM llm_configs ORDER BY id DESC LIMIT 1")).mappings().first()
    return config

@router.post("/config")
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
async def chat(chatmessage: RequestMessage, db: Session = Depends(get_pg_conn)):
    messages = []
    humanmes = []
    
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

    intent_data = load_intents(db)
    intent_name, tool_name, score = match_intent(humanmes, intent_data)    
    sentiment = detect_sentiment(last_human_message)
    sentiment_content = ""
    intent_content = ""

    if sentiment == "negative":
        sentiment_content = "ลูกค้าอยู่ในอารมณ์ไม่ดี กรุณาตอบกลับด้วยความสุภาพและช่วยให้เขาใจเย็นลง"
    elif sentiment == "positive":
        sentiment_content = "ลูกค้าอารมณ์ดี สามารถใช้ภาษากระชับหรือแสดงความยินดีได้"
    else:
        sentiment_content = "ลูกค้าอารมณ์ปกติ ตอบกลับได้ตามปกติ"

    if intent_name:
        intent_content =f"Intent: {intent_name}, Tool: {tool_name}"

    messages.insert(0, SystemMessage(content=f"""[INTENT] {intent_content} [SENTIMENT] {sentiment_content}""".strip()))

    tools = [test_list_collections]
    if tool_name == "track_order_tool":
        tools.append(Tool.from_function(track_order_tool, name="track_order_tool", description="เครื่องมือสำหรับติดตามการจัดส่งสิ้นค้า"))

    llm, system_prompt = get_current_llm_setting(db)
    agent = react_agent(llm, tools, system_prompt)
    result = await agent.ainvoke({"messages": messages})
    final_result = result["messages"][-1].content
    
    return {
        "human_message": last_human_message,
        "sentiment_model_message": sentiment_content,
        "response": final_result,
        "sentiment": sentiment,
        "intent_score": float(score) if score else None,
        "full_messages": result["messages"]
    }

@app.get("/")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,host='0.0.0.0',port=8001)