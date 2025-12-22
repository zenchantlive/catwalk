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
    # Unknown service type returns 404 (service schema not found)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
