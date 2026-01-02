"""
Journey Tracker Lambda handler.

Receives tracking events from per-domain API Gateways and writes to DynamoDB.

Routes:
    POST /t       - Single tracking event
    POST /t/batch - Batch tracking events (used by sendBeacon)
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3

# Configure logging
log_level = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

# Environment variables
ENV = os.environ.get("ENV", "dev")
APP_NAME = os.environ.get("APP_NAME", "outcomeops-analytics")
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE")
ALLOWED_DOMAINS = os.environ.get("ALLOWED_DOMAINS", "").split(",")

# Cached AWS clients (container reuse)
_dynamodb = None


def _get_dynamodb():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb


def _response(status_code: int, body: Any) -> Dict:
    """Return standardized API response with CORS headers."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST",
        },
        "body": json.dumps(body),
    }


def _error(status_code: int, message: str) -> Dict:
    return _response(status_code, {"error": message})


def _validate_event(event_data: Dict) -> Optional[str]:
    """Validate a tracking event. Returns error message or None if valid."""
    required_fields = ["session_id", "event_type", "domain", "path"]
    for field in required_fields:
        if field not in event_data:
            return f"Missing required field: {field}"

    # Validate domain is allowed
    domain = event_data.get("domain", "")
    if domain not in ALLOWED_DOMAINS:
        return f"Domain not allowed: {domain}"

    # Validate event type
    valid_types = [
        "session_start",
        "pageview",
        "navigation",
        "scroll",
        "time_on_page",
        "session_end",
        "not_found",  # 404 pages, includes AI hallucination detection
    ]
    if event_data.get("event_type") not in valid_types:
        return f"Invalid event type: {event_data.get('event_type')}"

    return None


def _build_dynamodb_item(event_data: Dict) -> Dict:
    """Build a DynamoDB item from tracking event data."""
    session_id = event_data["session_id"]
    event_type = event_data["event_type"]
    domain = event_data["domain"]
    path = event_data["path"]

    # Use client timestamp if provided, otherwise server time
    timestamp = event_data.get("timestamp") or datetime.utcnow().isoformat() + "Z"
    event_id = event_data.get("event_id") or str(uuid.uuid4())[:8]

    # Parse date from timestamp for GSI
    try:
        date = timestamp[:10]  # YYYY-MM-DD
    except (TypeError, IndexError):
        date = datetime.utcnow().strftime("%Y-%m-%d")

    # TTL: 90 days from now
    ttl = int(time.time()) + (90 * 24 * 60 * 60)

    item = {
        "PK": f"SESSION#{session_id}",
        "SK": f"EVENT#{timestamp}#{event_id}",
        "GSI1PK": f"DOMAIN#{domain}#DATE#{date}",
        "GSI1SK": f"SESSION#{session_id}",
        "GSI2PK": f"DOMAIN#{domain}#PATH#{path}",
        "GSI2SK": timestamp,
        "session_id": session_id,
        "event_type": event_type,
        "domain": domain,
        "path": path,
        "timestamp": timestamp,
        "ttl": ttl,
    }

    # Add optional fields
    optional_fields = [
        "referrer",
        "previous_path",
        "scroll_depth",
        "time_on_page",
        "user_agent",
        "screen_width",
        "screen_height",
        "viewport_width",
        "viewport_height",
        "is_ai_pattern",    # AI hallucination detection for not_found events
        "matched_pattern",  # Which AI pattern was matched
    ]
    for field in optional_fields:
        if field in event_data and event_data[field] is not None:
            item[field] = event_data[field]

    return item


def _write_events(events: List[Dict]) -> Dict:
    """Write events to DynamoDB. Returns result summary."""
    if not SESSIONS_TABLE:
        raise ValueError("SESSIONS_TABLE environment variable not set")

    table = _get_dynamodb().Table(SESSIONS_TABLE)
    written = 0
    errors = []

    # Use batch writer for efficiency
    with table.batch_writer() as batch:
        for event_data in events:
            try:
                validation_error = _validate_event(event_data)
                if validation_error:
                    errors.append(validation_error)
                    continue

                item = _build_dynamodb_item(event_data)
                batch.put_item(Item=item)
                written += 1
            except Exception as e:
                logger.exception(f"Error writing event: {e}")
                errors.append(str(e))

    return {"written": written, "errors": errors}


def _handle_single_event(body: Dict) -> Dict:
    """Handle a single tracking event."""
    result = _write_events([body])
    if result["written"] == 1:
        return _response(200, {"status": "ok"})
    else:
        return _error(400, result["errors"][0] if result["errors"] else "Unknown error")


def _handle_batch_events(body: Dict) -> Dict:
    """Handle batch tracking events."""
    events = body.get("events", [])
    if not events:
        return _error(400, "No events provided")

    if len(events) > 100:
        return _error(400, "Maximum 100 events per batch")

    result = _write_events(events)
    return _response(
        200,
        {
            "status": "ok",
            "written": result["written"],
            "errors": len(result["errors"]),
        },
    )


def lambda_handler(event: Dict, context: Any) -> Dict:
    """Main Lambda handler."""
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # Parse request
        http_method = event.get("requestContext", {}).get("http", {}).get("method", "")
        path = event.get("rawPath", "")

        # Handle OPTIONS for CORS preflight
        if http_method == "OPTIONS":
            return _response(200, {})

        # Only accept POST
        if http_method != "POST":
            return _error(405, "Method not allowed")

        # Parse body
        body_str = event.get("body", "{}")
        if event.get("isBase64Encoded"):
            import base64

            body_str = base64.b64decode(body_str).decode("utf-8")

        try:
            body = json.loads(body_str) if body_str else {}
        except json.JSONDecodeError:
            return _error(400, "Invalid JSON body")

        # Route to handler
        if path == "/t":
            return _handle_single_event(body)
        elif path == "/t/batch":
            return _handle_batch_events(body)
        else:
            return _error(404, "Not found")

    except Exception as e:
        logger.exception("Unexpected error")
        return _error(500, f"Internal error: {e}")
