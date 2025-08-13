import pytest
from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


def test_health_endpoint_returns_healthy_status():
    """Test that health endpoint returns healthy status"""
    response = client.get("/api/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check main status
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "components" in data
    
    # Check all components have correct status
    components = data["components"]
    
    # LLM component
    assert components["llm"]["status"] == "connected"
    assert "provider" in components["llm"]
    assert "model" in components["llm"]
    
    # Vector DB component
    assert components["vector_db"]["status"] == "connected"
    assert "provider" in components["vector_db"]
    assert "collection_count" in components["vector_db"]
    
    # MCP component
    assert components["mcp"]["status"] == "connected"
    assert "servers" in components["mcp"]
    assert "tools_available" in components["mcp"]
    
    # Tools component
    assert components["tools"]["status"] == "loaded"
    assert "count" in components["tools"]
    assert "available" in components["tools"]


def test_health_endpoint_component_placeholders():
    """Test that health endpoint returns expected placeholder values"""
    response = client.get("/api/health")
    data = response.json()
    
    components = data["components"]
    
    # Check placeholder values match expected structure
    assert components["llm"]["provider"] == "placeholder"
    assert components["llm"]["model"] == "placeholder"
    assert components["vector_db"]["provider"] == "placeholder"
    assert components["vector_db"]["collection_count"] == 0
    assert components["mcp"]["servers"] == []
    assert components["mcp"]["tools_available"] == 0
    assert components["tools"]["count"] == 0
    assert components["tools"]["available"] == []
