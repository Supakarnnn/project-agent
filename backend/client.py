import os, tempfile, uuid
from datetime import datetime, timezone
import requests
from fastapi import Request
from fastapi.responses import JSONResponse
from bs4 import BeautifulSoup
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, Form
from langchain_community.document_loaders import PyPDFLoader, TextLoader, WebBaseLoader
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage,AIMessage,SystemMessage
from agent.react import react_agent
from agent.prompt import ADMIN
from agent.module import RequestMessage, CollectionCreate, WebURL
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from agent.model import llm,embedding_model
from langchain_milvus import Milvus
from connect_milvus import connect_milvus
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility
from agent.tool_call import rag_search, track_order_tool
from sentiment_model.s_model import detect_sentiment
from langchain.tools import Tool

from sqlalchemy.orm import Session
from intents.database import get_pg_conn
from intents.intent_matcher import load_intents, match_intent

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import dotenv
dotenv.load_dotenv()

app = FastAPI()
db = get_pg_conn()
connect_milvus()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/create_collections")
def create_collection(req: CollectionCreate):
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="upload_id", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=req.dim),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=5000),
    ]
    schema = CollectionSchema(fields, description=f"Collection {req.name}")
    Collection(name=req.name, schema=schema)
    return {"status": "success", "collection": req.name}

@app.get("/collections")
def list_collections():
    return {"collections": utility.list_collections()}

@app.delete("/delete_collections/{name}")
def drop_collection(name: str):
    utility.drop_collection(name)
    return {"status": "deleted", "collection": name}

@app.post("/upload-file")
async def upload_file(file: UploadFile = File(...), file_type: str = Form(...), collection_name: str = Form("docs")):
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
    )
    vectorstore.add_documents(chunks)

    cur = db.cursor()
    cur.execute("""
        INSERT INTO upload_history (upload_id, collection, filename, timestamp, count)
        VALUES (%s, %s, %s, %s, %s)
    """, (upload_id, collection_name, file.filename, timestamp, len(chunks)))
    db.commit()
    cur.close()
    db.close()

    return {"status": "uploaded", "upload_id": upload_id, "file": file.filename}


@app.post("/chat")
async def chat(chatmessage: RequestMessage):
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

    messages.insert(0, SystemMessage(content=f"""
    [INTENT] {intent_content}
    [SENTIMENT] {sentiment_content}""".strip()))

    tools = []
    if tool_name == "track_order_tool":
        tools.append(Tool.from_function(track_order_tool, name="track_order_tool", description="ตรวจสอบสถานะ"))

    agent = react_agent(llm, tools, ADMIN)
    result = await agent.ainvoke({"messages": messages})
    final_result = result["messages"][-1].content

    print(humanmes)
    print(f"intent score {score}")
    
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