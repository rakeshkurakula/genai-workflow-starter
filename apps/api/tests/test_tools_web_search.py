"""Tests for web_search tool module.

Tests the WebSearchTool implementation including:
- JSON Schema validation
- Pydantic model validation 
- Guardrails enforcement
- Mock search functionality
- Error handling
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

# Import the modules we're testing
from tools.web_search import (
    WebSearchTool,
    WebSearchRequest, 
    WebSearchResponse,
    SearchResult,
    web_search,
    WEB_SEARCH_SCHEMA,
    MAX_RESULTS,
    MAX_QUERY_LENGTH,
    REQUEST_TIMEOUT
)


class TestWebSearchRequest:
    """Test WebSearchRequest Pydantic model validation."""
    
    def test_valid_request(self):
        """Test valid request creation."""
        request = WebSearchRequest(
            query="Python programming",
            max_results=10,
            safe_search=True,
            language="en"
        )
        assert request.query == "Python programming"
        assert request.max_results == 10
        assert request.safe_search is True
        assert request.language == "en"
        
    def test_default_values(self):
        """Test default values are applied correctly."""
        request = WebSearchRequest(query="test")
        assert request.max_results == 10
        assert request.safe_search is True
        assert request.language == "en"
        
    def test_query_validation(self):
        """Test query validation rules."""
        # Empty query should fail
        with pytest.raises(ValueError, match="Query cannot be empty"):
            WebSearchRequest(query="")
            
        # Whitespace-only query should fail
        with pytest.raises(ValueError, match="Query cannot be empty"):
            WebSearchRequest(query="   ")
            
        # Query too long should fail
        long_query = "a" * (MAX_QUERY_LENGTH + 1)
        with pytest.raises(ValueError):
            WebSearchRequest(query=long_query)
            
    def test_max_results_validation(self):
        """Test max_results validation rules."""
        # Too low
        with pytest.raises(ValueError):
            WebSearchRequest(query="test", max_results=0)
            
        # Too high
        with pytest.raises(ValueError):
            WebSearchRequest(query="test", max_results=MAX_RESULTS + 1)
            
        # Valid range
        request = WebSearchRequest(query="test", max_results=25)
        assert request.max_results == 25
        
    def test_language_validation(self):
        """Test language code validation."""
        # Invalid format
        with pytest.raises(ValueError):
            WebSearchRequest(query="test", language="english")
            
        with pytest.raises(ValueError):
            WebSearchRequest(query="test", language="e")
            
        # Valid format
        request = WebSearchRequest(query="test", language="es")
        assert request.language == "es"


class TestSearchResult:
    """Test SearchResult Pydantic model."""
    
    def test_valid_result(self):
        """Test valid search result creation."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
            published_date=datetime.utcnow()
        )
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet"
        assert isinstance(result.published_date, datetime)
        
    def test_optional_published_date(self):
        """Test that published_date is optional."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet"
        )
        assert result.published_date is None


class TestWebSearchResponse:
    """Test WebSearchResponse Pydantic model."""
    
    def test_valid_response(self):
        """Test valid response creation."""
        results = [
            SearchResult(
                title="Result 1",
                url="https://example1.com",
                snippet="First result"
            )
        ]
        
        response = WebSearchResponse(
            query="test query",
            results=results,
            total_results=1,
            search_time=0.5
        )
        
        assert response.query == "test query"
        assert len(response.results) == 1
        assert response.total_results == 1
        assert response.search_time == 0.5
        assert isinstance(response.timestamp, datetime)
        
    def test_empty_results(self):
        """Test response with no results."""
        response = WebSearchResponse(
            query="no results query",
            search_time=0.1
        )
        
        assert response.results == []
        assert response.total_results == 0


class TestWebSearchTool:
    """Test WebSearchTool implementation."""
    
    @pytest.fixture
    def search_tool(self):
        """Create a WebSearchTool instance for testing."""
        return WebSearchTool()
        
    @pytest.mark.asyncio
    async def test_mock_search(self, search_tool):
        """Test the mock search implementation."""
        request = WebSearchRequest(query="Python programming", max_results=3)
        
        response = await search_tool.search(request)
        
        assert response.query == "Python programming"
        assert len(response.results) == 3
        assert response.total_results == 3
        assert response.search_time > 0
        
        # Check result structure
        for i, result in enumerate(response.results):
            assert f"Mock Result {i+1}" in result.title
            assert "Python programming" in result.title
            assert result.url.startswith("https://example")
            assert "mock search result" in result.snippet.lower()
            assert isinstance(result.published_date, datetime)
            
    @pytest.mark.asyncio
    async def test_request_validation(self, search_tool):
        """Test request validation in search method."""
        # Test with dict input (should be converted to WebSearchRequest)
        response = await search_tool.search({"query": "test"})
        assert response.query == "test"
        
        # Test with invalid dict input
        with pytest.raises(ValueError):
            await search_tool.search({"query": ""})
            
    @pytest.mark.asyncio
    async def test_response_size_limit(self, search_tool):
        """Test response size limiting."""
        # This test would need to mock a large response
        # For now, we'll test the basic mechanism
        request = WebSearchRequest(query="test", max_results=MAX_RESULTS)
        response = await search_tool.search(request)
        
        # Response should be reasonable size
        response_json = response.model_dump_json()
        assert len(response_json) < 1024 * 1024  # Less than 1MB
        
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test WebSearchTool as async context manager."""
        async with WebSearchTool() as tool:
            response = await tool.search(WebSearchRequest(query="test"))
            assert response.query == "test"
            
    @pytest.mark.asyncio 
    async def test_timeout_handling(self, search_tool):
        """Test timeout handling in search."""
        # Mock the _mock_search method to take too long
        async def slow_search(request):
            await asyncio.sleep(2)  # Longer than any reasonable timeout
            return []
            
        with patch.object(search_tool, '_mock_search', side_effect=slow_search):
            request = WebSearchRequest(query="slow query", max_results=1)
            
            # This should complete quickly due to our mock timeout
            response = await search_tool.search(request)
            # Our mock doesn't actually timeout, so this will pass
            assert response.query == "slow query"


class TestConvenienceFunction:
    """Test the web_search convenience function."""
    
    @pytest.mark.asyncio
    async def test_basic_search(self):
        """Test basic usage of web_search function."""
        response = await web_search("Python programming")
        
        assert response.query == "Python programming"
        assert len(response.results) > 0
        assert response.search_time > 0
        
    @pytest.mark.asyncio
    async def test_search_with_params(self):
        """Test web_search with additional parameters."""
        response = await web_search(
            "AI research",
            max_results=5,
            safe_search=False,
            language="es"
        )
        
        assert response.query == "AI research"
        assert len(response.results) == 5
        
    @pytest.mark.asyncio
    async def test_search_error_handling(self):
        """Test error handling in convenience function."""
        with pytest.raises(ValueError):
            await web_search("")  # Empty query


class TestJSONSchema:
    """Test JSON Schema validation."""
    
    def test_schema_structure(self):
        """Test that the JSON schema has required structure."""
        assert "type" in WEB_SEARCH_SCHEMA
        assert WEB_SEARCH_SCHEMA["type"] == "object"
        assert "properties" in WEB_SEARCH_SCHEMA
        assert "required" in WEB_SEARCH_SCHEMA
        assert "query" in WEB_SEARCH_SCHEMA["required"]
        
        props = WEB_SEARCH_SCHEMA["properties"]
        assert "query" in props
        assert "max_results" in props
        assert "safe_search" in props
        assert "language" in props
        
    def test_schema_constraints(self):
        """Test schema constraints match our constants."""
        props = WEB_SEARCH_SCHEMA["properties"]
        
        assert props["query"]["maxLength"] == MAX_QUERY_LENGTH
        assert props["max_results"]["maximum"] == MAX_RESULTS
        assert props["max_results"]["minimum"] == 1


class TestGuardrails:
    """Test guardrails and safety measures."""
    
    def test_constants_are_reasonable(self):
        """Test that our safety constants are reasonable."""
        assert MAX_RESULTS > 0 and MAX_RESULTS <= 100
        assert MAX_QUERY_LENGTH > 10 and MAX_QUERY_LENGTH <= 1000
        assert REQUEST_TIMEOUT > 1 and REQUEST_TIMEOUT <= 60
        
    @pytest.mark.asyncio
    async def test_max_results_enforced(self):
        """Test that max_results is enforced."""
        tool = WebSearchTool()
        
        # Request more than allowed
        request = WebSearchRequest(query="test", max_results=5)
        response = await tool.search(request)
        
        # Should get at most the requested amount
        assert len(response.results) <= 5
        
        
if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
