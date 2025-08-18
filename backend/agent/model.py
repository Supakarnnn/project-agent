import os
import torch
import dotenv
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, declarative_base


dotenv.load_dotenv()

llm = ChatOpenAI(
   api_key=os.environ.get("OPENAI_KEY"),
   model='gpt-4o-mini',
   temperature=0.4
)

device = "cuda" if torch.cuda.is_available() else "cpu"
embedding_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-m3",
    model_kwargs={"device": device},
    encode_kwargs={"normalize_embeddings": True},
)

Base = declarative_base()

class Intent(Base):
    __tablename__ = "intents"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    tool_name = Column(String)
    training_phrases = relationship("TrainingPhrase", back_populates="intent", cascade="all, delete")

class TrainingPhrase(Base):
    __tablename__ = "training_phrases"
    id = Column(Integer, primary_key=True)
    intent_id = Column(Integer, ForeignKey("intents.id", ondelete="CASCADE"))
    phrase = Column(String, nullable=False)
    intent = relationship("Intent", back_populates="training_phrases")

