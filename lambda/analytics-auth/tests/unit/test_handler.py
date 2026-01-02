"""Unit tests for analytics-auth Lambda handler."""

import pytest
import json
from unittest.mock import patch, MagicMock
from freezegun import freeze_time
from moto import mock_aws
import boto3


@pytest.fixture
def mock_aws_services(aws_credentials):
    """Set up mocked DynamoDB, SSM, and SES together."""
    with mock_aws():
        # Create DynamoDB table
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

        # Create SSM parameter
        ssm = boto3.client("ssm", region_name="us-west-2")
        ssm.put_parameter(
            Name="/test/outcomeops-analytics/secrets/jwt_secret",
            Value="test-jwt-secret-key-for-testing",
            Type="SecureString",
        )

        # Verify SES sender
        ses = boto3.client("ses", region_name="us-west-2")
        ses.verify_email_identity(EmailAddress="noreply@outcomeops.ai")

        yield dynamodb, table, ssm, ses


class TestAnalyticsAuthHandler:
    """Tests for the analytics auth Lambda handler."""

    def test_magic_link_success(self, mock_aws_services, sample_magic_link_event):
        """Test sending magic link to valid admin."""
        dynamodb, table, ssm, ses = mock_aws_services

        # Create admin user
        table.put_item(Item={
            "email": "admin@outcomeops.ai",
            "name": "Admin User",
            "active": True,
        })

        # Clear cached clients
        import handler
        handler._dynamodb = None
        handler._ssm_client = None
        handler._ses_client = None
        handler._jwt_secret = None

        with patch.object(handler, '_send_magic_link_email') as mock_send:
            mock_send.return_value = None
            result = handler.lambda_handler(sample_magic_link_event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "message" in body
        mock_send.assert_called_once()

    def test_magic_link_non_admin_returns_200(self, mock_aws_services, sample_magic_link_event):
        """Test that non-admin email returns 200 (don't reveal if user exists)."""
        dynamodb, table, ssm, ses = mock_aws_services

        # Don't create admin user
        import handler
        handler._dynamodb = None
        handler._ssm_client = None
        handler._ses_client = None
        handler._jwt_secret = None

        result = handler.lambda_handler(sample_magic_link_event, None)

        # Should return 200 to not reveal if user exists
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["message"] == "If you are an admin, check your email"

    def test_magic_link_missing_email(self, mock_aws_services):
        """Test handling of missing email in request."""
        dynamodb, table, ssm, ses = mock_aws_services

        event = {
            "version": "2.0",
            "routeKey": "POST /auth/magic-link",
            "rawPath": "/auth/magic-link",
            "headers": {"content-type": "application/json"},
            "body": "{}",
            "requestContext": {"http": {"method": "POST"}},
        }

        import handler
        handler._dynamodb = None

        result = handler.lambda_handler(event, None)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "error" in body

    @freeze_time("2024-01-15 12:00:00")
    def test_verify_success(self, mock_aws_services):
        """Test verifying valid magic link token."""
        dynamodb, table, ssm, ses = mock_aws_services

        # Create admin user
        table.put_item(Item={
            "email": "admin@outcomeops.ai",
            "name": "Admin User",
            "active": True,
        })

        import handler
        handler._dynamodb = None
        handler._ssm_client = None
        handler._jwt_secret = None

        # Create a valid token using the handler's function
        token = handler._create_token("admin@outcomeops.ai", "Admin User", expires_in=900)

        event = {
            "version": "2.0",
            "routeKey": "POST /auth/verify",
            "rawPath": "/auth/verify",
            "headers": {"content-type": "application/json"},
            "body": json.dumps({"token": token}),
            "requestContext": {"http": {"method": "POST"}},
        }

        result = handler.lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "access_token" in body
        assert "user" in body
        assert body["user"]["email"] == "admin@outcomeops.ai"

    @freeze_time("2024-01-15 12:00:00")
    def test_verify_expired_token(self, mock_aws_services):
        """Test rejection of expired token."""
        dynamodb, table, ssm, ses = mock_aws_services

        import handler
        handler._dynamodb = None
        handler._ssm_client = None
        handler._jwt_secret = None

        # Create an expired token (negative expiry)
        import jwt
        from datetime import datetime, timedelta
        secret = handler._get_jwt_secret()
        token = jwt.encode(
            {
                "email": "admin@outcomeops.ai",
                "name": "Admin User",
                "exp": datetime.utcnow() - timedelta(hours=1),
                "iat": datetime.utcnow() - timedelta(hours=2),
            },
            secret,
            algorithm="HS256",
        )

        event = {
            "version": "2.0",
            "routeKey": "POST /auth/verify",
            "rawPath": "/auth/verify",
            "headers": {"content-type": "application/json"},
            "body": json.dumps({"token": token}),
            "requestContext": {"http": {"method": "POST"}},
        }

        result = handler.lambda_handler(event, None)

        assert result["statusCode"] == 401
        body = json.loads(result["body"])
        assert "error" in body

    def test_verify_invalid_token(self, mock_aws_services):
        """Test rejection of tampered/invalid token."""
        dynamodb, table, ssm, ses = mock_aws_services

        import handler
        handler._dynamodb = None
        handler._ssm_client = None
        handler._jwt_secret = None

        event = {
            "version": "2.0",
            "routeKey": "POST /auth/verify",
            "rawPath": "/auth/verify",
            "headers": {"content-type": "application/json"},
            "body": json.dumps({"token": "invalid.token.here"}),
            "requestContext": {"http": {"method": "POST"}},
        }

        result = handler.lambda_handler(event, None)

        assert result["statusCode"] == 401

    def test_handler_invalid_route(self, mock_aws_services):
        """Test 404 for unknown route."""
        dynamodb, table, ssm, ses = mock_aws_services

        event = {
            "version": "2.0",
            "routeKey": "GET /auth/unknown",
            "rawPath": "/auth/unknown",
            "headers": {},
            "requestContext": {"http": {"method": "GET"}},
        }

        import handler
        handler._dynamodb = None

        result = handler.lambda_handler(event, None)

        assert result["statusCode"] == 404

    def test_handler_returns_cors_headers(self, mock_aws_services, sample_magic_link_event):
        """Test that CORS headers are included."""
        dynamodb, table, ssm, ses = mock_aws_services

        import handler
        handler._dynamodb = None

        result = handler.lambda_handler(sample_magic_link_event, None)

        assert "Access-Control-Allow-Origin" in result["headers"]
