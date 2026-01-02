"""Pytest configuration and shared fixtures for analytics-auth tests."""

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
    monkeypatch.setenv("ADMIN_USERS_TABLE", "test-admin-users")
    monkeypatch.setenv("SENDER_EMAIL", "noreply@outcomeops.ai")
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
    """Create mocked DynamoDB table for admin users."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-west-2")
        table = dynamodb.create_table(
            TableName="test-admin-users",
            KeySchema=[
                {"AttributeName": "email", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "email", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
        yield dynamodb, table


@pytest.fixture
def mock_ssm(aws_credentials):
    """Create mocked SSM with JWT secret."""
    with mock_aws():
        ssm = boto3.client("ssm", region_name="us-west-2")
        ssm.put_parameter(
            Name="/test/outcomeops-analytics/secrets/jwt_secret",
            Value="test-jwt-secret-key-for-testing",
            Type="SecureString",
        )
        yield ssm


@pytest.fixture
def mock_ses(aws_credentials):
    """Create mocked SES client."""
    with mock_aws():
        ses = boto3.client("ses", region_name="us-west-2")
        # Verify sender email (required for SES)
        ses.verify_email_identity(EmailAddress="noreply@outcomeops.ai")
        yield ses


@pytest.fixture
def sample_admin_user(mock_dynamodb):
    """Create sample admin user in DynamoDB."""
    _, table = mock_dynamodb

    user = {
        "email": "admin@outcomeops.ai",
        "name": "Admin User",
        "created_at": "2024-01-01T00:00:00Z",
        "active": True,
    }
    table.put_item(Item=user)
    return user


@pytest.fixture
def sample_magic_link_event():
    """Sample API Gateway event for magic link request."""
    return {
        "version": "2.0",
        "routeKey": "POST /auth/magic-link",
        "rawPath": "/auth/magic-link",
        "headers": {
            "content-type": "application/json",
        },
        "body": '{"email": "admin@outcomeops.ai"}',
        "requestContext": {
            "http": {
                "method": "POST",
                "path": "/auth/magic-link",
            }
        },
    }


@pytest.fixture
def sample_verify_event():
    """Sample API Gateway event for token verification."""
    return {
        "version": "2.0",
        "routeKey": "POST /auth/verify",
        "rawPath": "/auth/verify",
        "headers": {
            "content-type": "application/json",
        },
        "body": '{"token": "test-magic-link-token"}',
        "requestContext": {
            "http": {
                "method": "POST",
                "path": "/auth/verify",
            }
        },
    }
