import re
import json
import uuid
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langgraph.prebuilt import create_react_agent

from app.agent.llm import get_chat_llm
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.memory import get_async_checkpointer, trim_conversation_history
from app.db.session import (
    add_message,
    get_farm_profile as db_get_farm_profile,
    create_or_update_thread
)
from app.tools.geocode import geocode_location
from app.tools.weather import get_weather_forecast, get_weather_alerts
from app.tools.irrigation import irrigation_advisor
from app.tools.spray import spray_window_checker
from app.tools.disease import disease_risk_estimator
from app.tools.profile import get_farm_profile, update_farm_profile
from app.tools.rag import search_farming_knowledge

logger = logging.getLogger("farm_advisor.agent")

AGENT_TOOLS = [
    geocode_location,
    get_weather_forecast,
    get_weather_alerts,
    irrigation_advisor,
    spray_window_checker,
    disease_risk_estimator,
    get_farm_profile,
    update_farm_profile,
    search_farming_knowledge
]

TOOL_HUMAN_LABELS = {
    "geocode_location": "Looking up coordinates for location...",
    "get_weather_forecast": "Fetching live 7-day weather forecast...",
    "get_weather_alerts": "Checking severe weather hazard alerts...",
    "irrigation_advisor": "Calculating crop water requirements and soil balance...",
    "spray_window_checker": "Evaluating agrochemical spray window safety...",
    "disease_risk_estimator": "Estimating fungal & pest disease outbreak risk...",
    "get_farm_profile": "Retrieving your registered farm profile...",
    "update_farm_profile": "Updating farm profile settings...",
    "search_farming_knowledge": "Searching agricultural knowledge base..."
}

def extract_sources_from_text(text: str) -> List[str]:
    """Extract 'Source: <filename>' or 'Source: file1, file2' from response text."""
    sources = []
    # Match patterns like: Source: abc.md, def.md or Source: [abc.md]
    matches = re.findall(r"Source:\s*([^\n\r]+)", text, re.IGNORECASE)
    for m in matches:
        items = m.split(",")
        for item in items:
            cleaned = item.strip().strip("[]()*` ")
            if cleaned and cleaned not in sources:
                sources.append(cleaned)
    return sources

def build_system_context_prompt() -> str:
    """Prepend current farm profile context into the system prompt."""
    try:
        profile = db_get_farm_profile()
        crops_str = ", ".join(profile.get("crops", [])) if profile.get("crops") else "None specified"
        context_block = f"""
### CURRENT FARM PROFILE CONTEXT:
- Farmer Name: {profile.get("farmer_name", "Farmer")}
- Farm Location: {profile.get("location_name", "Unknown")} (Lat: {profile.get("latitude")}, Lon: {profile.get("longitude")})
- Crops Grown: {crops_str}
- Field Size: {profile.get("field_size_hectares", 10.0)} ha
- Soil Type: {profile.get("soil_type", "Loamy")}
- Irrigation Method: {profile.get("irrigation_type", "Drip")}
- Language: {profile.get("preferred_language", "en")}
- Notes: {profile.get("notes", "")}

Use this profile context to personalize your advice immediately without repeatedly asking basic questions, unless the user provides new details.
"""
        return SYSTEM_PROMPT + "\n" + context_block
    except Exception as e:
        logger.warning("Could not append farm profile to system prompt: %s", e)
        return SYSTEM_PROMPT

async def stream_agent_execution(
    message: str,
    thread_id: Optional[str] = None,
    override_location: Optional[str] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """Execute the advisory agent workflow and stream events (tokens, tool execution chips, citations)."""
    thread_id = thread_id or str(uuid.uuid4())
    create_or_update_thread(thread_id)
    
    # Store user message
    add_message(thread_id=thread_id, role="user", content=message)
    
    user_prompt = message
    if override_location:
        user_prompt += f"\n(Note: User requested location override: {override_location})"

    full_system_prompt = build_system_context_prompt()
    llm = get_chat_llm()
    
    async with get_async_checkpointer() as checkpointer:
        agent = create_react_agent(
            model=llm,
            tools=AGENT_TOOLS,
            prompt=full_system_prompt,
            checkpointer=checkpointer
        )
        
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }
        
        accumulated_tokens: List[str] = []
        tool_executions: List[Dict[str, Any]] = []
        collected_sources: List[str] = []
        
        try:
            async for event in agent.astream_events(
                {"messages": [HumanMessage(content=user_prompt)]},
                config=config,
                version="v2"
            ):
                ev_type = event.get("event")
                
                # Tool Started
                if ev_type == "on_tool_start":
                    tool_name = event.get("name", "tool")
                    tool_input = event.get("data", {}).get("input", {})
                    label = TOOL_HUMAN_LABELS.get(tool_name, f"Running {tool_name}...")
                    
                    tool_entry = {
                        "tool": tool_name,
                        "label": label,
                        "status": "running",
                        "input": tool_input
                    }
                    tool_executions.append(tool_entry)
                    yield {
                        "type": "tool_start",
                        "tool": tool_name,
                        "label": label,
                        "input": tool_input
                    }
                    
                # Tool Completed
                elif ev_type == "on_tool_end":
                    tool_name = event.get("name", "tool")
                    tool_output = event.get("data", {}).get("output", "")
                    
                    # Update tool entry
                    for te in tool_executions:
                        if te["tool"] == tool_name and te["status"] == "running":
                            te["status"] = "completed"
                            te["output_preview"] = str(tool_output)[:200]
                            break
                            
                    # Extract citations from knowledge base tool if present
                    if tool_name == "search_farming_knowledge" and isinstance(tool_output, dict):
                        for s in tool_output.get("sources", []):
                            if s not in collected_sources:
                                collected_sources.append(s)
                                
                    yield {
                        "type": "tool_end",
                        "tool": tool_name,
                        "status": "completed"
                    }
                    
                # Model Stream Token
                elif ev_type == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        token_str = chunk.content if isinstance(chunk.content, str) else ""
                        if token_str:
                            accumulated_tokens.append(token_str)
                            yield {
                                "type": "token",
                                "token": token_str
                            }
                            
        except Exception as e:
            logger.error("Error during agent streaming: %s", e, exc_info=True)
            err_msg = str(e)
            user_friendly_err = (
                "⚠️ **Advisory Agent Notice**\n\n"
                "We encountered a temporary connection issue while processing your agricultural query. "
                "If using NVIDIA AI Endpoints, please verify your `NVIDIA_API_KEY` and quota in `backend/.env`.\n\n"
                f"*Technical details: {err_msg[:180]}*"
            )
            accumulated_tokens.append(user_friendly_err)
            yield {
                "type": "token",
                "token": user_friendly_err
            }

        final_response = "".join(accumulated_tokens)
        
        # Combine extracted citations from text and tool outputs
        text_sources = extract_sources_from_text(final_response)
        all_sources = list(dict.fromkeys(collected_sources + text_sources))
        
        # Save assistant message to persistent DB
        add_message(
            thread_id=thread_id,
            role="assistant",
            content=final_response,
            sources=all_sources,
            tool_calls=tool_executions
        )
        
        yield {
            "type": "done",
            "thread_id": thread_id,
            "response": final_response,
            "sources": all_sources,
            "tool_executions": tool_executions
        }

async def run_agent(
    message: str,
    thread_id: Optional[str] = None,
    override_location: Optional[str] = None
) -> Dict[str, Any]:
    """Execute the agent workflow non-streamingly and return the complete response payload."""
    last_event = None
    async for event in stream_agent_execution(message, thread_id, override_location):
        if event.get("type") == "done":
            last_event = event
            
    if last_event:
        return {
            "thread_id": last_event["thread_id"],
            "response": last_event["response"],
            "sources": last_event["sources"],
            "tool_executions": last_event["tool_executions"]
        }
    return {
        "thread_id": thread_id or str(uuid.uuid4()),
        "response": "No response generated.",
        "sources": [],
        "tool_executions": []
    }
