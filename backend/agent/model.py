import os
import torch
import json
import uuid
import dotenv
from langchain_community.embeddings import DeepInfraEmbeddings
from sqlalchemy.orm import Session
from sqlalchemy import text, Text, Boolean
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.asyncio import AsyncSession


dotenv.load_dotenv()

async def get_current_llm_setting(db: AsyncSession):
    result = await db.execute(text("""
        SELECT *
        FROM llm_configs
        ORDER BY id DESC
        LIMIT 1
    """))
    config = result.mappings().first()

    if not config:
        # กันเคสตารางว่าง
        raise RuntimeError("No llm_configs found in database")

    llm = ChatOpenAI(
        api_key=os.environ.get("OPENAI_KEY"),
        model=config["model"],
        temperature=config["temperature"],
        logprobs=True,
    )
    return llm, config["system_prompt"]

# device = "cuda" if torch.cuda.is_available() else "cpu"
# embedding_model = HuggingFaceEmbeddings(
#     model_name="BAAI/bge-m3",
#     model_kwargs={"device": device},
#     encode_kwargs={"normalize_embeddings": True},
# )

embedding_model = DeepInfraEmbeddings(
    deepinfra_api_token=os.environ.get("DEEPINFRA_KEY"),
    model_id="BAAI/bge-m3",
    normalize=True
)

Base = declarative_base()

class Intent(Base):
    __tablename__ = "intents"
    intent_id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    tool_name = Column(String)
    training_phrases = relationship("TrainingPhrase", back_populates="intent", cascade="all, delete")

class TrainingPhrase(Base):
    __tablename__ = "training_phrases"
    tp_id = Column(Integer, primary_key=True)
    intent_id = Column(Integer, ForeignKey("intents.intent_id", ondelete="CASCADE"))
    phrase = Column(String, nullable=False)
    intent = relationship("Intent", back_populates="training_phrases")

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_session_id = Column(String, unique=True, nullable=True)
    mode = Column(String, default="ai") 
    now = datetime.now()
    started_at = Column(DateTime, default=now)

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("chat_sessions.external_session_id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    tel = Column(String(50))
    email = Column(String(255))
    category_fullname = Column(String(255))
    detail = Column(Text)
    now = datetime.now()
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime, default=now)

#ไม่รู้จะเอาไปไว้ที่ไหน
def save_ticket_pg(db, session_id: str, data, ticket_code):
    try:
        row = db.execute(
            text("""
                INSERT INTO tickets (
                    session_id,
                    name,
                    tel,
                    email,
                    category_fullname,
                    detail,
                    code
                )
                VALUES (
                    :session_id,
                    :name,
                    :tel,
                    :email,
                    :category_fullname,
                    :detail,
                    :code
                )
                RETURNING id, created_at
            """),
            {
                "session_id": session_id,
                "name": data.customer.name,
                "tel": getattr(data.customer, "tel", None),
                "email": getattr(data.customer, "email", None),
                "category_fullname": data.category_fullname,
                "detail": data.detail,
                "code": ticket_code
            }
        ).mappings().first()

        db.commit()

        return {
            "ok": True,
            "created_at": str(row["created_at"]),
        }

    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}

