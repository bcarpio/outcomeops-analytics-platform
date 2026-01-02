"""Pytest configuration and shared fixtures for analytics-api tests."""

import os
import sys
import pytest
import boto3
from moto import mock_aws

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    """Set required environment variables for all tests."""
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("APP_NAME", "outcomeops-analytics")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("TABLE_NAME", "test-analytics-events")
    monkeypatch.setenv("SESSIONS_TABLE", "test-analytics-sessions")
    monkeypatch.setenv("ALLOWED_DOMAINS", "myfantasy.ai,outcomeops.ai,thetek.net")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-west-2")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-west-2"


@pytest.fixture
def mock_dynamodb(aws_credentials):
    """Create mocked DynamoDB tables."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-west-2")

        # Analytics events table (CloudFront log data)
        # Schema: PK = "{domain}#{date}", SK = "{timestamp}#{request_id}"
        table = dynamodb.create_table(
            TableName="test-analytics-events",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()

        # Sessions table (journey tracking data)
        # Schema: PK = "SESSION#{session_id}", SK = "EVENT#{timestamp}#{id}"
        # GSI1: GSI1PK = "DOMAIN#{domain}#DATE#{date}", GSI1SK = "SESSION#{session_id}"
        sessions_table = dynamodb.create_table(
            TableName="test-analytics-sessions",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI1PK", "AttributeType": "S"},
                {"AttributeName": "GSI1SK", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI1",
                    "KeySchema": [
                        {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        sessions_table.wait_until_exists()

        yield dynamodb, table, sessions_table


@pytest.fixture
def sample_analytics_data(mock_dynamodb):
    """Populate DynamoDB with sample analytics data."""
    _, table, _ = mock_dynamodb

    # Sample page view events matching handler schema
    # PK = "{domain}#{date}", SK = "{timestamp}#{request_id}"
    items = [
        {
            "PK": "myfantasy.ai#2024-01-15",
            "SK": "2024-01-15T12:00:00Z#uuid1",
            "domain": "myfantasy.ai",
            "path": "/",
            "referrer_domain": "google.com",
            "country": "US",
            "timestamp": "2024-01-15T12:00:00Z",
            "client_ip": "192.168.1.1",
        },
        {
            "PK": "myfantasy.ai#2024-01-15",
            "SK": "2024-01-15T12:30:00Z#uuid2",
            "domain": "myfantasy.ai",
            "path": "/about",
            "referrer_domain": "twitter.com",
            "country": "CA",
            "timestamp": "2024-01-15T12:30:00Z",
            "client_ip": "192.168.1.2",
        },
        {
            "PK": "myfantasy.ai#2024-01-15",
            "SK": "2024-01-15T14:00:00Z#uuid3",
            "domain": "myfantasy.ai",
            "path": "/",
            "referrer_domain": "google.com",
            "country": "US",
            "timestamp": "2024-01-15T14:00:00Z",
            "client_ip": "192.168.1.1",  # Same visitor
        },
    ]

    for item in items:
        table.put_item(Item=item)

    return items


@pytest.fixture
def sample_sessions_data(mock_dynamodb):
    """Populate DynamoDB with sample session/journey data."""
    _, _, sessions_table = mock_dynamodb

    # Sample session events
    items = [
        # Session 1: Multi-page session
        {
            "PK": "SESSION#sess-001",
            "SK": "EVENT#2024-01-15T12:00:00Z#evt1",
            "GSI1PK": "DOMAIN#myfantasy.ai#DATE#2024-01-15",
            "GSI1SK": "SESSION#sess-001",
            "session_id": "sess-001",
            "domain": "myfantasy.ai",
            "event_type": "pageview",
            "path": "/",
            "timestamp": "2024-01-15T12:00:00Z",
        },
        {
            "PK": "SESSION#sess-001",
            "SK": "EVENT#2024-01-15T12:00:30Z#evt2",
            "GSI1PK": "DOMAIN#myfantasy.ai#DATE#2024-01-15",
            "GSI1SK": "SESSION#sess-001",
            "session_id": "sess-001",
            "domain": "myfantasy.ai",
            "event_type": "navigation",
            "path": "/about",
            "previous_path": "/",
            "timestamp": "2024-01-15T12:00:30Z",
        },
        {
            "PK": "SESSION#sess-001",
            "SK": "EVENT#2024-01-15T12:01:00Z#evt3",
            "GSI1PK": "DOMAIN#myfantasy.ai#DATE#2024-01-15",
            "GSI1SK": "SESSION#sess-001",
            "session_id": "sess-001",
            "domain": "myfantasy.ai",
            "event_type": "time_on_page",
            "time_on_page": 60,
            "timestamp": "2024-01-15T12:01:00Z",
        },
        # Session 2: Bounce session
        {
            "PK": "SESSION#sess-002",
            "SK": "EVENT#2024-01-15T13:00:00Z#evt4",
            "GSI1PK": "DOMAIN#myfantasy.ai#DATE#2024-01-15",
            "GSI1SK": "SESSION#sess-002",
            "session_id": "sess-002",
            "domain": "myfantasy.ai",
            "event_type": "pageview",
            "path": "/blog/post-1",
            "timestamp": "2024-01-15T13:00:00Z",
        },
        {
            "PK": "SESSION#sess-002",
            "SK": "EVENT#2024-01-15T13:00:05Z#evt5",
            "GSI1PK": "DOMAIN#myfantasy.ai#DATE#2024-01-15",
            "GSI1SK": "SESSION#sess-002",
            "session_id": "sess-002",
            "domain": "myfantasy.ai",
            "event_type": "time_on_page",
            "time_on_page": 5,
            "timestamp": "2024-01-15T13:00:05Z",
        },
    ]

    for item in items:
        sessions_table.put_item(Item=item)

    return items


@pytest.fixture
def sample_api_event():
    """Sample API Gateway event."""
    return {
        "version": "2.0",
        "routeKey": "GET /analytics/stats/{domain}",
        "rawPath": "/analytics/stats/myfantasy.ai",
        "headers": {
            "authorization": "Bearer test-token",
            "content-type": "application/json",
        },
        "pathParameters": {"domain": "myfantasy.ai"},
        "queryStringParameters": {
            "from": "2024-01-01",
            "to": "2024-01-31",
        },
        "requestContext": {
            "http": {
                "method": "GET",
                "path": "/analytics/stats/myfantasy.ai",
            }
        },
    }


@pytest.fixture
def valid_jwt_token():
    """Generate a valid JWT token for testing."""
    import jwt
    from datetime import datetime, timedelta

    payload = {
        "sub": "admin@outcomeops.ai",
        "email": "admin@outcomeops.ai",
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, "test-secret", algorithm="HS256")
