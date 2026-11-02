# ==============================================================================
# AgriPulse: Chat Threads & History API Endpoint (/api/threads)
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Lists all past chat sessions so users can switch between different topics.
# 2. Retrieves past messages for a selected conversation thread.
# 3. Deletes conversation threads and cleans up associated message history.
# ==============================================================================

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException

from app.db.session import list_threads, get_thread_messages, delete_thread

logger = logging.getLogger("farm_advisor.api.threads")

# Router mounted at /api/threads
router = APIRouter(prefix="/threads", tags=["Threads"])


@router.get("", response_model=List[Dict[str, Any]])
def get_all_threads():
    """
    GET /api/threads
    Lists all past conversation threads ordered by most recently updated.
    """
    try:
        return list_threads()
    except Exception as e:
        logger.error("Error listing threads: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{thread_id}/messages", response_model=List[Dict[str, Any]])
def get_messages(thread_id: str):
    """
    GET /api/threads/{thread_id}/messages
    Retrieves the full chronological list of messages (user, assistant, tool calls, citations)
    for a given thread.
    """
    try:
        return get_thread_messages(thread_id)
    except Exception as e:
        logger.error("Error retrieving thread messages: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{thread_id}")
def remove_thread(thread_id: str):
    """
    DELETE /api/threads/{thread_id}
    Deletes a conversation thread and its associated messages from the database.
    """
    try:
        delete_thread(thread_id)
        return {"status": "success", "message": f"Thread {thread_id} deleted."}
    except Exception as e:
        logger.error("Error deleting thread %s: %s", thread_id, e)
        raise HTTPException(status_code=500, detail=str(e))
