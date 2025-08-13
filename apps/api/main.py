from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import json
import asyncio
from typing import AsyncGenerator


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("FastAPI app starting up...")
    yield
    # Shutdown
    print("FastAPI app shutting down...")


app = FastAPI(
    title="GenAI Workflow API",
    description="Backend API for GenAI workflow management",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "API is running"}


@app.post("/api/chat")
async def chat_stream(message: dict):
    """Chat endpoint with Server-Sent Events (SSE) streaming"""
    async def generate_response() -> AsyncGenerator[str, None]:
        # This is a stub - replace with actual chat logic
        chunks = [
            "Hello! ",
            "This is a ",
            "streaming response ",
            "from the chat API. ",
            "Message received: ",
            f"{message.get('content', 'No content')}"
        ]
        
        for chunk in chunks:
            await asyncio.sleep(0.1)  # Simulate processing delay
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@app.post("/api/ingest")
async def ingest_document(document: dict):
    """Document ingestion endpoint for RAG system"""
    # This is a stub - replace with actual ingestion logic
    document_id = document.get("id", "unknown")
    content = document.get("content", "")
    
    return {
        "status": "success",
        "message": f"Document {document_id} ingested successfully",
        "document_id": document_id,
        "content_length": len(content)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
