import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatResult, ChatGeneration, ChatGenerationChunk
from langchain_core.language_models.chat_models import BaseChatModel

from app.main import app

client = TestClient(app)

class MockAgronomyLLM(BaseChatModel):
    """Mock LLM to test agent integration without network or API keys."""
    model_name: str = "mock-nim-model"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        content = (
            "🌾 **Mock Field Advisory:**\n\n"
            "Based on live weather conditions, hold off on nitrogen application. "
            "Inspect drip lines for pressure consistency.\n\n"
            "Source: crop_calendar_and_sowing.md"
        )
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        content = (
            "🌾 **Mock Field Advisory:**\n\n"
            "Based on live weather conditions, hold off on nitrogen application. "
            "Inspect drip lines for pressure consistency.\n\n"
            "Source: crop_calendar_and_sowing.md"
        )
        words = content.split(" ")
        for i, word in enumerate(words):
            prefix = "" if i == 0 else " "
            yield ChatGenerationChunk(message=AIMessageChunk(content=prefix + word))

    @property
    def _llm_type(self) -> str:
        return "mock-agronomy"

def test_health_check_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "nvidia_config" in data

def test_profile_read_and_update():
    # Read profile
    get_res = client.get("/api/profile")
    assert get_res.status_code == 200
    prof = get_res.json()
    assert "farmer_name" in prof
    assert "location_name" in prof

    # Update profile
    update_res = client.put("/api/profile", json={
        "farmer_name": "Maria Garcia",
        "soil_type": "Clay",
        "crops": ["Tomato", "Wheat"]
    })
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["farmer_name"] == "Maria Garcia"
    assert updated["soil_type"] == "Clay"
    assert "Tomato" in updated["crops"]

def test_weather_endpoint_with_location():
    # Live Open-Meteo test (free, no key)
    response = client.get("/api/weather?place_name=Fresno")
    assert response.status_code == 200
    data = response.json()
    assert "current" in data
    assert "daily" in data
    assert "location" in data
    assert len(data["daily"]) > 0
    assert "temperature_2m" in data["current"]

def test_knowledge_base_search_endpoint():
    response = client.post("/api/kb/search", json={
        "query": "irrigation scheduling",
        "top_k": 2
    })
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "content" in data[0]

@patch("app.agent.agent.get_chat_llm", return_value=MockAgronomyLLM())
def test_chat_endpoint_mocked_llm(mock_llm):
    # Test non-streaming JSON endpoint
    response = client.post(
        "/api/chat?stream=false",
        json={
            "message": "When should I water my tomatoes?",
            "thread_id": "test-mock-thread-101"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "thread_id" in data
    assert data["thread_id"] == "test-mock-thread-101"
    assert "Mock Field Advisory" in data["response"]
    assert "crop_calendar_and_sowing.md" in data["sources"]

def test_threads_list_and_messages():
    res = client.get("/api/threads")
    assert res.status_code == 200
    threads = res.json()
    assert isinstance(threads, list)
