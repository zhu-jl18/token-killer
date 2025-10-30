"""FastAPI main application."""
import time
import uuid
import json
from contextlib import asynccontextmanager
from typing import Any, Dict
try:
    from typing import AsyncGenerator
except ImportError:
    from collections.abc import AsyncGenerator

import aiohttp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from app.config import app_config, settings
from app.core import ThinkingOrchestrator, Fusion, ModelClient
from app.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatCompletionStreamResponse,
    ChatCompletionStreamChoice,
    ChatMessage,
    Usage,
)
from app.models.openai import ErrorResponse, HealthResponse
from app.utils import setup_logging, get_logger

# Setup logging
setup_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info(
        "app_startup",
        host=settings.host,
        port=settings.port,
        model=app_config.service.model_name,
    )
    
    # Create global HTTP session
    connector = aiohttp.TCPConnector(
        limit=settings.http_max_connections,
        limit_per_host=settings.http_max_connections
    )
    timeout = aiohttp.ClientTimeout(total=settings.http_timeout)
    app.state.http_session = aiohttp.ClientSession(
        connector=connector,
        timeout=timeout
    )
    
    yield
    
    # Shutdown
    await app.state.http_session.close()
    logger.info("app_shutdown")


# Create FastAPI app
app = FastAPI(
    title="Triple-Thread Thinking API",
    description=app_config.service.description,
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.exception("unhandled_error", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Internal server error",
                "type": type(exc).__name__,
                "code": "internal_error",
            }
        },
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        model=app_config.service.model_name,
    )


async def generate_streaming_response(
    request: ChatCompletionRequest,
    request_id: str,
    final_answer: str
) -> AsyncGenerator[str, None]:
    """Generate streaming response chunks."""
    
    # Send initial chunk with role
    initial_chunk = ChatCompletionStreamResponse(
        id=request_id,
        model=request.model or app_config.service.model_name,
        choices=[
            ChatCompletionStreamChoice(
                index=0,
                delta={"role": "assistant"},
                finish_reason=None
            )
        ]
    )
    yield f"data: {initial_chunk.model_dump_json()}\n\n"
    
    # Stream content in chunks
    chunk_size = 50  # Characters per chunk
    for i in range(0, len(final_answer), chunk_size):
        chunk_text = final_answer[i:i + chunk_size]
        
        chunk = ChatCompletionStreamResponse(
            id=request_id,
            model=request.model or app_config.service.model_name,
            choices=[
                ChatCompletionStreamChoice(
                    index=0,
                    delta={"content": chunk_text},
                    finish_reason=None
                )
            ]
        )
        yield f"data: {chunk.model_dump_json()}\n\n"
        
        # Add small delay to simulate real streaming
        import asyncio
        await asyncio.sleep(0.05)
    
    # Send final chunk with finish reason
    final_chunk = ChatCompletionStreamResponse(
        id=request_id,
        model=request.model or app_config.service.model_name,
        choices=[
            ChatCompletionStreamChoice(
                index=0,
                delta={},
                finish_reason="stop"
            )
        ]
    )
    yield f"data: {final_chunk.model_dump_json()}\n\n"
    
    # Send [DONE] to signal end
    yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible chat completions endpoint with streaming support."""
    
    start_time = time.time()
    request_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    
    try:
        # Extract user message
        if not request.messages:
            raise HTTPException(status_code=400, detail="Messages required")
        
        user_message = request.messages[-1].content
        logger.info(
            "request_start",
            request_id=request_id,
            message_preview=user_message[:100],
            stream=request.stream or False,
        )
        
        # Get HTTP session from app state
        http_session = app.state.http_session
        
        # Run thinking orchestrator
        orchestrator = ThinkingOrchestrator(http_session)
        thread_results = await orchestrator.think_parallel(user_message)
        
        if not thread_results:
            raise HTTPException(
                status_code=500,
                detail="All thinking threads failed"
            )
        
        # Fuse results
        client = ModelClient(http_session)
        fusion = Fusion(client)
        final_answer = await fusion.fuse_threads(thread_results, user_message)
        
        # Calculate token usage (approximate)
        prompt_tokens = sum(len(msg.content) for msg in request.messages) // 4
        completion_tokens = len(final_answer) // 4
        
        elapsed = time.time() - start_time
        logger.info(
            "request_complete",
            request_id=request_id,
            elapsed_seconds=elapsed,
            output_length=len(final_answer),
            stream=request.stream or False,
        )
        
        # Return streaming or non-streaming response
        if request.stream:
            return StreamingResponse(
                generate_streaming_response(request, request_id, final_answer),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                }
            )
        else:
            # Return regular JSON response
            return ChatCompletionResponse(
                id=request_id,
                model=request.model or app_config.service.model_name,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message=ChatMessage(
                            role="assistant",
                            content=final_answer
                        ),
                    )
                ],
                usage=Usage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                ),
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "request_failed",
            request_id=request_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )


@app.get("/v1/models")
async def list_models():
    """List available models."""
    return {
        "data": [
            {
                "id": app_config.service.model_name,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "organization",
                "permission": [],
                "root": app_config.service.model_name,
                "parent": None,
            }
        ],
        "object": "list",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False,
    )