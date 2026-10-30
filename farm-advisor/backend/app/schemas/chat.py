from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Message(BaseModel):
    role: str = Field(description="user, assistant, or system")
    content: str = Field(description="Text content of message")
    timestamp: Optional[str] = None
    sources: Optional[List[str]] = Field(default_factory=list, description="Citations or document references")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Tool calls made during response")

class ChatRequest(BaseModel):
    message: str = Field(description="Farmer's prompt or question")
    thread_id: Optional[str] = Field(default=None, description="Conversation session ID (uuid)")
    override_location: Optional[str] = Field(default=None, description="Optional location override")

class ToolCallEvent(BaseModel):
    tool: str
    input: Dict[str, Any]
    status: str = Field(description="started, running, completed, error")
    output: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    thread_id: str
    sources: List[str] = Field(default_factory=list)
    tool_executions: List[ToolCallEvent] = Field(default_factory=list)

class ThreadSummary(BaseModel):
    thread_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int
