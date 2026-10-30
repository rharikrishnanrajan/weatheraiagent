import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException

from app.db.session import list_threads, get_thread_messages, delete_thread

logger = logging.getLogger("farm_advisor.api.threads")
router = APIRouter(prefix="/threads", tags=["Threads"])

@router.get("", response_model=List[Dict[str, Any]])
def get_all_threads():
    """List all advisory conversation threads sorted by last activity."""
    try:
        return list_threads()
    except Exception as e:
        logger.error("Error listing threads: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{thread_id}/messages", response_model=List[Dict[str, Any]])
def get_messages(thread_id: str):
    """Retrieve full chronological chat message history for a specific thread."""
    try:
        return get_thread_messages(thread_id)
    except Exception as e:
        logger.error("Error retrieving thread messages: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{thread_id}")
def remove_thread(thread_id: str):
    """Delete a conversation thread and all its associated messages."""
    try:
        delete_thread(thread_id)
        return {"status": "success", "message": f"Thread {thread_id} deleted."}
    except Exception as e:
        logger.error("Error deleting thread %s: %s", thread_id, e)
        raise HTTPException(status_code=500, detail=str(e))
