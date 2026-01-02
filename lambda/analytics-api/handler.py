"""
Analytics Query API Lambda

Provides REST API endpoints for querying analytics data.

Routes:
    GET /analytics/stats/{domain}                  - Daily visitor counts
    GET /analytics/pages/{domain}                  - Top pages
    GET /analytics/referrers/{domain}              - Top referrers (aggregated by domain)
    GET /analytics/hours/{domain}                  - Traffic by hour
    GET /analytics/countries/{domain}              - Visitor countries
    GET /analytics/journeys/{domain}               - Journey summary stats
    GET /analytics/sessions/{domain}               - All sessions with referrer, filters, rollup
    GET /analytics/sessions/{domain}/{session_id}  - Session detail with page journey
    GET /analytics/flows/{domain}                  - Page flow data
    GET /analytics/hallucinations/{domain}         - AI hallucination metrics from 404s
"""

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List

import boto3


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types from DynamoDB."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super().default(obj)


from boto3.dynamodb.conditions import Key

# Configure logging
log_level = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

HANDLER_NAME = "analytics-api"

# Environment variables
ENV = os.environ.get("ENV", "dev")
TABLE_NAME = os.environ.get("TABLE_NAME")
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE")
ALLOWED_DOMAINS = os.environ.get("ALLOWED_DOMAINS", "outcomeops.ai,myfantasy.ai,thetek.net").split(",")

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
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "OPTIONS,GET,POST",
        },
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def _error(status_code: int, message: str) -> Dict:
    return _response(status_code, {"error": message})


def _parse_date_range(event: Dict) -> tuple[str, str]:
    """
    Parse from/to date parameters from query string.

    Defaults to last 7 days if not provided.
    """
    params = event.get("queryStringParameters") or {}

    to_date = params.get("to")
    from_date = params.get("from")

    if not to_date:
        to_date = datetime.utcnow().strftime("%Y-%m-%d")

    if not from_date:
        from_dt = datetime.utcnow() - timedelta(days=7)
        from_date = from_dt.strftime("%Y-%m-%d")

    return from_date, to_date


def _get_domain_from_path(event: Dict) -> str | None:
    """Extract domain from path parameters."""
    path_params = event.get("pathParameters") or {}
    return path_params.get("domain")


def _validate_domain(domain: str) -> bool:
    """Check if domain is in allowed list."""
    return domain in ALLOWED_DOMAINS


def _generate_date_range(from_date: str, to_date: str) -> List[str]:
    """Generate list of dates between from_date and to_date (inclusive)."""
    dates = []
    current = datetime.strptime(from_date, "%Y-%m-%d")
    end = datetime.strptime(to_date, "%Y-%m-%d")

    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    return dates


def handle_stats(event: Dict) -> Dict:
    """
    GET /analytics/stats/{domain}

    Returns daily visitor counts for the specified domain and date range.
    """
    domain = _get_domain_from_path(event)
    if not domain or not _validate_domain(domain):
        return _error(400, f"Invalid domain: {domain}")

    from_date, to_date = _parse_date_range(event)
    dates = _generate_date_range(from_date, to_date)

    logger.info(f"{HANDLER_NAME}: Getting stats for {domain} from {from_date} to {to_date}")

    dynamodb = _get_dynamodb()
    table = dynamodb.Table(TABLE_NAME)

    daily_stats = {}
    total_requests = 0
    unique_ips = set()

    for date in dates:
        pk = f"{domain}#{date}"

        response = table.query(
            KeyConditionExpression=Key("PK").eq(pk)
        )

        items = response.get("Items", [])
        day_count = len(items)

        # Collect unique IPs
        for item in items:
            if "client_ip" in item:
                unique_ips.add(item["client_ip"])

        daily_stats[date] = day_count
        total_requests += day_count

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = table.query(
                KeyConditionExpression=Key("PK").eq(pk),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items = response.get("Items", [])
            day_count = len(items)

            for item in items:
                if "client_ip" in item:
                    unique_ips.add(item["client_ip"])

            daily_stats[date] += day_count
            total_requests += day_count

    return _response(200, {
        "domain": domain,
        "from_date": from_date,
        "to_date": to_date,
        "total_requests": total_requests,
        "unique_visitors": len(unique_ips),
        "daily": daily_stats,
    })


def handle_pages(event: Dict) -> Dict:
    """
    GET /analytics/pages/{domain}

    Returns top pages for the specified domain and date range.
    """
    domain = _get_domain_from_path(event)
    if not domain or not _validate_domain(domain):
        return _error(400, f"Invalid domain: {domain}")

    from_date, to_date = _parse_date_range(event)
    dates = _generate_date_range(from_date, to_date)

    params = event.get("queryStringParameters") or {}
    limit = int(params.get("limit", 10))

    logger.info(f"{HANDLER_NAME}: Getting top pages for {domain}")

    dynamodb = _get_dynamodb()
    table = dynamodb.Table(TABLE_NAME)

    page_counts = defaultdict(int)

    for date in dates:
        pk = f"{domain}#{date}"

        response = table.query(
            KeyConditionExpression=Key("PK").eq(pk),
            ProjectionExpression="#p",
            ExpressionAttributeNames={"#p": "path"},
        )

        for item in response.get("Items", []):
            path = item.get("path", "/")
            page_counts[path] += 1

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = table.query(
                KeyConditionExpression=Key("PK").eq(pk),
                ProjectionExpression="#p",
                ExpressionAttributeNames={"#p": "path"},
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            for item in response.get("Items", []):
                path = item.get("path", "/")
                page_counts[path] += 1

    # Sort by count and take top N
    sorted_pages = sorted(page_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

    return _response(200, {
        "domain": domain,
        "from_date": from_date,
        "to_date": to_date,
        "pages": [{"path": path, "count": count} for path, count in sorted_pages],
    })


def handle_referrers(event: Dict) -> Dict:
    """
    GET /analytics/referrers/{domain}

    Returns top referrers for the specified domain and date range.
    """
    domain = _get_domain_from_path(event)
    if not domain or not _validate_domain(domain):
        return _error(400, f"Invalid domain: {domain}")

    from_date, to_date = _parse_date_range(event)
    dates = _generate_date_range(from_date, to_date)

    params = event.get("queryStringParameters") or {}
    limit = int(params.get("limit", 10))

    logger.info(f"{HANDLER_NAME}: Getting top referrers for {domain}")

    dynamodb = _get_dynamodb()
    table = dynamodb.Table(TABLE_NAME)

    referrer_counts = defaultdict(int)

    for date in dates:
        pk = f"{domain}#{date}"

        response = table.query(
            KeyConditionExpression=Key("PK").eq(pk),
            ProjectionExpression="referrer_domain",
        )

        for item in response.get("Items", []):
            ref_domain = item.get("referrer_domain")
            if ref_domain:
                referrer_counts[ref_domain] += 1

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = table.query(
                KeyConditionExpression=Key("PK").eq(pk),
                ProjectionExpression="referrer_domain",
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            for item in response.get("Items", []):
                ref_domain = item.get("referrer_domain")
                if ref_domain:
                    referrer_counts[ref_domain] += 1

    # Sort by count and take top N
    sorted_referrers = sorted(referrer_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

    return _response(200, {
        "domain": domain,
        "from_date": from_date,
        "to_date": to_date,
        "referrers": [{"domain": ref, "count": count} for ref, count in sorted_referrers],
    })


def handle_hours(event: Dict) -> Dict:
    """
    GET /analytics/hours/{domain}

    Returns traffic aggregated by hour of day (0-23 UTC).
    """
    domain = _get_domain_from_path(event)
    if not domain or not _validate_domain(domain):
        return _error(400, f"Invalid domain: {domain}")

    from_date, to_date = _parse_date_range(event)
    dates = _generate_date_range(from_date, to_date)

    logger.info(f"{HANDLER_NAME}: Getting hourly traffic for {domain}")

    dynamodb = _get_dynamodb()
    table = dynamodb.Table(TABLE_NAME)

    # Initialize hour buckets (0-23)
    hourly_counts = {str(h).zfill(2): 0 for h in range(24)}

    for date in dates:
        pk = f"{domain}#{date}"

        response = table.query(
            KeyConditionExpression=Key("PK").eq(pk),
            ProjectionExpression="#ts",
            ExpressionAttributeNames={"#ts": "timestamp"},
        )

        for item in response.get("Items", []):
            ts = item.get("timestamp", "")
            if len(ts) >= 13:  # YYYY-MM-DDTHH format minimum
                hour = ts[11:13]  # Extract HH from timestamp
                if hour in hourly_counts:
                    hourly_counts[hour] += 1

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = table.query(
                KeyConditionExpression=Key("PK").eq(pk),
                ProjectionExpression="#ts",
                ExpressionAttributeNames={"#ts": "timestamp"},
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            for item in response.get("Items", []):
                ts = item.get("timestamp", "")
                if len(ts) >= 13:
                    hour = ts[11:13]
                    if hour in hourly_counts:
                        hourly_counts[hour] += 1

    # Find peak hour
    peak_hour = max(hourly_counts, key=hourly_counts.get)
    total = sum(hourly_counts.values())

    return _response(200, {
        "domain": domain,
        "from_date": from_date,
        "to_date": to_date,
        "hourly": hourly_counts,
        "peak_hour": peak_hour,
        "total": total,
    })


def handle_countries(event: Dict) -> Dict:
    """
    GET /analytics/countries/{domain}

    Returns visitor countries for the specified domain and date range.

    Note: Country detection requires CloudFront to include country header
    or a GeoIP lookup service. This is a placeholder implementation.
    """
    domain = _get_domain_from_path(event)
    if not domain or not _validate_domain(domain):
        return _error(400, f"Invalid domain: {domain}")

    from_date, to_date = _parse_date_range(event)

    logger.info(f"{HANDLER_NAME}: Getting countries for {domain}")

    # TODO: Implement country detection
    # This would require either:
    # 1. CloudFront to include x-edge-location or country header
    # 2. A GeoIP lookup service for client IPs

    return _response(200, {
        "domain": domain,
        "from_date": from_date,
        "to_date": to_date,
        "countries": [],
        "message": "Country detection not yet implemented",
    })


def handle_journeys(event: Dict) -> Dict:
    """
    GET /analytics/journeys/{domain}

    Returns journey summary stats: total sessions, avg pages per session, avg duration.
    """
    domain = _get_domain_from_path(event)
    if not domain or not _validate_domain(domain):
        return _error(400, f"Invalid domain: {domain}")

    from_date, to_date = _parse_date_range(event)
    dates = _generate_date_range(from_date, to_date)

    logger.info(f"{HANDLER_NAME}: Getting journey stats for {domain}")

    if not SESSIONS_TABLE:
        return _error(500, "Sessions table not configured")

    dynamodb = _get_dynamodb()
    table = dynamodb.Table(SESSIONS_TABLE)

    sessions = {}  # session_id -> list of events
    total_pageviews = 0

    for date in dates:
        gsi1pk = f"DOMAIN#{domain}#DATE#{date}"

        response = table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq(gsi1pk),
        )

        for item in response.get("Items", []):
            session_id = item.get("session_id")
            event_type = item.get("event_type")

            if session_id not in sessions:
                sessions[session_id] = []
            sessions[session_id].append(item)

            if event_type == "pageview":
                total_pageviews += 1

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = table.query(
                IndexName="GSI1",
                KeyConditionExpression=Key("GSI1PK").eq(gsi1pk),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            for item in response.get("Items", []):
                session_id = item.get("session_id")
                event_type = item.get("event_type")

                if session_id not in sessions:
                    sessions[session_id] = []
                sessions[session_id].append(item)

                if event_type == "pageview":
                    total_pageviews += 1

    total_sessions = len(sessions)
    avg_pages = round(total_pageviews / total_sessions, 1) if total_sessions > 0 else 0

    # Calculate engagement metrics
    total_duration = 0
    sessions_with_duration = 0
    bounce_count = 0
    engaged_count = 0
    blog_sessions = 0
    blog_total_time = 0

    for session_events in sessions.values():
        # Calculate session duration
        session_duration = sum(
            int(e.get("time_on_page", 0)) for e in session_events
            if e.get("event_type") == "time_on_page"
        )
        if session_duration > 0:
            total_duration += session_duration
            sessions_with_duration += 1

        # Count pageviews in session
        pageviews = [e for e in session_events if e.get("event_type") in ("pageview", "navigation")]
        page_count = len(pageviews)

        # Bounce: 1 pageview + <10s duration
        if page_count == 1 and session_duration < 10:
            bounce_count += 1

        # Engaged: >30s or >1 page
        if session_duration > 30 or page_count > 1:
            engaged_count += 1

        # Blog metrics: sessions starting on /blog or /blogs
        if pageviews:
            entry_path = pageviews[0].get("path", "")
            if entry_path.startswith("/blog"):
                blog_sessions += 1
                blog_total_time += session_duration

    avg_duration = round(total_duration / sessions_with_duration) if sessions_with_duration > 0 else 0
    bounce_rate = round((bounce_count / total_sessions) * 100, 1) if total_sessions > 0 else 0
    engaged_rate = round((engaged_count / total_sessions) * 100, 1) if total_sessions > 0 else 0
    avg_blog_time = round(blog_total_time / blog_sessions) if blog_sessions > 0 else 0

    return _response(200, {
        "domain": domain,
        "from_date": from_date,
        "to_date": to_date,
        "total_sessions": total_sessions,
        "total_pageviews": total_pageviews,
        "avg_pages_per_session": avg_pages,
        "avg_session_duration": avg_duration,
        "bounce_rate": bounce_rate,
        "engaged_sessions": engaged_count,
        "engaged_rate": engaged_rate,
        "blog_sessions": blog_sessions,
        "avg_blog_time": avg_blog_time,
    })


def _extract_referrer_domain(referrer: str, site_domain: str) -> str | None:
    """Extract domain from referrer URL, returning None if self-referral."""
    if not referrer:
        return None
    try:
        from urllib.parse import urlparse
        parsed = urlparse(referrer)
        ref_domain = parsed.netloc.replace("www.", "")
        # Check if self-referral
        if site_domain in ref_domain or ref_domain in site_domain:
            return None
        return ref_domain
    except Exception:
        return None


def handle_sessions(event: Dict) -> Dict:
    """
    GET /analytics/sessions/{domain}

    Returns list of recent sessions with entry/exit pages, referrer, and page count.
    Supports filtering by referrer and entry page.
    """
    domain = _get_domain_from_path(event)
    if not domain or not _validate_domain(domain):
        return _error(400, f"Invalid domain: {domain}")

    from_date, to_date = _parse_date_range(event)
    dates = _generate_date_range(from_date, to_date)

    params = event.get("queryStringParameters") or {}
    limit = int(params.get("limit", 50))
    referrer_filter = params.get("referrer")  # Filter by referrer domain
    page_filter = params.get("page")  # Filter by entry page

    logger.info(f"{HANDLER_NAME}: Getting sessions for {domain}, referrer={referrer_filter}, page={page_filter}")

    if not SESSIONS_TABLE:
        return _error(500, "Sessions table not configured")

    dynamodb = _get_dynamodb()
    table = dynamodb.Table(SESSIONS_TABLE)

    sessions = {}  # session_id -> list of events

    for date in dates:
        gsi1pk = f"DOMAIN#{domain}#DATE#{date}"

        response = table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq(gsi1pk),
        )

        for item in response.get("Items", []):
            session_id = item.get("session_id")
            if session_id not in sessions:
                sessions[session_id] = []
            sessions[session_id].append(item)

        while "LastEvaluatedKey" in response:
            response = table.query(
                IndexName="GSI1",
                KeyConditionExpression=Key("GSI1PK").eq(gsi1pk),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            for item in response.get("Items", []):
                session_id = item.get("session_id")
                if session_id not in sessions:
                    sessions[session_id] = []
                sessions[session_id].append(item)

    # Build session summaries
    session_list = []
    referrer_counts = defaultdict(int)  # For rollup

    for session_id, events in sessions.items():
        # Sort events by timestamp
        events.sort(key=lambda x: x.get("timestamp", ""))

        pageviews = [e for e in events if e.get("event_type") in ("pageview", "navigation")]
        if not pageviews:
            continue

        first_pageview = pageviews[0]
        entry_page = first_pageview.get("path", "/")
        exit_page = pageviews[-1].get("path", "/")
        page_count = len(pageviews)

        # Get referrer from first pageview, extract domain, exclude self-referrals
        raw_referrer = first_pageview.get("referrer", "")
        referrer_domain = _extract_referrer_domain(raw_referrer, domain)
        # Use "(direct)" for no referrer or self-referral
        referrer_display = referrer_domain or "(direct)"

        # Apply filters
        if page_filter and entry_page != page_filter:
            continue
        if referrer_filter:
            if referrer_filter == "(direct)" and referrer_domain is not None:
                continue
            elif referrer_filter != "(direct)" and referrer_domain != referrer_filter:
                continue

        # Count for rollup (only when page filter is active)
        if page_filter:
            referrer_counts[referrer_display] += 1

        # Get duration from time_on_page events
        duration = sum(
            int(e.get("time_on_page", 0)) for e in events
            if e.get("event_type") == "time_on_page"
        )

        # Get first timestamp
        timestamp = first_pageview.get("timestamp", "")

        session_list.append({
            "session_id": session_id,
            "timestamp": timestamp,
            "referrer": referrer_display,
            "entry_page": entry_page,
            "exit_page": exit_page,
            "page_count": page_count,
            "duration": duration,
        })

    # Sort by timestamp descending and limit
    session_list.sort(key=lambda x: x["timestamp"], reverse=True)
    session_list = session_list[:limit]

    # Build rollup summary (sorted by count)
    rollup = [
        {"referrer": ref, "count": count}
        for ref, count in sorted(referrer_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    return _response(200, {
        "domain": domain,
        "from_date": from_date,
        "to_date": to_date,
        "page_filter": page_filter,
        "referrer_filter": referrer_filter,
        "rollup": rollup,
        "sessions": session_list,
    })


def handle_flows(event: Dict) -> Dict:
    """
    GET /analytics/flows/{domain}

    Returns page flow data: entry pages, exit pages, and navigation paths.
    """
    domain = _get_domain_from_path(event)
    if not domain or not _validate_domain(domain):
        return _error(400, f"Invalid domain: {domain}")

    from_date, to_date = _parse_date_range(event)
    dates = _generate_date_range(from_date, to_date)

    params = event.get("queryStringParameters") or {}
    limit = int(params.get("limit", 10))

    logger.info(f"{HANDLER_NAME}: Getting flows for {domain}")

    if not SESSIONS_TABLE:
        return _error(500, "Sessions table not configured")

    dynamodb = _get_dynamodb()
    table = dynamodb.Table(SESSIONS_TABLE)

    entry_pages = defaultdict(int)
    exit_pages = defaultdict(int)
    transitions = defaultdict(int)  # "from_path -> to_path" -> count

    sessions = {}

    for date in dates:
        gsi1pk = f"DOMAIN#{domain}#DATE#{date}"

        response = table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq(gsi1pk),
        )

        for item in response.get("Items", []):
            session_id = item.get("session_id")
            if session_id not in sessions:
                sessions[session_id] = []
            sessions[session_id].append(item)

        while "LastEvaluatedKey" in response:
            response = table.query(
                IndexName="GSI1",
                KeyConditionExpression=Key("GSI1PK").eq(gsi1pk),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            for item in response.get("Items", []):
                session_id = item.get("session_id")
                if session_id not in sessions:
                    sessions[session_id] = []
                sessions[session_id].append(item)

    # Analyze sessions
    for events in sessions.values():
        events.sort(key=lambda x: x.get("timestamp", ""))

        pageviews = [e for e in events if e.get("event_type") in ("pageview", "navigation")]
        if not pageviews:
            continue

        # Entry and exit pages
        entry_pages[pageviews[0].get("path", "/")] += 1
        exit_pages[pageviews[-1].get("path", "/")] += 1

        # Transitions
        for i in range(len(pageviews) - 1):
            from_path = pageviews[i].get("path", "/")
            to_path = pageviews[i + 1].get("path", "/")
            if from_path != to_path:
                transitions[f"{from_path} -> {to_path}"] += 1

    # Sort and limit
    sorted_entries = sorted(entry_pages.items(), key=lambda x: x[1], reverse=True)[:limit]
    sorted_exits = sorted(exit_pages.items(), key=lambda x: x[1], reverse=True)[:limit]
    sorted_transitions = sorted(transitions.items(), key=lambda x: x[1], reverse=True)[:limit]

    return _response(200, {
        "domain": domain,
        "from_date": from_date,
        "to_date": to_date,
        "entry_pages": [{"path": p, "count": c} for p, c in sorted_entries],
        "exit_pages": [{"path": p, "count": c} for p, c in sorted_exits],
        "transitions": [{"flow": f, "count": c} for f, c in sorted_transitions],
    })


def handle_referrals(event: Dict) -> Dict:
    """
    GET /analytics/referrals/{domain}

    Returns sessions with external referrers (excludes self-referrals).
    Supports filtering by entry page path.
    """
    domain = _get_domain_from_path(event)
    if not domain or not _validate_domain(domain):
        return _error(400, f"Invalid domain: {domain}")

    from_date, to_date = _parse_date_range(event)
    dates = _generate_date_range(from_date, to_date)

    params = event.get("queryStringParameters") or {}
    limit = int(params.get("limit", 50))
    page_filter = params.get("page")  # Optional filter by entry page

    logger.info(f"{HANDLER_NAME}: Getting referrals for {domain}, page={page_filter}")

    if not SESSIONS_TABLE:
        return _error(500, "Sessions table not configured")

    dynamodb = _get_dynamodb()
    table = dynamodb.Table(SESSIONS_TABLE)

    sessions = {}  # session_id -> list of events

    for date in dates:
        gsi1pk = f"DOMAIN#{domain}#DATE#{date}"

        response = table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq(gsi1pk),
        )

        for item in response.get("Items", []):
            session_id = item.get("session_id")
            if session_id not in sessions:
                sessions[session_id] = []
            sessions[session_id].append(item)

        while "LastEvaluatedKey" in response:
            response = table.query(
                IndexName="GSI1",
                KeyConditionExpression=Key("GSI1PK").eq(gsi1pk),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            for item in response.get("Items", []):
                session_id = item.get("session_id")
                if session_id not in sessions:
                    sessions[session_id] = []
                sessions[session_id].append(item)

    # Build referral list
    referral_list = []
    for session_id, events in sessions.items():
        # Sort events by timestamp
        events.sort(key=lambda x: x.get("timestamp", ""))

        # Find first pageview with external referrer
        pageviews = [e for e in events if e.get("event_type") in ("pageview", "navigation")]
        if not pageviews:
            continue

        first_pageview = pageviews[0]
        referrer = first_pageview.get("referrer", "")

        # Skip if no referrer or self-referral
        if not referrer:
            continue

        # Check if self-referral (referrer contains the domain)
        if domain in referrer:
            continue

        entry_page = first_pageview.get("path", "/")

        # Apply page filter if provided
        if page_filter and entry_page != page_filter:
            continue

        exit_page = pageviews[-1].get("path", "/")
        page_count = len(pageviews)

        # Calculate duration from time_on_page events
        duration = sum(
            int(e.get("time_on_page", 0)) for e in events
            if e.get("event_type") == "time_on_page"
        )

        timestamp = first_pageview.get("timestamp", "")

        referral_list.append({
            "session_id": session_id,
            "timestamp": timestamp,
            "referrer": referrer,
            "entry_page": entry_page,
            "exit_page": exit_page,
            "page_count": page_count,
            "duration": duration,
        })

    # Sort by timestamp descending and limit
    referral_list.sort(key=lambda x: x["timestamp"], reverse=True)
    referral_list = referral_list[:limit]

    return _response(200, {
        "domain": domain,
        "from_date": from_date,
        "to_date": to_date,
        "page_filter": page_filter,
        "referrals": referral_list,
    })


def handle_session_detail(event: Dict) -> Dict:
    """
    GET /analytics/sessions/{domain}/{session_id}

    Returns all events for a specific session with full page sequence and timestamps.
    """
    path_params = event.get("pathParameters") or {}
    domain = path_params.get("domain")
    session_id = path_params.get("session_id")

    if not domain or not _validate_domain(domain):
        return _error(400, f"Invalid domain: {domain}")

    if not session_id:
        return _error(400, "Session ID required")

    logger.info(f"{HANDLER_NAME}: Getting session detail for {session_id}")

    if not SESSIONS_TABLE:
        return _error(500, "Sessions table not configured")

    dynamodb = _get_dynamodb()
    table = dynamodb.Table(SESSIONS_TABLE)

    # Query all events for this session
    response = table.query(
        KeyConditionExpression=Key("PK").eq(f"SESSION#{session_id}"),
    )

    events = response.get("Items", [])

    # Handle pagination
    while "LastEvaluatedKey" in response:
        response = table.query(
            KeyConditionExpression=Key("PK").eq(f"SESSION#{session_id}"),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        events.extend(response.get("Items", []))

    if not events:
        return _error(404, f"Session not found: {session_id}")

    # Sort by timestamp
    events.sort(key=lambda x: x.get("timestamp", ""))

    # Build page sequence from pageview/navigation events
    pages = []
    for e in events:
        event_type = e.get("event_type")
        if event_type in ("pageview", "navigation"):
            pages.append({
                "path": e.get("path", "/"),
                "timestamp": e.get("timestamp", ""),
                "referrer": e.get("referrer", ""),
            })

    # Get session metadata from first event
    first_event = events[0]
    last_event = events[-1]

    # Calculate total duration from time_on_page events
    duration = sum(
        int(e.get("time_on_page", 0)) for e in events
        if e.get("event_type") == "time_on_page"
    )

    return _response(200, {
        "session_id": session_id,
        "domain": domain,
        "start_time": first_event.get("timestamp", ""),
        "end_time": last_event.get("timestamp", ""),
        "duration": duration,
        "page_count": len(pages),
        "pages": pages,
    })


def handle_hallucinations(event: Dict) -> Dict:
    """
    GET /analytics/hallucinations/{domain}

    Returns AI hallucination metrics from not_found events.
    Shows how many 404s match AI-generated URL patterns.
    """
    domain = _get_domain_from_path(event)
    if not domain or not _validate_domain(domain):
        return _error(400, f"Invalid domain: {domain}")

    from_date, to_date = _parse_date_range(event)

    logger.info(f"{HANDLER_NAME}: Getting hallucinations for {domain} from {from_date} to {to_date}")

    if not SESSIONS_TABLE:
        return _error(500, "Sessions table not configured")

    dynamodb = _get_dynamodb()
    table = dynamodb.Table(SESSIONS_TABLE)

    # Query not_found events by date range
    dates = _generate_date_range(from_date, to_date)
    all_events = []

    for date in dates:
        gsi1pk = f"DOMAIN#{domain}#DATE#{date}"

        response = table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq(gsi1pk),
        )

        all_events.extend(response.get("Items", []))

        while "LastEvaluatedKey" in response:
            response = table.query(
                IndexName="GSI1",
                KeyConditionExpression=Key("GSI1PK").eq(gsi1pk),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            all_events.extend(response.get("Items", []))

    # Filter to not_found events only
    not_found_events = [e for e in all_events if e.get("event_type") == "not_found"]

    # Calculate metrics
    total_404s = len(not_found_events)
    ai_hallucinations = [e for e in not_found_events if e.get("is_ai_pattern")]
    ai_count = len(ai_hallucinations)

    # Group by pattern
    pattern_counts: Dict[str, int] = defaultdict(int)
    for e in ai_hallucinations:
        pattern = e.get("matched_pattern", "unknown")
        pattern_counts[pattern] += 1

    # Sort patterns by count
    patterns = [
        {"pattern": k, "count": v}
        for k, v in sorted(pattern_counts.items(), key=lambda x: -x[1])
    ]

    # Get unique paths that triggered 404s
    path_counts: Dict[str, Dict] = defaultdict(lambda: {"count": 0, "is_ai": False, "pattern": None})
    for e in not_found_events:
        path = e.get("path", "unknown")
        path_counts[path]["count"] += 1
        if e.get("is_ai_pattern"):
            path_counts[path]["is_ai"] = True
            path_counts[path]["pattern"] = e.get("matched_pattern")

    # Sort paths by count, limit to top 20
    top_paths = [
        {"path": k, "count": v["count"], "is_ai_pattern": v["is_ai"], "matched_pattern": v["pattern"]}
        for k, v in sorted(path_counts.items(), key=lambda x: -x[1]["count"])[:20]
    ]

    # Recent AI hallucinations (last 10)
    ai_hallucinations.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    recent = [
        {
            "path": e.get("path", ""),
            "timestamp": e.get("timestamp", ""),
            "referrer": e.get("referrer", ""),
            "matched_pattern": e.get("matched_pattern", ""),
        }
        for e in ai_hallucinations[:10]
    ]

    return _response(200, {
        "domain": domain,
        "from_date": from_date,
        "to_date": to_date,
        "total_404s": total_404s,
        "ai_hallucinations": ai_count,
        "ai_percentage": round(ai_count / total_404s * 100, 1) if total_404s > 0 else 0,
        "patterns": patterns,
        "top_paths": top_paths,
        "recent_hallucinations": recent,
    })


def lambda_handler(event: Dict, context: Any) -> Dict:
    """Main Lambda handler - routes requests to appropriate handlers."""
    logger.info(f"{HANDLER_NAME}: Received event: {json.dumps(event)}")

    # Handle CORS preflight
    http_method = event.get("requestContext", {}).get("http", {}).get("method")
    if http_method == "OPTIONS":
        return _response(200, {})

    route_key = event.get("routeKey", "")

    routes = {
        "GET /analytics/stats/{domain}": handle_stats,
        "GET /analytics/pages/{domain}": handle_pages,
        "GET /analytics/referrers/{domain}": handle_referrers,
        "GET /analytics/hours/{domain}": handle_hours,
        "GET /analytics/countries/{domain}": handle_countries,
        "GET /analytics/journeys/{domain}": handle_journeys,
        "GET /analytics/sessions/{domain}": handle_sessions,
        "GET /analytics/sessions/{domain}/{session_id}": handle_session_detail,
        "GET /analytics/flows/{domain}": handle_flows,
        "GET /analytics/hallucinations/{domain}": handle_hallucinations,
    }

    handler = routes.get(route_key)
    if handler:
        try:
            return handler(event)
        except Exception as e:
            logger.exception(f"{HANDLER_NAME}: Error handling request")
            return _error(500, f"Internal error: {e}")

    return _error(404, f"Route not found: {route_key}")
