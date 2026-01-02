"""
Cache Builder Lambda

Pre-computes dashboard data from rollups and stores in cache for fast reads.
Triggered by EventBridge on hourly schedule.
"""

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import boto3
from boto3.dynamodb.conditions import Key

# Configure logging
log_level = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

HANDLER_NAME = "cache-builder"

# Environment variables
TABLE_NAME = os.environ.get("TABLE_NAME")
DOMAIN_LIST = os.environ.get("DOMAIN_LIST", "").split(",")

# Cache TTL (2 hours - gives buffer even with hourly refresh)
CACHE_TTL_HOURS = 2

# Cached AWS clients
_dynamodb = None


def _get_dynamodb():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb


def _get_date_range(days: int = 7) -> list:
    """Generate list of date strings for the last N days."""
    dates = []
    today = datetime.now(timezone.utc).date()
    for i in range(days):
        date = today - timedelta(days=i)
        dates.append(date.strftime("%Y-%m-%d"))
    return sorted(dates)


def _build_stats_cache(table, domain: str, dates: list) -> Dict:
    """Build stats cache from rollups."""
    daily_stats = {}
    total_requests = 0
    unique_ips: set = set()

    for date in dates:
        try:
            response = table.get_item(
                Key={"PK": f"ROLLUP#{domain}", "SK": f"STATS#{date}"}
            )
            item = response.get("Item")
            if item:
                day_count = int(item.get("requests", 0))
                daily_stats[date] = day_count
                total_requests += day_count
                if "unique_ips" in item:
                    unique_ips.update(item["unique_ips"])
            else:
                daily_stats[date] = 0
        except Exception as e:
            logger.warning(f"Failed to get stats rollup for {date}: {e}")
            daily_stats[date] = 0

    return {
        "total_requests": total_requests,
        "unique_visitors": len(unique_ips),
        "daily": daily_stats,
    }


def _build_pages_cache(table, domain: str, dates: list, limit: int = 10) -> Dict:
    """Build pages cache from rollups."""
    page_counts = defaultdict(int)

    for date in dates:
        try:
            response = table.query(
                KeyConditionExpression=Key("PK").eq(f"ROLLUP#{domain}") & Key("SK").begins_with(f"PAGE#{date}#"),
            )

            for item in response.get("Items", []):
                sk = item.get("SK", "")
                prefix = f"PAGE#{date}#"
                if sk.startswith(prefix):
                    path = sk[len(prefix):]
                    count = int(item.get("count", 0))
                    page_counts[path] += count

            while "LastEvaluatedKey" in response:
                response = table.query(
                    KeyConditionExpression=Key("PK").eq(f"ROLLUP#{domain}") & Key("SK").begins_with(f"PAGE#{date}#"),
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                for item in response.get("Items", []):
                    sk = item.get("SK", "")
                    prefix = f"PAGE#{date}#"
                    if sk.startswith(prefix):
                        path = sk[len(prefix):]
                        count = int(item.get("count", 0))
                        page_counts[path] += count
        except Exception as e:
            logger.warning(f"Failed to get page rollups for {date}: {e}")

    sorted_pages = sorted(page_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    return {"pages": [{"path": p, "count": c} for p, c in sorted_pages]}


def _build_referrers_cache(table, domain: str, dates: list, limit: int = 10) -> Dict:
    """Build referrers cache from rollups."""
    referrer_counts = defaultdict(int)

    for date in dates:
        try:
            response = table.query(
                KeyConditionExpression=Key("PK").eq(f"ROLLUP#{domain}") & Key("SK").begins_with(f"REF#{date}#"),
            )

            for item in response.get("Items", []):
                sk = item.get("SK", "")
                prefix = f"REF#{date}#"
                if sk.startswith(prefix):
                    ref_domain = sk[len(prefix):]
                    count = int(item.get("count", 0))
                    referrer_counts[ref_domain] += count

            while "LastEvaluatedKey" in response:
                response = table.query(
                    KeyConditionExpression=Key("PK").eq(f"ROLLUP#{domain}") & Key("SK").begins_with(f"REF#{date}#"),
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                for item in response.get("Items", []):
                    sk = item.get("SK", "")
                    prefix = f"REF#{date}#"
                    if sk.startswith(prefix):
                        ref_domain = sk[len(prefix):]
                        count = int(item.get("count", 0))
                        referrer_counts[ref_domain] += count
        except Exception as e:
            logger.warning(f"Failed to get referrer rollups for {date}: {e}")

    sorted_refs = sorted(referrer_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    return {"referrers": [{"domain": r, "count": c} for r, c in sorted_refs]}


def _build_hours_cache(table, domain: str, dates: list) -> Dict:
    """Build hourly traffic cache from rollups."""
    hourly_counts = {str(h).zfill(2): 0 for h in range(24)}

    for date in dates:
        try:
            response = table.query(
                KeyConditionExpression=Key("PK").eq(f"ROLLUP#{domain}") & Key("SK").begins_with(f"HOUR#{date}#"),
            )

            for item in response.get("Items", []):
                sk = item.get("SK", "")
                prefix = f"HOUR#{date}#"
                if sk.startswith(prefix):
                    hour = sk[len(prefix):]
                    if hour in hourly_counts:
                        count = int(item.get("count", 0))
                        hourly_counts[hour] += count

            while "LastEvaluatedKey" in response:
                response = table.query(
                    KeyConditionExpression=Key("PK").eq(f"ROLLUP#{domain}") & Key("SK").begins_with(f"HOUR#{date}#"),
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
                for item in response.get("Items", []):
                    sk = item.get("SK", "")
                    prefix = f"HOUR#{date}#"
                    if sk.startswith(prefix):
                        hour = sk[len(prefix):]
                        if hour in hourly_counts:
                            count = int(item.get("count", 0))
                            hourly_counts[hour] += count
        except Exception as e:
            logger.warning(f"Failed to get hourly rollups for {date}: {e}")

    peak_hour = max(hourly_counts, key=hourly_counts.get)
    total = sum(hourly_counts.values())

    return {
        "hourly": hourly_counts,
        "peak_hour": peak_hour,
        "total": total,
    }


def _write_cache(table, domain: str, cache_type: str, data: Dict, from_date: str, to_date: str):
    """Write cache item to DynamoDB."""
    ttl = int((datetime.now(timezone.utc) + timedelta(hours=CACHE_TTL_HOURS)).timestamp())
    built_at = datetime.now(timezone.utc).isoformat()

    cache_item = {
        "PK": f"CACHE#{domain}",
        "SK": cache_type,
        "data": json.dumps(data),
        "from_date": from_date,
        "to_date": to_date,
        "built_at": built_at,
        "ttl": ttl,
    }

    table.put_item(Item=cache_item)
    logger.info(f"Wrote cache: CACHE#{domain}/{cache_type}")


def lambda_handler(event: Dict, context: Any) -> Dict:
    """
    Main Lambda handler - triggered by EventBridge schedule.

    Builds cache for all domains in DOMAIN_LIST.
    """
    logger.info(f"{HANDLER_NAME}: Starting cache build")
    logger.info(f"{HANDLER_NAME}: Domains: {DOMAIN_LIST}")

    if not TABLE_NAME:
        logger.error("TABLE_NAME not configured")
        return {"statusCode": 500, "body": "TABLE_NAME not configured"}

    domains = [d.strip() for d in DOMAIN_LIST if d.strip()]
    if not domains:
        logger.warning("No domains configured")
        return {"statusCode": 200, "body": "No domains to process"}

    dynamodb = _get_dynamodb()
    table = dynamodb.Table(TABLE_NAME)

    dates = _get_date_range(7)
    from_date = dates[0]
    to_date = dates[-1]

    logger.info(f"{HANDLER_NAME}: Date range: {from_date} to {to_date}")

    results = {}

    for domain in domains:
        logger.info(f"{HANDLER_NAME}: Building cache for {domain}")

        try:
            # Build all cache types
            stats = _build_stats_cache(table, domain, dates)
            _write_cache(table, domain, "stats", stats, from_date, to_date)

            pages = _build_pages_cache(table, domain, dates)
            _write_cache(table, domain, "pages", pages, from_date, to_date)

            referrers = _build_referrers_cache(table, domain, dates)
            _write_cache(table, domain, "referrers", referrers, from_date, to_date)

            hours = _build_hours_cache(table, domain, dates)
            _write_cache(table, domain, "hours", hours, from_date, to_date)

            results[domain] = "success"
            logger.info(f"{HANDLER_NAME}: Cache built for {domain}")

        except Exception as e:
            logger.exception(f"{HANDLER_NAME}: Failed to build cache for {domain}")
            results[domain] = f"error: {str(e)}"

    logger.info(f"{HANDLER_NAME}: Cache build complete")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Cache build complete",
            "results": results,
        }),
    }
