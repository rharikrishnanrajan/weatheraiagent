import sqlite3
import logging
from typing import List
from contextlib import asynccontextmanager
from langchain_core.messages import BaseMessage, trim_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.config import settings

logger = logging.getLogger("farm_advisor.agent.memory")

_checkpointer_conn = None
_checkpointer_instance = None

def get_checkpointer() -> SqliteSaver:
    """Return singleton SqliteSaver checkpointer instance for synchronous usage."""
    global _checkpointer_conn, _checkpointer_instance
    if _checkpointer_instance is None:
        logger.info("Initializing LangGraph SqliteSaver checkpointer at %s", settings.SQLITE_DB_PATH)
        _checkpointer_conn = sqlite3.connect(settings.SQLITE_DB_PATH, check_same_thread=False)
        _checkpointer_instance = SqliteSaver(_checkpointer_conn)
        _checkpointer_instance.setup()
    return _checkpointer_instance

@asynccontextmanager
async def get_async_checkpointer():
    """Context manager returning an AsyncSqliteSaver connected to SQLITE_DB_PATH."""
    async with AsyncSqliteSaver.from_conn_string(settings.SQLITE_DB_PATH) as checkpointer:
        yield checkpointer

def trim_conversation_history(messages: List[BaseMessage], max_tokens: int = 4000) -> List[BaseMessage]:
    """Trim conversation history preserving system message and recent dialogue turns."""
    try:
        def approximate_token_counter(msgs: List[BaseMessage]) -> int:
            total_words = 0
            for m in msgs:
                if isinstance(m.content, str):
                    total_words += len(m.content.split())
                elif isinstance(m.content, list):
                    for part in m.content:
                        if isinstance(part, dict) and "text" in part:
                            total_words += len(part["text"].split())
            return int(total_words * 1.3)

        return trim_messages(
            messages,
            max_tokens=max_tokens,
            token_counter=approximate_token_counter,
            strategy="last",
            start_on="human",
            include_system=True,
            allow_partial=False
        )
    except Exception as e:
        logger.warning("Message trimming encountered an issue, returning raw messages: %s", e)
        return messages
