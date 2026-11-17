"""Create trace parents and read complete traces from the local Tempo API."""
import base64
import binascii
import json
import os
import secrets
import time
import urllib.error
import urllib.request


def new_trace_context():
    """Return a trace ID, parent span ID, and W3C traceparent header."""
    trace_id = secrets.token_hex(16)
    parent_span_id = secrets.token_hex(8)
    return trace_id, parent_span_id, f"00-{trace_id}-{parent_span_id}-01"


def read_trace(trace_id, timeout_seconds=30, settle_seconds=1.5):
    """Poll Tempo until the server span arrives and the span set settles."""
    deadline = time.monotonic() + timeout_seconds
    tempo_query_url = os.getenv("TEMPO_QUERY_URL", "http://tempo:3200").rstrip("/")
    url = f"{tempo_query_url}/api/v2/traces/{trace_id}"
    last_spans = []
    last_signature = None
    stable_since = None

    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                payload = json.load(response)
            trace = payload.get("trace", payload)
            spans = [
                span
                for resource in trace.get("resourceSpans", [])
                for scope in resource.get("scopeSpans", [])
                for span in scope.get("spans", [])
            ]
            if spans:
                last_spans = spans
                signature = tuple(sorted(span.get("spanId", "") for span in spans))
                now = time.monotonic()
                if signature != last_signature:
                    last_signature = signature
                    stable_since = now
                elif (
                    any(span.get("kind") == "SPAN_KIND_SERVER" for span in spans)
                    and stable_since is not None
                    and now - stable_since >= settle_seconds
                ):
                    return spans
        except urllib.error.HTTPError as error:
            if error.code not in (404, 429, 500, 502, 503, 504):
                raise
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            pass
        time.sleep(0.5)

    return last_spans


def span_attributes(span):
    """Convert OTLP's typed attribute values into a simple dictionary."""
    values = {}
    for attribute in span.get("attributes", []):
        value = attribute.get("value", {})
        values[attribute.get("key", "")] = next(iter(value.values()), None)
    return values


def has_ingress_span(spans, trace_id, parent_span_id):
    """Confirm the server span continues the supplied traceparent context."""
    for span in spans:
        if span.get("kind") != "SPAN_KIND_SERVER":
            continue
        try:
            decoded_trace_id = base64.b64decode(span.get("traceId", "")).hex()
            decoded_parent_id = base64.b64decode(span.get("parentSpanId", "")).hex()
            if decoded_trace_id == trace_id and decoded_parent_id == parent_span_id:
                return True
        except (ValueError, binascii.Error):
            continue
    return False
