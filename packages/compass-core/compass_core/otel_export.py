"""Optional OpenTelemetry export — no hard dependency."""

from __future__ import annotations

import os
from typing import Any


def export_span(name: str, duration_ms: int, *, status: str = "ok", attrs: dict | None = None) -> bool:
    """Best-effort OTLP/console span. Returns True if exported via SDK."""
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint and os.environ.get("COMPASS_OTEL", "").lower() not in ("1", "true", "on"):
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

        provider = trace.get_tracer_provider()
        if not hasattr(provider, "add_span_processor"):
            resource = Resource.create({"service.name": "compass"})
            provider = TracerProvider(resource=resource)
            if endpoint:
                try:
                    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

                    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
                except Exception:
                    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            else:
                provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            trace.set_tracer_provider(provider)
        tracer = trace.get_tracer("compass")
        with tracer.start_as_current_span(name) as span:
            span.set_attribute("duration_ms", duration_ms)
            span.set_attribute("status_custom", status)
            for k, v in (attrs or {}).items():
                if isinstance(v, (str, int, float, bool)):
                    span.set_attribute(str(k), v)
        return True
    except ImportError:
        return False
