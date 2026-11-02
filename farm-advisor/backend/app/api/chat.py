# ==============================================================================
# AgriPulse: Chat API Endpoint (POST /api/chat)
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Receives incoming user messages from the React frontend.
# 2. Streams token-by-token responses and tool events using Server-Sent Events (SSE).
# 3. Supports standard non-streaming JSON responses if the stream query parameter is false.
# ==============================================================================

import json
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest, ChatResponse
from app.agent.agent import stream_agent_execution, run_agent

logger = logging.getLogger("farm_advisor.api.chat")

# Router mounted at /api/chat
router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("")
async def chat_endpoint(
    payload: ChatRequest,
    stream: bool = Query(True, description="Enable Server-Sent Events (SSE) token and tool event streaming")
):
    """
    POST /api/chat
    Main communication endpoint between farmer and AgriPulse AI.
    
    Parameters:
    - payload: ChatRequest containing `message`, optional `thread_id`, and optional `override_location`.
    - stream: Query parameter (?stream=true by default).
    
    Returns:
    - If stream=true: A continuous Server-Sent Event (SSE) text stream.
    - If stream=false: A single ChatResponse JSON object.
    """
    # Reject empty or whitespace-only messages
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # --------------------------------------------------------------------------
    # MODE A: NON-STREAMING (Standard JSON Response)
    # --------------------------------------------------------------------------
    if not stream:
        try:
            res = await run_agent(
                message=payload.message,
                thread_id=payload.thread_id,
                override_location=payload.override_location
            )
            return ChatResponse(
                response=res["response"],
                thread_id=res["thread_id"],
                sources=res["sources"],
                tool_executions=res.get("tool_executions", [])
            )
        except Exception as e:
            logger.error("Non-streaming chat execution error: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    # --------------------------------------------------------------------------
    # MODE B: REAL-TIME STREAMING (Server-Sent Events)
    # --------------------------------------------------------------------------
    async def event_generator():
        """
        Inner generator function that formats each agent event into the standard
        Server-Sent Events protocol format: 'data: {...}\\n\\n'
        """
        try:
            async for event in stream_agent_execution(
                message=payload.message,
                thread_id=payload.thread_id,
                override_location=payload.override_location
            ):
                payload_str = json.dumps(event)
                yield f"data: {payload_str}\n\n"
        except Exception as e:
            logger.error("SSE stream generation encountered an exception: %s", e)
            err_event = {
                "type": "error",
                "message": f"Stream interrupted: {str(e)}"
            }
            yield f"data: {json.dumps(err_event)}\n\n"

    # Return HTTP 200 StreamingResponse with event-stream media type
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",         # Do not cache streaming data
            "Connection": "keep-alive",          # Keep TCP connection open
            "X-Accel-Buffering": "no"            # Disable proxy buffering (Nginx)
        }
    )
