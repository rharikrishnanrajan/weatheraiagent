import json
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest, ChatResponse
from app.agent.agent import stream_agent_execution, run_agent

logger = logging.getLogger("farm_advisor.api.chat")
router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("")
async def chat_endpoint(payload: ChatRequest, stream: bool = Query(True, description="Enable SSE token and tool event streaming")):
    """Chat endpoint supporting real-time Server-Sent Events (SSE) streaming or non-streaming JSON responses."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

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

    async def event_generator():
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

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
