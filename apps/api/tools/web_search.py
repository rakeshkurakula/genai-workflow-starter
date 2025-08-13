"""Web Search Tool Module.

Provides web search functionality with JSON Schema validation,
Pydantic models, and guardrails for timeout and size limits.
"""

import asyncio
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import httpx
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Configuration constants for guardrails
MAX_RESULTS = 50
REQUEST_TIMEOUT = 30.0  # seconds
MAX_QUERY_LENGTH = 500
MAX_RESPONSE_SIZE = 10 * 1024 * 1024  # 10MB

# JSON Schema for web search tool
WEB_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Search query string",
            "maxLength": MAX_QUERY_LENGTH
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results to return",
            "minimum": 1,
            "maximum": MAX_RESULTS,
            "default": 10
        },
        "safe_search": {
            "type": "boolean",
            "description": "Enable safe search filtering",
            "default": True
        },
        "language": {
            "type": "string",
            "description": "Search language (ISO 639-1 code)",
            "pattern": "^[a-z]{2}$",
            "default": "en"
        }
    },
    "required": ["query"],
    "additionalProperties": False
}


class WebSearchRequest(BaseModel):
    """Pydantic model for web search requests."""
    
    query: str = Field(
        ...,
        description="Search query string",
        max_length=MAX_QUERY_LENGTH
    )
    max_results: int = Field(
        default=10,
        description="Maximum number of results to return",
        ge=1,
        le=MAX_RESULTS
    )
    safe_search: bool = Field(
        default=True,
        description="Enable safe search filtering"
    )
    language: str = Field(
        default="en",
        description="Search language (ISO 639-1 code)",
        regex=r"^[a-z]{2}$"
    )
    
    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


class SearchResult(BaseModel):
    """Pydantic model for individual search results."""
    
    title: str = Field(..., description="Result title")
    url: str = Field(..., description="Result URL")
    snippet: str = Field(..., description="Result snippet/description")
    published_date: Optional[datetime] = Field(
        None, 
        description="Publication date if available"
    )
    

class WebSearchResponse(BaseModel):
    """Pydantic model for web search responses."""
    
    query: str = Field(..., description="Original search query")
    results: List[SearchResult] = Field(
        default=[],
        description="List of search results"
    )
    total_results: int = Field(
        default=0,
        description="Total number of results found"
    )
    search_time: float = Field(
        ...,
        description="Time taken for search in seconds"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Search timestamp"
    )
    

class WebSearchTool:
    """Web search tool implementation with guardrails."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)
        
    async def search(self, request: WebSearchRequest) -> WebSearchResponse:
        """Execute web search with guardrails.
        
        Args:
            request: Web search request parameters
            
        Returns:
            WebSearchResponse: Search results and metadata
            
        Raises:
            ValueError: If request validation fails
            TimeoutError: If search times out
            httpx.HTTPError: If HTTP request fails
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Validate request
            if not isinstance(request, WebSearchRequest):
                request = WebSearchRequest(**request)
                
            logger.info(f"Executing web search for query: {request.query}")
            
            # This is a stub implementation
            # In production, integrate with actual search APIs like:
            # - Google Custom Search API
            # - Bing Search API
            # - DuckDuckGo API
            # - Serper API, etc.
            
            results = await self._mock_search(request)
            
            search_time = asyncio.get_event_loop().time() - start_time
            
            response = WebSearchResponse(
                query=request.query,
                results=results,
                total_results=len(results),
                search_time=search_time
            )
            
            # Check response size limit
            response_size = len(response.model_dump_json())
            if response_size > MAX_RESPONSE_SIZE:
                logger.warning(f"Response size {response_size} exceeds limit")
                # Truncate results if needed
                response.results = response.results[:5]
                response.total_results = len(response.results)
                
            return response
            
        except asyncio.TimeoutError:
            logger.error("Web search timed out")
            raise TimeoutError(f"Search timed out after {REQUEST_TIMEOUT}s")
        except Exception as e:
            logger.error(f"Web search failed: {str(e)}")
            raise
            
    async def _mock_search(self, request: WebSearchRequest) -> List[SearchResult]:
        """Mock search implementation for testing.
        
        Replace this with actual search API integration.
        """
        # Simulate API delay
        await asyncio.sleep(0.1)
        
        # Mock results based on query
        mock_results = [
            SearchResult(
                title=f"Mock Result {i+1} for '{request.query}'",
                url=f"https://example{i+1}.com/mock-result",
                snippet=f"This is a mock search result {i+1} for the query '{request.query}'. "
                       f"It demonstrates the structure of search results.",
                published_date=datetime.utcnow()
            )
            for i in range(min(request.max_results, 5))
        ]
        
        return mock_results
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()


# Convenience function for direct usage
async def web_search(query: str, **kwargs) -> WebSearchResponse:
    """Convenience function for web search.
    
    Args:
        query: Search query string
        **kwargs: Additional search parameters
        
    Returns:
        WebSearchResponse: Search results
    """
    request = WebSearchRequest(query=query, **kwargs)
    
    async with WebSearchTool() as tool:
        return await tool.search(request)


if __name__ == "__main__":
    # Simple test
    import asyncio
    
    async def test_search():
        result = await web_search("Python programming")
        print(f"Found {result.total_results} results in {result.search_time:.2f}s")
        for r in result.results:
            print(f"- {r.title}: {r.url}")
            
    asyncio.run(test_search())
