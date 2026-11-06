# ==============================================================================
# AgriPulse: Chat Data Schemas (Pydantic Models)
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Defines data validation models for conversation requests and responses.
# 2. Ensures incoming JSON from the frontend has the correct structure and types.
# 3. Documents API payloads automatically in FastAPI's Swagger UI (/docs).
#
# BEGINNER TIP: Pydantic models act like strict blueprints for data.
# If the client sends an invalid field (like missing a message), Pydantic
# automatically returns a clean HTTP 422 error describing what went wrong.
# ==============================================================================

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class Message(BaseModel):
    """Represents a single chat message stored in the database or sent over API."""
    role: str = Field(description="The sender role: 'user', 'assistant', or 'system'")
    content: str = Field(description="The plain text or markdown content of the message")
    timestamp: Optional[str] = Field(default=None, description="ISO timestamp when the message was sent")
    sources: Optional[List[str]] = Field(default_factory=list, description="List of knowledge base guide filenames cited")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Details of tools invoked while generating the answer")


class ChatRequest(BaseModel):
    """The incoming payload sent by the frontend when a user submits a question."""
    message: str = Field(description="Farmer's prompt or question (e.g., 'Should I spray fungicide today?')")
    thread_id: Optional[str] = Field(default=None, description="Unique conversation session UUID; creates new if omitted")
    override_location: Optional[str] = Field(default=None, description="Optional location override if asking about a different region")


class ToolCallEvent(BaseModel):
    """Records the execution lifecycle of a single tool used by the AI agent."""
    tool: str = Field(description="Name of the tool executed (e.g. 'get_weather_forecast')")
    input: Dict[str, Any] = Field(description="Parameters passed to the tool")
    status: str = Field(description="Current status: 'started', 'running', 'completed', or 'error'")
    output: Optional[str] = Field(default=None, description="Summary or snippet of the data returned by the tool")


class ChatResponse(BaseModel):
    """The complete response payload returned for non-streaming chat requests."""
    response: str = Field(description="The complete AI generated markdown response")
    thread_id: str = Field(description="The conversation thread ID")
    sources: List[str] = Field(default_factory=list, description="List of referenced guides cited by the agent")
    tool_executions: List[ToolCallEvent] = Field(default_factory=list, description="Timeline of tool calls executed")


class ThreadSummary(BaseModel):
    """Summary overview of a chat thread displayed in the conversation history sidebar."""
    thread_id: str = Field(description="Unique identifier of the conversation thread")
    title: str = Field(description="Auto-generated or first-message conversation title")
    created_at: str = Field(description="Timestamp when conversation started")
    updated_at: str = Field(description="Timestamp of last message exchange")
    message_count: int = Field(description="Total number of messages exchanged in this session")
