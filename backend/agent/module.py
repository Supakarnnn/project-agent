from pydantic import BaseModel
from typing import List, Literal, Optional

class Message(BaseModel):
    role: Literal["ai", "human", "system"]
    content: str

class RequestMessage(BaseModel):
    messages: List[Message]

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

class ConfigUpdate(BaseModel):
    model: str
    temperature: Optional[float] = 0.2
    top_p: Optional[float] = 0 
    system_prompt: str