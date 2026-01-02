"""
CloudFront Log Parser Lambda

Parses CloudFront access logs from S3 and writes analytics events to DynamoDB.

Trigger: S3 ObjectCreated (*.gz logs)
"""

import gzip
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Any, Dict, List, Set
from urllib.parse import unquote, urlparse

import boto3

# Configure logging
log_level = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

HANDLER_NAME = "log-parser"

# Environment variables
ENV = os.environ.get("ENV", "dev")
TABLE_NAME = os.environ.get("TABLE_NAME")

# TTL for analytics events (90 days)
TTL_DAYS = 90

# File extensions to exclude from analytics (configurable via env var)
_excluded_ext_str = os.environ.get("EXCLUDED_EXTENSIONS", "")
EXCLUDED_EXTENSIONS = set(ext.strip().lower() for ext in _excluded_ext_str.split(",") if ext.strip())

# Path prefixes to exclude from analytics (bots, scanners, browser automation)
_excluded_paths_str = os.environ.get("EXCLUDED_PATHS", "")
EXCLUDED_PATHS = [p.strip() for p in _excluded_paths_str.split(",") if p.strip()]

# Cached AWS clients (container reuse)
_dynamodb = None
_s3_client = None


def _get_dynamodb():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3")
    return _s3_client


def _parse_cloudfront_log_line(line: str) -> Dict | None:
    """
    Parse a single CloudFront log line.

    CloudFront log format (tab-separated):
    date time x-edge-location sc-bytes c-ip cs-method cs(Host) cs-uri-stem
    sc-status cs(Referer) cs(User-Agent) cs-uri-query cs(Cookie)
    x-edge-result-type x-edge-request-id x-host-header cs-protocol
    cs-bytes time-taken x-forwarded-for ssl-protocol ssl-cipher
    x-edge-response-result-type cs-protocol-version fle-status
    fle-encrypted-fields c-port time-to-first-byte x-edge-detailed-result-type
    sc-content-type sc-content-len sc-range-start sc-range-end
    """
    # Skip comment lines
    if line.startswith("#"):
        return None

    fields = line.strip().split("\t")
    if len(fields) < 20:
        return None

    try:
        date_str = fields[0]
        time_str = fields[1]
        client_ip = fields[4]
        host = fields[6]
        path = unquote(fields[7])
        status = fields[8]
        referrer = unquote(fields[9]) if fields[9] != "-" else None
        user_agent = unquote(fields[10]) if fields[10] != "-" else None
        request_id = fields[14]

        # Parse referrer domain (normalize by stripping www., skip self-referrals)
        referrer_domain = None
        if referrer and referrer != "-":
            try:
                parsed = urlparse(referrer)
                raw_ref_domain = parsed.netloc.lower()
                if raw_ref_domain.startswith("www."):
                    raw_ref_domain = raw_ref_domain[4:]
                # Normalize host for comparison (strip www.)
                normalized_host = host.lower()
                if normalized_host.startswith("www."):
                    normalized_host = normalized_host[4:]
                # Only store if not a self-referral
                if raw_ref_domain and raw_ref_domain != normalized_host:
                    referrer_domain = raw_ref_domain
            except Exception:
                pass

        # Create timestamp
        timestamp = f"{date_str}T{time_str}Z"

        return {
            "domain": host,
            "timestamp": timestamp,
            "date": date_str,
            "path": path,
            "status": status,
            "referrer": referrer,
            "referrer_domain": referrer_domain,
            "user_agent": user_agent,
            "client_ip": client_ip,
            "request_id": request_id,
        }
    except Exception as e:
        logger.warning(f"{HANDLER_NAME}: Failed to parse log line: {e}")
        return None


def _extract_domain_from_s3_key(key: str) -> str | None:
    """
    Extract domain from S3 key.

    Expected format: {domain}/YYYY/MM/DD/access-log-xyz.gz
    Example: example.com/2025/12/13/E2ABC123.2025-12-13-14.abc123.gz
    """
    parts = key.split("/")
    if len(parts) > 0:
        return parts[0]
    return None


def _should_exclude_path(path: str) -> bool:
    """Check if path should be excluded based on file extension or path prefix."""
    path_lower = path.lower()

    # Check file extensions
    if EXCLUDED_EXTENSIONS and any(path_lower.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
        return True

    # Check path prefixes (bots, scanners, browser automation)
    if EXCLUDED_PATHS and any(path_lower.startswith(prefix.lower()) for prefix in EXCLUDED_PATHS):
        return True

    return False


def _batch_write_to_dynamodb(items: List[Dict]) -> int:
    """
    Batch write items to DynamoDB (25 items at a time).

    Returns number of items written.
    """
    if not items:
        return 0

    dynamodb = _get_dynamodb()
    table = dynamodb.Table(TABLE_NAME)

    written = 0
    batch_size = 25

    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]

        with table.batch_writer() as writer:
            for item in batch:
                # Create DynamoDB item with PK/SK structure
                pk = f"{item['domain']}#{item['date']}"
                sk = f"{item['timestamp']}#{item['request_id']}"

                # Calculate TTL (90 days from now)
                ttl = int((datetime.now(timezone.utc) + timedelta(days=TTL_DAYS)).timestamp())

                db_item = {
                    "PK": pk,
                    "SK": sk,
                    "domain": item["domain"],
                    "timestamp": item["timestamp"],
                    "path": item["path"],
                    "status": item["status"],
                    "request_id": item["request_id"],
                    "ttl": ttl,
                    # GSI1 for path queries
                    "GSI1PK": f"{item['domain']}#{item['path']}",
                    "GSI1SK": item["timestamp"],
                }

                # Optional fields
                if item.get("referrer"):
                    db_item["referrer"] = item["referrer"]
                if item.get("referrer_domain"):
                    db_item["referrer_domain"] = item["referrer_domain"]
                    # GSI2 for referrer queries
                    db_item["GSI2PK"] = f"{item['domain']}#{item['referrer_domain']}"
                    db_item["GSI2SK"] = item["timestamp"]
                if item.get("user_agent"):
                    db_item["user_agent"] = item["user_agent"]
                if item.get("client_ip"):
                    db_item["client_ip"] = item["client_ip"]

                writer.put_item(Item=db_item)
                written += 1

    return written


def _update_rollups(items: List[Dict]) -> None:
    """
    Update rollup counters in DynamoDB for aggregated analytics.

    Rollup items use atomic ADD operations for concurrent safety:
    - ROLLUP#{domain} / STATS#{date} - daily request count + unique IPs set
    - ROLLUP#{domain} / PAGE#{date}#{path} - page request count
    - ROLLUP#{domain} / REF#{date}#{referrer} - referrer count
    - ROLLUP#{domain} / HOUR#{date}#{hour} - hourly count
    """
    if not items:
        return

    # Aggregate in memory first
    daily_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"requests": 0, "ips": set()})
    page_counts: Dict[str, int] = defaultdict(int)
    referrer_counts: Dict[str, int] = defaultdict(int)
    hourly_counts: Dict[str, int] = defaultdict(int)

    for item in items:
        domain = item["domain"]
        date = item["date"]
        path = item["path"]
        client_ip = item.get("client_ip")
        referrer_domain = item.get("referrer_domain")

        # Extract hour from timestamp (format: 2024-01-15T12:00:00Z)
        hour = item["timestamp"][11:13] if len(item["timestamp"]) >= 13 else "00"

        # Daily stats
        daily_key = f"{domain}#{date}"
        daily_stats[daily_key]["requests"] += 1
        if client_ip:
            daily_stats[daily_key]["ips"].add(client_ip)

        # Page counts
        page_key = f"{domain}#{date}#{path}"
        page_counts[page_key] += 1

        # Referrer counts (only if external referrer)
        if referrer_domain:
            ref_key = f"{domain}#{date}#{referrer_domain}"
            referrer_counts[ref_key] += 1

        # Hourly counts
        hour_key = f"{domain}#{date}#{hour}"
        hourly_counts[hour_key] += 1

    dynamodb = _get_dynamodb()
    table = dynamodb.Table(TABLE_NAME)

    # Calculate TTL (90 days from now)
    ttl = int((datetime.now(timezone.utc) + timedelta(days=TTL_DAYS)).timestamp())

    # Update daily stats rollups
    for key, stats in daily_stats.items():
        domain, date = key.split("#", 1)
        try:
            update_expr = "ADD requests :r"
            expr_values: Dict[str, Any] = {":r": stats["requests"]}

            if stats["ips"]:
                update_expr += ", unique_ips :ips"
                expr_values[":ips"] = stats["ips"]

            table.update_item(
                Key={"PK": f"ROLLUP#{domain}", "SK": f"STATS#{date}"},
                UpdateExpression=f"SET #ttl = :ttl {update_expr}",
                ExpressionAttributeNames={"#ttl": "ttl"},
                ExpressionAttributeValues={**expr_values, ":ttl": ttl},
            )
        except Exception as e:
            logger.warning(f"{HANDLER_NAME}: Failed to update daily rollup {key}: {e}")

    # Update page count rollups
    for key, count in page_counts.items():
        domain, date, path = key.split("#", 2)
        try:
            table.update_item(
                Key={"PK": f"ROLLUP#{domain}", "SK": f"PAGE#{date}#{path}"},
                UpdateExpression="SET #ttl = :ttl ADD #count :c",
                ExpressionAttributeNames={"#ttl": "ttl", "#count": "count"},
                ExpressionAttributeValues={":ttl": ttl, ":c": count},
            )
        except Exception as e:
            logger.warning(f"{HANDLER_NAME}: Failed to update page rollup {key}: {e}")

    # Update referrer count rollups
    for key, count in referrer_counts.items():
        domain, date, referrer = key.split("#", 2)
        try:
            table.update_item(
                Key={"PK": f"ROLLUP#{domain}", "SK": f"REF#{date}#{referrer}"},
                UpdateExpression="SET #ttl = :ttl ADD #count :c",
                ExpressionAttributeNames={"#ttl": "ttl", "#count": "count"},
                ExpressionAttributeValues={":ttl": ttl, ":c": count},
            )
        except Exception as e:
            logger.warning(f"{HANDLER_NAME}: Failed to update referrer rollup {key}: {e}")

    # Update hourly count rollups
    for key, count in hourly_counts.items():
        domain, date, hour = key.split("#", 2)
        try:
            table.update_item(
                Key={"PK": f"ROLLUP#{domain}", "SK": f"HOUR#{date}#{hour}"},
                UpdateExpression="SET #ttl = :ttl ADD #count :c",
                ExpressionAttributeNames={"#ttl": "ttl", "#count": "count"},
                ExpressionAttributeValues={":ttl": ttl, ":c": count},
            )
        except Exception as e:
            logger.warning(f"{HANDLER_NAME}: Failed to update hourly rollup {key}: {e}")

    logger.info(
        f"{HANDLER_NAME}: Updated rollups - daily: {len(daily_stats)}, "
        f"pages: {len(page_counts)}, referrers: {len(referrer_counts)}, "
        f"hours: {len(hourly_counts)}"
    )


def lambda_handler(event: Dict, context: Any) -> Dict:
    """
    Main Lambda handler - triggered by S3 ObjectCreated events.

    Processes CloudFront log files and writes parsed events to DynamoDB.
    """
    logger.info(f"{HANDLER_NAME}: Received event: {json.dumps(event)}")

    total_processed = 0
    total_written = 0

    try:
        s3 = _get_s3_client()

        for record in event.get("Records", []):
            bucket = record["s3"]["bucket"]["name"]
            key = record["s3"]["object"]["key"]

            logger.info(f"{HANDLER_NAME}: Processing s3://{bucket}/{key}")

            # Get the log file
            response = s3.get_object(Bucket=bucket, Key=key)

            # Decompress and parse
            with gzip.GzipFile(fileobj=response["Body"]) as gz:
                content = gz.read().decode("utf-8")

            # Extract actual domain from S3 key path (e.g., example.com/2025/12/14/...)
            actual_domain = _extract_domain_from_s3_key(key)
            if not actual_domain:
                logger.warning(f"{HANDLER_NAME}: Could not extract domain from key: {key}")
                continue

            items = []
            skipped = 0
            for line in content.split("\n"):
                parsed = _parse_cloudfront_log_line(line)
                if parsed:
                    # Skip static assets based on excluded extensions
                    if _should_exclude_path(parsed["path"]):
                        skipped += 1
                        continue
                    # Override CloudFront distribution domain with actual domain
                    parsed["domain"] = actual_domain
                    items.append(parsed)
                    total_processed += 1

            if skipped > 0:
                logger.debug(f"{HANDLER_NAME}: Skipped {skipped} static asset requests")

            # Batch write to DynamoDB
            if items:
                written = _batch_write_to_dynamodb(items)
                total_written += written
                logger.info(
                    f"{HANDLER_NAME}: Wrote {written} items from {key}"
                )

                # Update rollup counters
                _update_rollups(items)

        logger.info(
            f"{HANDLER_NAME}: Completed. Processed: {total_processed}, Written: {total_written}"
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Success",
                    "processed": total_processed,
                    "written": total_written,
                }
            ),
        }

    except Exception as e:
        logger.exception(f"{HANDLER_NAME}: Error processing logs")
        raise e
