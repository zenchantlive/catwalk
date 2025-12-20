from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_generate_openai_form():
    response = client.get("/api/forms/generate/openai")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Configure OpenAI"
    assert len(data["fields"]) == 2
    assert data["fields"][0]["name"] == "api_key"

def test_generate_anthropic_form():
    response = client.get("/api/forms/generate/anthropic")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Configure Anthropic"
    assert data["fields"][0]["name"] == "api_key"

def test_generate_invalid_service_form():
    response = client.get("/api/forms/generate/unknown-service")
    # Pydantic validation for the 'service_type' Literal path param 
    # will actually catch this before logical code execution, returning 422
    assert response.status_code == 422
