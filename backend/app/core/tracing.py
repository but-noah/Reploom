"""
OpenTelemetry tracing configuration and utilities for Reploom backend.

This module sets up distributed tracing for the critical path:
- Token exchange
- Gmail operations
- LangGraph runs

Sensitive data (tokens, PII) is masked to prevent exposure in traces.
"""

import os
import re
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


def setup_tracing(service_name: str = "reploom-backend") -> TracerProvider:
    """
    Initialize OpenTelemetry tracing with OTLP exporter.

    Environment variables:
    - OTEL_EXPORTER_OTLP_ENDPOINT: OTLP collector endpoint (default: http://localhost:4317)
    - OTEL_TRACES_EXPORTER: "otlp", "console", or "none" (default: console)

    Args:
        service_name: Name of the service for trace identification

    Returns:
        Configured TracerProvider
    """
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": "0.1.0",
        }
    )

    provider = TracerProvider(resource=resource)

    # Determine exporter based on environment
    exporter_type = os.getenv("OTEL_TRACES_EXPORTER", "console").lower()

    if exporter_type == "otlp":
        # OTLP exporter for production/collector
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    elif exporter_type == "console":
        # Console exporter for local development
        exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(exporter))
    # If "none", no exporter is added

    trace.set_tracer_provider(provider)
    return provider


def get_tracer(name: str = __name__) -> trace.Tracer:
    """Get a tracer instance for creating spans."""
    return trace.get_tracer(name)


def mask_token(token: str | None) -> str:
    """
    Mask an access token for safe logging in traces.

    Shows first 8 and last 4 characters, masks the rest.

    Args:
        token: The token to mask

    Returns:
        Masked token string or placeholder
    """
    if not token:
        return "<none>"

    if len(token) <= 12:
        return "***"

    return f"{token[:8]}...{token[-4:]}"


def mask_email(email: str | None) -> str:
    """
    Mask an email address for PII protection.

    Shows first character and domain, masks the rest.

    Args:
        email: Email address to mask

    Returns:
        Masked email or placeholder
    """
    if not email:
        return "<none>"

    match = re.match(r"^([^@])([^@]*)(@.+)$", email)
    if match:
        first_char, rest, domain = match.groups()
        return f"{first_char}{'*' * min(len(rest), 5)}{domain}"

    return "***@***"


def sanitize_message_content(content: str | None, max_length: int = 100) -> str:
    """
    Sanitize message content for tracing.

    Truncates long content and removes sensitive patterns.

    Args:
        content: Message content to sanitize
        max_length: Maximum length to include in trace

    Returns:
        Sanitized content
    """
    if not content:
        return "<empty>"

    # Truncate long content
    if len(content) > max_length:
        content = content[:max_length] + "..."

    # Remove potential tokens/secrets (simple heuristic)
    content = re.sub(r'[A-Za-z0-9_-]{40,}', '***TOKEN***', content)

    return content


def safe_span_attributes(**kwargs: Any) -> dict[str, Any]:
    """
    Create span attributes with automatic sanitization.

    Automatically masks common sensitive fields:
    - access_token, token, api_key -> masked
    - email, user_email -> masked email
    - message_body, body -> sanitized

    Args:
        **kwargs: Key-value pairs for span attributes

    Returns:
        Sanitized attributes dictionary
    """
    sanitized = {}

    for key, value in kwargs.items():
        # Skip None values
        if value is None:
            continue

        # Mask tokens
        if any(token_key in key.lower() for token_key in ["token", "secret", "key", "password"]):
            sanitized[key] = mask_token(str(value))
        # Mask emails
        elif "email" in key.lower():
            sanitized[key] = mask_email(str(value))
        # Sanitize message content
        elif any(content_key in key.lower() for content_key in ["body", "content", "message"]):
            sanitized[key] = sanitize_message_content(str(value))
        # Pass through safe values
        else:
            # Only include primitive types
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            else:
                sanitized[key] = str(value)

    return sanitized
