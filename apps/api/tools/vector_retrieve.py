"""Vector retrieve tool for semantic search and retrieval."""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# JSON Schema for the tool
VECTOR_RETRIEVE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "vector_retrieve",
        "description": "Retrieve semantically similar documents/chunks using vector similarity search",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for semantic retrieval"
                },
                "collection_name": {
                    "type": "string",
                    "description": "Name of the vector collection/index to search in"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of top similar results to retrieve",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 5
                },
                "similarity_threshold": {
                    "type": "number",
                    "description": "Minimum similarity score threshold (0.0 to 1.0)",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.5
                },
                "filters": {
                    "type": "object",
                    "description": "Optional metadata filters for the search",
                    "additionalProperties": True
                },
                "include_metadata": {
                    "type": "boolean",
                    "description": "Whether to include metadata in results",
                    "default": True
                },
                "rerank": {
                    "type": "boolean",
                    "description": "Whether to apply reranking for better relevance",
                    "default": False
                }
            },
            "required": ["query", "collection_name"]
        }
    }
}

class VectorRetrieveRequest(BaseModel):
    """Request model for vector retrieval."""
    query: str = Field(..., description="Search query")
    collection_name: str = Field(..., description="Vector collection name")
    top_k: int = Field(5, ge=1, le=100, description="Number of results")
    similarity_threshold: float = Field(0.5, ge=0.0, le=1.0, description="Similarity threshold")
    filters: Optional[Dict[str, Any]] = Field(None, description="Metadata filters")
    include_metadata: bool = Field(True, description="Include metadata")
    rerank: bool = Field(False, description="Apply reranking")
    
    @validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        if len(v) > 1000:
            raise ValueError("Query too long (max 1000 characters)")
        return v.strip()
    
    @validator('collection_name')
    def validate_collection_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Collection name cannot be empty")
        # Basic name validation
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Collection name must be alphanumeric with underscores/hyphens")
        return v.strip()

class VectorRetrieveResponse(BaseModel):
    """Response model for vector retrieval."""
    results: List[Dict[str, Any]]
    total_found: int
    query_time_ms: float
    collection_name: str
    
class VectorRetrieveTool:
    """Vector retrieval tool with guardrails and validation."""
    
    def __init__(self, vector_store=None, embedding_model=None):
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        
    async def _validate_collection_exists(self, collection_name: str) -> bool:
        """Validate that collection exists."""
        try:
            # This would be implemented based on your vector store
            # For now, simulate collection existence check
            if self.vector_store:
                return await self.vector_store.collection_exists(collection_name)
            return True  # Mock validation
        except Exception as e:
            logger.error(f"Collection validation error: {e}")
            return False
    
    async def _get_query_embedding(self, query: str) -> np.ndarray:
        """Get embedding for the query."""
        try:
            if self.embedding_model:
                return await self.embedding_model.embed_query(query)
            else:
                # Mock embedding for demo
                return np.random.rand(384)  # OpenAI ada-002 dimension
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            raise
    
    async def _search_vectors(self, 
                             query_embedding: np.ndarray,
                             collection_name: str,
                             top_k: int,
                             similarity_threshold: float,
                             filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Perform vector similarity search."""
        try:
            if self.vector_store:
                return await self.vector_store.similarity_search(
                    query_embedding=query_embedding,
                    collection_name=collection_name,
                    top_k=top_k,
                    similarity_threshold=similarity_threshold,
                    filters=filters
                )
            else:
                # Mock search results
                mock_results = []
                for i in range(min(top_k, 3)):
                    mock_results.append({
                        "id": f"doc_{i}",
                        "content": f"Mock document {i} content related to query",
                        "score": 0.8 - (i * 0.1),
                        "metadata": {
                            "title": f"Document {i}",
                            "source": f"source_{i}.txt",
                            "timestamp": "2024-01-01T00:00:00Z"
                        }
                    })
                return mock_results
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            raise
    
    async def _rerank_results(self, 
                             query: str, 
                             results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply reranking to improve result relevance."""
        try:
            # Simple reranking based on content length and score
            # In practice, you'd use a reranking model
            def rerank_score(result):
                content_length = len(result.get('content', ''))
                similarity_score = result.get('score', 0)
                # Prefer balanced content length and high similarity
                length_factor = min(content_length / 500, 1.0)  # Normalize length
                return similarity_score * 0.7 + length_factor * 0.3
            
            reranked = sorted(results, key=rerank_score, reverse=True)
            
            # Update scores to reflect reranking
            for i, result in enumerate(reranked):
                result['rerank_score'] = rerank_score(result)
                result['original_rank'] = results.index(result)
            
            return reranked
        except Exception as e:
            logger.error(f"Reranking error: {e}")
            return results  # Return original results on error
    
    def _apply_guardrails(self, request: VectorRetrieveRequest) -> None:
        """Apply safety guardrails."""
        # Rate limiting check (would be implemented with actual rate limiter)
        
        # Query content validation
        query_lower = request.query.lower()
        
        # Block potentially harmful queries
        harmful_patterns = [
            'delete', 'drop', 'truncate', 'exec', 'script',
            'password', 'credential', 'secret', 'token'
        ]
        
        for pattern in harmful_patterns:
            if pattern in query_lower:
                logger.warning(f"Potentially harmful query blocked: {pattern}")
                raise ValueError(f"Query contains restricted content: {pattern}")
        
        # Collection name validation
        if request.collection_name.startswith(('system_', 'admin_', 'internal_')):
            raise ValueError("Access to system collections is restricted")
    
    async def execute(self, **kwargs) -> VectorRetrieveResponse:
        """Execute vector retrieval with validation and guardrails."""
        import time
        start_time = time.time()
        
        try:
            # Validate and parse request
            request = VectorRetrieveRequest(**kwargs)
            
            # Apply guardrails
            self._apply_guardrails(request)
            
            # Validate collection exists
            if not await self._validate_collection_exists(request.collection_name):
                raise ValueError(f"Collection '{request.collection_name}' does not exist")
            
            # Get query embedding
            query_embedding = await self._get_query_embedding(request.query)
            
            # Perform vector search
            results = await self._search_vectors(
                query_embedding=query_embedding,
                collection_name=request.collection_name,
                top_k=request.top_k,
                similarity_threshold=request.similarity_threshold,
                filters=request.filters
            )
            
            # Apply reranking if requested
            if request.rerank and results:
                results = await self._rerank_results(request.query, results)
            
            # Filter results by similarity threshold
            filtered_results = [
                result for result in results 
                if result.get('score', 0) >= request.similarity_threshold
            ]
            
            # Remove metadata if not requested
            if not request.include_metadata:
                for result in filtered_results:
                    result.pop('metadata', None)
            
            query_time_ms = (time.time() - start_time) * 1000
            
            logger.info(f"Vector retrieval completed: {len(filtered_results)} results in {query_time_ms:.2f}ms")
            
            return VectorRetrieveResponse(
                results=filtered_results,
                total_found=len(filtered_results),
                query_time_ms=query_time_ms,
                collection_name=request.collection_name
            )
            
        except ValueError as e:
            logger.error(f"Validation error in vector retrieval: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in vector retrieval: {e}")
            raise RuntimeError(f"Vector retrieval failed: {str(e)}")

# Tool instance
vector_retrieve_tool = VectorRetrieveTool()

async def vector_retrieve(**kwargs) -> Dict[str, Any]:
    """Vector retrieve function for agent use."""
    response = await vector_retrieve_tool.execute(**kwargs)
    return response.dict()

# Export schema and function
__all__ = ['VECTOR_RETRIEVE_SCHEMA', 'vector_retrieve', 'VectorRetrieveTool']
