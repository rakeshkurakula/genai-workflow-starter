from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import asyncio
import os
from typing import Dict, Any

# Observability imports
from observability import setup_tracing, setup_cost_logger, ObservabilityMiddleware
from observability.tracing import instrument_fastapi

app = FastAPI(title="GenAI Workflow API", version="1.0.0")

# Setup observability
try:
    # Setup tracing
    setup_tracing(
        service_name="genai-workflow-api",
        service_version="1.0.0"
    )
    
    # Setup cost logging
    cost_log_file = os.getenv("COST_LOG_FILE", "logs/costs.log")
    setup_cost_logger(
        log_file=cost_log_file,
        enable_console=True
    )
    
    # Instrument FastAPI for tracing
    instrument_fastapi(app)
    
    print("✅ Observability setup completed")
except Exception as e:
    print(f"⚠️  Observability setup failed: {e}")
    print("📝 Continuing without observability...")

# Add observability middleware
try:
    app.add_middleware(
        ObservabilityMiddleware,
        exclude_paths=["/health", "/metrics", "/docs", "/openapi.json"],
        track_cost_paths=["/api/chat", "/api/ingest"]
    )
except Exception as e:
    print(f"⚠️  Failed to add observability middleware: {e}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class IngestRequest(BaseModel):
    content: str
    source: str
    metadata: Dict[str, Any] = {}

@app.get("/api/health")
async def health_check():
    """Health check endpoint with component status"""
    return {
        "status": "healthy",
        "components": {
            "llm": {
                "status": "connected",
                "provider": "placeholder",
                "model": "placeholder"
            },
            "vector_db": {
                "status": "connected",
                "provider": "placeholder",
                "collection_count": 0
            },
            "mcp": {
                "status": "connected",
                "servers": [],
                "tools_available": 0
            },
            "tools": {
                "status": "loaded",
                "count": 0,
                "available": []
            },
            "observability": {
                "tracing": "enabled" if 'OTEL_EXPORTER_OTLP_ENDPOINT' in os.environ else "disabled",
                "cost_logging": "enabled",
                "log_file": os.getenv("COST_LOG_FILE", "logs/costs.log")
            }
        },
        "timestamp": "2025-08-13T18:11:00Z"
    }

@app.post("/api/chat")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint using Server-Sent Events"""
    
    async def generate_response():
        # Placeholder streaming response
        messages = [
            "Thinking about your request...",
            "Processing with available tools...",
            "Generating response...",
            f"Here's a response to: {request.message}"
        ]
        
        for i, msg in enumerate(messages):
            chunk = {
                "id": f"chunk_{i}",
                "object": "chat.completion.chunk",
                "choices": [{
                    "delta": {"content": msg},
                    "index": 0,
                    "finish_reason": "stop" if i == len(messages) - 1 else None
                }]
            }
            
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0.5)  # Simulate processing time
        
        yield "data: [DONE]\n\n"
    
    # Add response headers for cost tracking (normally set by AI service)
    response = StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            # Example cost tracking headers (would be set by actual AI service)
            "x-input-tokens": "50",
            "x-output-tokens": "75",
            "x-cost-usd": "0.002",
            "x-provider": "openai",
            "x-model": "gpt-4"
        }
    )
    
    return response

@app.post("/api/ingest")
async def ingest_content(request: IngestRequest):
    """Content ingestion endpoint for RAG system"""
    # Placeholder implementation
    return {
        "status": "success",
        "message": "Content ingested successfully",
        "document_id": f"doc_{hash(request.content) % 100000}",
        "chunks_created": 1,
        "source": request.source,
        "metadata": request.metadata,
        "timestamp": "2025-08-13T18:11:00Z"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "GenAI Workflow API", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
