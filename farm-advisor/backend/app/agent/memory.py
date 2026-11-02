# ==============================================================================
# AgriPulse: Conversation Memory & SQLite Checkpointing
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Connects LangGraph to SQLite to save conversation history across restarts.
# 2. Implements token trimming to keep conversation size within LLM context windows.
# 3. Ensures asynchronous database operations do not block the web server.
# ==============================================================================

import sqlite3
import logging
from typing import List
from contextlib import asynccontextmanager
from langchain_core.messages import BaseMessage, trim_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.config import settings

logger = logging.getLogger("farm_advisor.agent.memory")

# Singleton connection holders
_checkpointer_conn = None
_checkpointer_instance = None


def get_checkpointer() -> SqliteSaver:
    """
    Returns a singleton synchronous SqliteSaver checkpointer instance.
    This saves conversational state to the SQLite database.
    """
    global _checkpointer_conn, _checkpointer_instance
    if _checkpointer_instance is None:
        logger.info("Initializing LangGraph SqliteSaver checkpointer at %s", settings.SQLITE_DB_PATH)
        _checkpointer_conn = sqlite3.connect(settings.SQLITE_DB_PATH, check_same_thread=False)
        _checkpointer_instance = SqliteSaver(_checkpointer_conn)
        _checkpointer_instance.setup()
    return _checkpointer_instance


@asynccontextmanager
async def get_async_checkpointer():
    """
    Asynchronous context manager returning an AsyncSqliteSaver.
    Used during live streaming queries so chat turns persist asynchronously.
    """
    async with AsyncSqliteSaver.from_conn_string(settings.SQLITE_DB_PATH) as checkpointer:
        yield checkpointer


def trim_conversation_history(messages: List[BaseMessage], max_tokens: int = 4000) -> List[BaseMessage]:
    """
    Trims long conversation histories to prevent overflowing model token limits.
    
    Rules followed:
    - Always preserves the original SystemMessage (persona instructions).
    - Keeps the most recent messages (strategy="last").
    - Starts the trimmed window on a human message for natural conversational flow.
    
    Args:
        messages: List of chat messages (Human, AI, System, Tool).
        max_tokens: Approximate maximum token limit (default: 4000).
        
    Returns:
        List[BaseMessage]: Trimmed list of messages safely within token budget.
    """
    try:
        def approximate_token_counter(msgs: List[BaseMessage]) -> int:
            """
            Simple token estimation function: count words and multiply by 1.3.
            This avoids heavy tokenization libraries while maintaining accuracy.
            """
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
