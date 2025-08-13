"""Middleware for observability in GenAI Workflow API."""

import time
from typing import Callable, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from opentelemetry import trace

from .tracing import get_tracer, add_span_attributes, record_exception
from .cost_logger import get_cost_logger


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic request tracing."""
    
    def __init__(self, app, exclude_paths: list = None):
        """Initialize tracing middleware.
        
        Args:
            app: FastAPI application
            exclude_paths: List of paths to exclude from tracing
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with tracing.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response from downstream handler
        """
        # Skip tracing for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        try:
            tracer = get_tracer()
        except RuntimeError:
            # Tracing not setup, skip
            return await call_next(request)
        
        # Create span for the request
        with tracer.start_as_current_span(
            f"{request.method} {request.url.path}",
            kind=trace.SpanKind.SERVER
        ) as span:
            # Add request attributes
            add_span_attributes(
                **{
                    "http.method": request.method,
                    "http.url": str(request.url),
                    "http.path": request.url.path,
                    "http.scheme": request.url.scheme,
                    "http.host": request.headers.get("host", ""),
                    "http.user_agent": request.headers.get("user-agent", ""),
                    "http.client_ip": request.client.host if request.client else "",
                }
            )
            
            # Add custom headers if present
            session_id = request.headers.get("x-session-id")
            if session_id:
                add_span_attributes(**{"session.id": session_id})
            
            request_id = request.headers.get("x-request-id")
            if request_id:
                add_span_attributes(**{"request.id": request_id})
            
            start_time = time.time()
            
            try:
                # Process request
                response = await call_next(request)
                
                # Add response attributes
                duration_ms = (time.time() - start_time) * 1000
                add_span_attributes(
                    **{
                        "http.status_code": response.status_code,
                        "http.response.duration_ms": round(duration_ms, 2),
                    }
                )
                
                # Set span status based on status code
                if response.status_code >= 400:
                    span.set_status(
                        trace.Status(
                            trace.StatusCode.ERROR,
                            f"HTTP {response.status_code}"
                        )
                    )
                
                return response
                
            except Exception as e:
                # Record exception in span
                record_exception(e)
                raise


class CostMiddleware(BaseHTTPMiddleware):
    """Middleware for cost tracking."""
    
    def __init__(self, app, track_paths: list = None):
        """Initialize cost middleware.
        
        Args:
            app: FastAPI application
            track_paths: List of paths to track costs for (default: ['/api/chat'])
        """
        super().__init__(app)
        self.track_paths = track_paths or ["/api/chat"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with cost tracking.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response from downstream handler
        """
        # Only track costs for specified paths
        if request.url.path not in self.track_paths:
            return await call_next(request)
        
        start_time = time.time()
        
        # Extract session ID from headers or generate one
        session_id = request.headers.get("x-session-id", "default")
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Try to extract cost information from response headers
            # These would be set by the actual AI service calls
            input_tokens = int(response.headers.get("x-input-tokens", 0))
            output_tokens = int(response.headers.get("x-output-tokens", 0))
            cost_usd = float(response.headers.get("x-cost-usd", 0.0))
            provider = response.headers.get("x-provider", "unknown")
            model = response.headers.get("x-model", "unknown")
            
            # Log cost if we have meaningful data
            if input_tokens > 0 or output_tokens > 0 or cost_usd > 0:
                try:
                    cost_logger = get_cost_logger()
                    cost_logger.log_cost(
                        session_id=session_id,
                        operation=request.url.path.split("/")[-1],  # e.g., 'chat'
                        provider=provider,
                        model=model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cost_usd=cost_usd,
                        duration_ms=duration_ms,
                        metadata={
                            "method": request.method,
                            "path": request.url.path,
                            "status_code": response.status_code,
                        }
                    )
                except Exception as e:
                    # Don't fail the request if cost logging fails
                    print(f"Warning: Cost logging failed: {e}")
            
            return response
            
        except Exception as e:
            # Log failed request
            duration_ms = (time.time() - start_time) * 1000
            
            try:
                cost_logger = get_cost_logger()
                cost_logger.log_cost(
                    session_id=session_id,
                    operation=f"{request.url.path.split('/')[-1]}_error",
                    provider="error",
                    model="error",
                    input_tokens=0,
                    output_tokens=0,
                    cost_usd=0.0,
                    duration_ms=duration_ms,
                    metadata={
                        "method": request.method,
                        "path": request.url.path,
                        "error": str(e),
                    }
                )
            except Exception:
                pass  # Ignore cost logging errors during exception handling
            
            raise


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Combined middleware for tracing and cost logging."""
    
    def __init__(self, app, exclude_paths: list = None, track_cost_paths: list = None):
        """Initialize observability middleware.
        
        Args:
            app: FastAPI application
            exclude_paths: List of paths to exclude from tracing
            track_cost_paths: List of paths to track costs for
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
        self.track_cost_paths = track_cost_paths or ["/api/chat"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with both tracing and cost tracking.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response from downstream handler
        """
        # Skip observability for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        start_time = time.time()
        session_id = request.headers.get("x-session-id", "default")
        
        # Setup tracing if available
        tracer = None
        span = None
        try:
            tracer = get_tracer()
            span = tracer.start_span(
                f"{request.method} {request.url.path}",
                kind=trace.SpanKind.SERVER
            )
            
            # Add request attributes to span
            with span:
                add_span_attributes(
                    **{
                        "http.method": request.method,
                        "http.url": str(request.url),
                        "http.path": request.url.path,
                        "session.id": session_id,
                        "request.id": request.headers.get("x-request-id", ""),
                    }
                )
        except RuntimeError:
            # Tracing not setup, continue without it
            pass
        
        try:
            # Process request
            if span:
                with span:
                    response = await call_next(request)
            else:
                response = await call_next(request)
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Update span with response info
            if span:
                add_span_attributes(
                    **{
                        "http.status_code": response.status_code,
                        "http.response.duration_ms": round(duration_ms, 2),
                    }
                )
                
                if response.status_code >= 400:
                    span.set_status(
                        trace.Status(
                            trace.StatusCode.ERROR,
                            f"HTTP {response.status_code}"
                        )
                    )
            
            # Log costs for specified paths
            if request.url.path in self.track_cost_paths:
                try:
                    input_tokens = int(response.headers.get("x-input-tokens", 0))
                    output_tokens = int(response.headers.get("x-output-tokens", 0))
                    cost_usd = float(response.headers.get("x-cost-usd", 0.0))
                    provider = response.headers.get("x-provider", "unknown")
                    model = response.headers.get("x-model", "unknown")
                    
                    if input_tokens > 0 or output_tokens > 0 or cost_usd > 0:
                        cost_logger = get_cost_logger()
                        cost_logger.log_cost(
                            session_id=session_id,
                            operation=request.url.path.split("/")[-1],
                            provider=provider,
                            model=model,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            cost_usd=cost_usd,
                            duration_ms=duration_ms,
                            metadata={
                                "method": request.method,
                                "path": request.url.path,
                                "status_code": response.status_code,
                            }
                        )
                except Exception as e:
                    print(f"Warning: Cost logging failed: {e}")
            
            return response
            
        except Exception as e:
            # Record exception in span
            if span:
                record_exception(e)
            
            # Log failed request cost
            if request.url.path in self.track_cost_paths:
                try:
                    duration_ms = (time.time() - start_time) * 1000
                    cost_logger = get_cost_logger()
                    cost_logger.log_cost(
                        session_id=session_id,
                        operation=f"{request.url.path.split('/')[-1]}_error",
                        provider="error",
                        model="error",
                        input_tokens=0,
                        output_tokens=0,
                        cost_usd=0.0,
                        duration_ms=duration_ms,
                        metadata={
                            "method": request.method,
                            "path": request.url.path,
                            "error": str(e),
                        }
                    )
                except Exception:
                    pass
            
            raise
        
        finally:
            if span:
                span.end()
