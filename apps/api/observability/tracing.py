"""OpenTelemetry tracing setup for GenAI Workflow API."""

import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

# Global tracer instance
_tracer: Optional[trace.Tracer] = None
_tracer_provider: Optional[TracerProvider] = None


def setup_tracing(service_name: str = "genai-workflow-api", service_version: str = "1.0.0") -> TracerProvider:
    """Setup OpenTelemetry tracing with OTLP export.
    
    Args:
        service_name: Name of the service for tracing
        service_version: Version of the service
    
    Returns:
        TracerProvider instance
    """
    global _tracer_provider, _tracer
    
    # Create resource with service information
    resource = Resource.create({
        "service.name": service_name,
        "service.version": service_version,
        "service.instance.id": os.getenv("HOSTNAME", "localhost"),
    })
    
    # Create tracer provider
    _tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(_tracer_provider)
    
    # Configure exporters
    exporters = []
    
    # Add OTLP exporter if endpoint is configured
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            headers={
                "Authorization": f"Bearer {os.getenv('OTEL_EXPORTER_OTLP_HEADERS', '')}"
            } if os.getenv('OTEL_EXPORTER_OTLP_HEADERS') else None
        )
        exporters.append(otlp_exporter)
    
    # Add console exporter for development
    if os.getenv("OTEL_TRACES_CONSOLE", "false").lower() == "true":
        console_exporter = ConsoleSpanExporter()
        exporters.append(console_exporter)
    
    # Add batch span processors for each exporter
    for exporter in exporters:
        span_processor = BatchSpanProcessor(exporter)
        _tracer_provider.add_span_processor(span_processor)
    
    # Create tracer instance
    _tracer = trace.get_tracer(service_name, service_version)
    
    # Auto-instrument popular libraries
    _setup_auto_instrumentation()
    
    return _tracer_provider


def _setup_auto_instrumentation() -> None:
    """Setup automatic instrumentation for popular libraries."""
    try:
        # Instrument HTTP libraries
        RequestsInstrumentor().instrument()
        HTTPXClientInstrumentor().instrument()
        
        # Instrument logging
        LoggingInstrumentor().instrument(set_logging_format=True)
        
    except Exception as e:
        # Log but don't fail if instrumentation fails
        print(f"Warning: Failed to setup auto-instrumentation: {e}")


def instrument_fastapi(app) -> None:
    """Instrument FastAPI application with OpenTelemetry.
    
    Args:
        app: FastAPI application instance
    """
    try:
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls=os.getenv("OTEL_EXCLUDED_URLS", "/health,/metrics")
        )
    except Exception as e:
        print(f"Warning: Failed to instrument FastAPI: {e}")


def get_tracer() -> trace.Tracer:
    """Get the configured tracer instance.
    
    Returns:
        OpenTelemetry tracer instance
    
    Raises:
        RuntimeError: If tracing hasn't been setup yet
    """
    global _tracer
    
    if _tracer is None:
        raise RuntimeError("Tracing not setup. Call setup_tracing() first.")
    
    return _tracer


def create_span(name: str, **kwargs):
    """Create a new span with the configured tracer.
    
    Args:
        name: Name of the span
        **kwargs: Additional span attributes
    
    Returns:
        Span context manager
    """
    tracer = get_tracer()
    span = tracer.start_span(name)
    
    # Add attributes if provided
    for key, value in kwargs.items():
        span.set_attribute(key, value)
    
    return span


def add_span_attributes(**attributes) -> None:
    """Add attributes to the current span.
    
    Args:
        **attributes: Key-value pairs to add as span attributes
    """
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        for key, value in attributes.items():
            current_span.set_attribute(key, value)


def record_exception(exception: Exception) -> None:
    """Record an exception in the current span.
    
    Args:
        exception: Exception to record
    """
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        current_span.record_exception(exception)
        current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(exception)))
