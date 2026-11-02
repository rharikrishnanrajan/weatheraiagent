# ==============================================================================
# AgriPulse: LangGraph Agent Workflow, Streaming & Tool Execution
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Assembles all 9 agricultural tools (weather, soil, irrigation, spray, disease, etc.).
# 2. Compiles a LangGraph ReAct agent that loops: Think -> Act (Call Tools) -> Observe -> Answer.
# 3. Streams Server-Sent Events (SSE) so words appear in real-time on the frontend.
# 4. Emits user-friendly tool execution chips ("Fetching live 7-day weather forecast...").
# 5. Automatically parses and returns knowledge base source citations (e.g. irrigation_guide.md).
# ==============================================================================

import re
import json
import uuid
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langgraph.prebuilt import create_react_agent

# AI model, system instructions, and SQLite memory saver
from app.agent.llm import get_chat_llm
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.memory import get_async_checkpointer, trim_conversation_history

# Database access helpers
from app.db.session import (
    add_message,
    get_farm_profile as db_get_farm_profile,
    create_or_update_thread
)

# 9 Agricultural & Meteorological Tools registered with the Agent
from app.tools.geocode import geocode_location
from app.tools.weather import get_weather_forecast, get_weather_alerts
from app.tools.irrigation import irrigation_advisor
from app.tools.spray import spray_window_checker
from app.tools.disease import disease_risk_estimator
from app.tools.profile import get_farm_profile, update_farm_profile
from app.tools.rag import search_farming_knowledge

logger = logging.getLogger("farm_advisor.agent")

# Complete list of tools available for the AI agent to call
AGENT_TOOLS = [
    geocode_location,          # Converts city/village names into GPS coordinates
    get_weather_forecast,      # Pulls temperature, rain, wind from Open-Meteo
    get_weather_alerts,        # Checks frost, heatwave, heavy rain warnings
    irrigation_advisor,        # Calculates soil moisture & water requirements (FAO-56)
    spray_window_checker,      # Evaluates pesticide/fertilizer spray safety windows
    disease_risk_estimator,    # Calculates fungal spore & pest outbreak risk
    get_farm_profile,          # Reads the user's farm profile from database
    update_farm_profile,       # Updates crops, soil type, or irrigation method
    search_farming_knowledge   # Semantic vector search in ChromaDB farming guides
]

# Human-readable labels displayed in the UI when the agent runs a specific tool
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
    """
    Scans the AI output text for citations matching patterns like:
    `Source: irrigation_management_guide.md, pest_and_fungal_disease_guide.md`
    
    Returns:
        List[str]: Clean list of referenced file names.
    """
    sources = []
    # Match patterns: Source: file1.md, file2.md
    matches = re.findall(r"Source:\s*([^\n\r]+)", text, re.IGNORECASE)
    for m in matches:
        items = m.split(",")
        for item in items:
            cleaned = item.strip().strip("[]()*` ")
            if cleaned and cleaned not in sources:
                sources.append(cleaned)
    return sources


def build_system_context_prompt() -> str:
    """
    Fetches the farmer's registered profile from SQLite and injects it into
    the System Prompt so the AI always knows the farmer's location, soil, and crops.
    """
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
    """
    Executes the ReAct Agent in an asynchronous generator, yielding real-time events:
    1. 'tool_start': Fired when the agent decides to invoke an external tool.
    2. 'tool_end': Fired when the tool returns data.
    3. 'token': Fired as each word/token is generated by the LLM.
    4. 'done': Fired upon completion with full message, citations, and tools.
    """
    # Create thread ID if starting a new conversation
    thread_id = thread_id or str(uuid.uuid4())
    create_or_update_thread(thread_id)
    
    # Save the user's message into SQLite
    add_message(thread_id=thread_id, role="user", content=message)
    
    user_prompt = message
    if override_location:
        user_prompt += f"\n(Note: User requested location override: {override_location})"

    # Prepare customized prompt and load AI model
    full_system_prompt = build_system_context_prompt()
    llm = get_chat_llm()
    
    # Establish SQLite memory checkpointer for this conversation thread
    async with get_async_checkpointer() as checkpointer:
        # Build LangGraph ReAct Agent
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
            # Stream internal execution events from the LangGraph workflow
            async for event in agent.astream_events(
                {"messages": [HumanMessage(content=user_prompt)]},
                config=config,
                version="v2"
            ):
                ev_type = event.get("event")
                
                # --- EVENT 1: AGENT CALLS A TOOL ---
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
                    
                # --- EVENT 2: TOOL FINISHES EXECUTION ---
                elif ev_type == "on_tool_end":
                    tool_name = event.get("name", "tool")
                    tool_output = event.get("data", {}).get("output", "")
                    
                    # Update status in tool execution log
                    for te in tool_executions:
                        if te["tool"] == tool_name and te["status"] == "running":
                            te["status"] = "completed"
                            te["output_preview"] = str(tool_output)[:200]
                            break
                            
                    # Extract document citations if the knowledge base tool was used
                    if tool_name == "search_farming_knowledge" and isinstance(tool_output, dict):
                        for s in tool_output.get("sources", []):
                            if s not in collected_sources:
                                collected_sources.append(s)
                                
                    yield {
                        "type": "tool_end",
                        "tool": tool_name,
                        "status": "completed"
                    }
                    
                # --- EVENT 3: MODEL GENERATES RESPONSE TOKEN ---
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
        
        # Save assistant message and tool records to persistent SQLite database
        add_message(
            thread_id=thread_id,
            role="assistant",
            content=final_response,
            sources=all_sources,
            tool_calls=tool_executions
        )
        
        # --- EVENT 4: STREAM COMPLETED ---
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
    """
    Executes the agent synchronously (non-streaming) and returns the complete response dictionary.
    Useful for testing or standard JSON HTTP responses.
    """
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
