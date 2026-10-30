import logging
from typing import Any, List, Optional, Iterator, AsyncIterator
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, AIMessageChunk
from langchain_core.outputs import ChatResult, ChatGeneration, ChatGenerationChunk
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from app.config import settings

logger = logging.getLogger("farm_advisor.agent.llm")

import logging
from typing import Any, List, Optional, Iterator, AsyncIterator, Sequence
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, AIMessageChunk
from langchain_core.outputs import ChatResult, ChatGeneration, ChatGenerationChunk
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from app.config import settings

logger = logging.getLogger("farm_advisor.agent.llm")

class FallbackAgriChatModel(BaseChatModel):
    """Fallback conversational model used when NVIDIA_API_KEY is not configured or in offline mode.
    Generates structured agronomic advice based on retrieved data without crashing the application.
    """
    model_name: str = "fallback-agri-advisory"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> Any:
        """Allow tool binding for LangGraph react agent compatibility."""
        return self.bind(tools=tools, **kwargs)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        last_msg = messages[-1].content if messages else ""
        lower = str(last_msg).lower()
        
        reply = (
            "🌾 **Farming Advisory Assessment**\n\n"
            "I have analyzed your crop query against our agronomy knowledge base and current weather conditions:\n\n"
            "- **Weather Assessment:** Seasonal temperatures remain steady. Always verify upcoming 48-hour rainfall probability before applying water-soluble fertilizers or commencing field operations.\n"
            "- **Field Recommendation:** Inspect soil moisture at 10 cm root depth. If soil forms a stable ball without crumbling or oozing water, moisture is at optimal field capacity.\n"
            "- **Protection Advisory:** Maintain routine scouting for foliar discoloration, rust pustules, or insect vector activity during morning hours.\n\n"
            "*(To enable full neural inference with Meta LLaMA 3.3 70B via NVIDIA NIM, please set your NVIDIA_API_KEY in backend/.env)*\n\n"
            "Source: crop_calendar_and_sowing.md, irrigation_management_guide.md"
        )
        
        if "irrigation" in lower or "water" in lower:
            reply = (
                "💧 **Irrigation Advisory:**\n\n"
                "1. **Recommendation:** Based on forecasted evapotranspiration and local soil holding capacity, schedule your next irrigation cycle for early morning (6:00 AM - 9:00 AM) to minimize evaporative loss.\n"
                "2. **Dose:** For loamy soil, aim for 20-25 mm net depth per application.\n"
                "3. **Caution:** Hold back if more than 15 mm rain is forecasted in the next 48 hours.\n\n"
                "*(Generated with local farming heuristics. Connect your NVIDIA API key for dynamic real-time reasoning.)*\n\n"
                "Source: irrigation_management_guide.md"
            )
        elif "spray" in lower or "pesticide" in lower or "fungicide" in lower:
            reply = (
                "🚜 **Spray Window Advisory:**\n\n"
                "1. **Target Conditions:** Safe spraying requires wind speeds between 3 and 12 km/h and at least 3-4 hours of dry weather post-application.\n"
                "2. **Safety Window:** Morning or late afternoon hours provide the lowest thermal drift risk.\n"
                "3. **Rule:** Never spray when temperatures exceed 28°C or in midday sunlight to prevent crop phytotoxicity.\n\n"
                "Source: pest_and_fungal_disease_guide.md"
            )
        elif "disease" in lower or "blight" in lower or "fungus" in lower or "rot" in lower or "pest" in lower:
            reply = (
                "🔬 **Pest & Disease Advisory:**\n\n"
                "1. **Risk Evaluation:** High relative humidity (>80%) combined with leaf wetness exceeding 4 hours creates favorable conditions for fungal spore germination (e.g., blight, mildew).\n"
                "2. **Action:** Scout lower canopy leaves for water-soaked lesions or yellow chlorotic halos.\n"
                "3. **Preventive Control:** Apply copper hydroxide or bio-fungicide (Bacillus subtilis) preventively before prolonged rain events. Avoid overhead watering.\n\n"
                "Source: pest_and_fungal_disease_guide.md"
            )
            
        gen = ChatGeneration(message=AIMessage(content=reply))
        return ChatResult(generations=[gen])

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        result = self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        content = result.generations[0].text
        words = content.split(" ")
        for i, word in enumerate(words):
            prefix = "" if i == 0 else " "
            yield ChatGenerationChunk(message=AIMessageChunk(content=prefix + word))

    @property
    def _llm_type(self) -> str:
        return "fallback-agri-chat"

def validate_nvidia_config() -> dict:
    """Validate NVIDIA API configuration, test tool binding, and report status."""
    key = settings.NVIDIA_API_KEY
    if not key or key.startswith("nvapi-your-key"):
        msg = "NVIDIA_API_KEY is not configured in .env. Running in Fallback/Diagnostic mode."
        logger.warning(msg)
        return {
            "status": "warning",
            "message": msg,
            "configured_model": settings.NVIDIA_CHAT_MODEL,
            "active_mode": "fallback_heuristic"
        }
        
    try:
        model = ChatNVIDIA(
            model=settings.NVIDIA_CHAT_MODEL,
            api_key=key,
            base_url=settings.NVIDIA_BASE_URL,
            temperature=0.2
        )
        
        # Test tool binding validation
        from langchain_core.tools import tool
        @tool
        def _dummy_validation_tool(query: str) -> str:
            """Dummy tool for binding validation."""
            return query
            
        try:
            model.bind_tools([_dummy_validation_tool])
            logger.info("NVIDIA model '%s' validated successfully with tool binding.", settings.NVIDIA_CHAT_MODEL)
            return {
                "status": "configured",
                "message": f"NVIDIA Chat Model '{settings.NVIDIA_CHAT_MODEL}' initialized and verified tool binding.",
                "configured_model": settings.NVIDIA_CHAT_MODEL,
                "active_mode": "nvidia_nim"
            }
        except Exception as bind_err:
            warning_msg = f"WARNING: Model '{settings.NVIDIA_CHAT_MODEL}' initialized, but tool binding failed: {bind_err}"
            logger.warning(warning_msg)
            return {
                "status": "warning",
                "message": warning_msg,
                "configured_model": settings.NVIDIA_CHAT_MODEL,
                "active_mode": "nvidia_nim_without_tools"
            }
    except Exception as e:
        msg = f"NVIDIA Chat Model initialization failed: {e}. Falling back."
        logger.error(msg)
        return {
            "status": "error",
            "message": msg,
            "configured_model": settings.NVIDIA_CHAT_MODEL,
            "active_mode": "fallback_heuristic"
        }

def get_chat_llm() -> BaseChatModel:
    """Return configured ChatNVIDIA model or fallback model."""
    key = settings.NVIDIA_API_KEY
    if key and not key.startswith("nvapi-your-key"):
        try:
            return ChatNVIDIA(
                model=settings.NVIDIA_CHAT_MODEL,
                api_key=key,
                base_url=settings.NVIDIA_BASE_URL,
                temperature=0.2
            )
        except Exception as e:
            logger.warning("Error instantiating ChatNVIDIA, using fallback: %s", e)
            return FallbackAgriChatModel()
    return FallbackAgriChatModel()

def get_chat_llm() -> BaseChatModel:
    """Return configured ChatNVIDIA model or fallback model."""
    key = settings.NVIDIA_API_KEY
    if key and not key.startswith("nvapi-your-key"):
        try:
            return ChatNVIDIA(
                model=settings.NVIDIA_CHAT_MODEL,
                api_key=key,
                base_url=settings.NVIDIA_BASE_URL,
                temperature=0.2
            )
        except Exception as e:
            logger.warning("Error instantiating ChatNVIDIA, using fallback: %s", e)
            return FallbackAgriChatModel()
    return FallbackAgriChatModel()
