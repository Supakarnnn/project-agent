from pydantic import BaseModel
from typing import List, Literal, Optional

class Message(BaseModel):
    role: Literal["ai", "human", "system"]
    content: str

class RequestMessage(BaseModel):
    messages: List[Message]
    session_id: str = None

class AgentResponse(BaseModel):
    response: str
    plan: Optional[str]
    query: Optional[str]
    report: Optional[str]
    graph: Optional[str]

class CollectionCreate(BaseModel):
    name: str
    dim: int = 1024
    description: Optional[str] = None

class WebURL(BaseModel):
    url: str