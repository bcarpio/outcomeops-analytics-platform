"""Unit tests for analytics-api Lambda handler."""

import pytest
import json
from unittest.mock import patch, MagicMock


class TestAnalyticsAPIHandler:
    """Tests for the analytics API Lambda handler."""

    @pytest.mark.unit
    def test_get_stats_success(self, mock_dynamodb, sample_analytics_data, sample_api_event):
        """Test getting stats for a valid domain."""
        from handler import lambda_handler

        result = lambda_handler(sample_api_event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["domain"] == "myfantasy.ai"
        assert "total_requests" in body

    @pytest.mark.unit
    def test_get_stats_invalid_domain(self, mock_dynamodb, sample_api_event):
        """Test rejection of unauthorized domain."""
        sample_api_event["pathParameters"]["domain"] = "unauthorized.com"
        sample_api_event["rawPath"] = "/analytics/stats/unauthorized.com"

        from handler import lambda_handler

        result = lambda_handler(sample_api_event, None)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "error" in body

    @pytest.mark.unit
    def test_get_stats_with_date_range(self, mock_dynamodb, sample_analytics_data, sample_api_event):
        """Test filtering by date range."""
        sample_api_event["queryStringParameters"] = {
            "from": "2024-01-15",
            "to": "2024-01-15",
        }

        from handler import lambda_handler

        result = lambda_handler(sample_api_event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["from_date"] == "2024-01-15"
        assert body["to_date"] == "2024-01-15"

    @pytest.mark.unit
    def test_get_pages_success(self, mock_dynamodb, sample_analytics_data):
        """Test getting top pages."""
        event = {
            "version": "2.0",
            "routeKey": "GET /analytics/pages/{domain}",
            "rawPath": "/analytics/pages/myfantasy.ai",
            "headers": {"authorization": "Bearer test-token"},
            "pathParameters": {"domain": "myfantasy.ai"},
            "queryStringParameters": {"limit": "10"},
            "requestContext": {"http": {"method": "GET"}},
        }

        from handler import lambda_handler

        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "pages" in body

    @pytest.mark.unit
    def test_get_referrers_success(self, mock_dynamodb, sample_analytics_data):
        """Test getting top referrers."""
        event = {
            "version": "2.0",
            "routeKey": "GET /analytics/referrers/{domain}",
            "rawPath": "/analytics/referrers/myfantasy.ai",
            "headers": {"authorization": "Bearer test-token"},
            "pathParameters": {"domain": "myfantasy.ai"},
            "queryStringParameters": {},
            "requestContext": {"http": {"method": "GET"}},
        }

        from handler import lambda_handler

        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "referrers" in body

    @pytest.mark.unit
    def test_get_countries_success(self, mock_dynamodb, sample_analytics_data):
        """Test getting visitor countries."""
        event = {
            "version": "2.0",
            "routeKey": "GET /analytics/countries/{domain}",
            "rawPath": "/analytics/countries/myfantasy.ai",
            "headers": {"authorization": "Bearer test-token"},
            "pathParameters": {"domain": "myfantasy.ai"},
            "queryStringParameters": {},
            "requestContext": {"http": {"method": "GET"}},
        }

        from handler import lambda_handler

        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "countries" in body

    @pytest.mark.unit
    def test_handler_returns_cors_headers(self, mock_dynamodb, sample_api_event):
        """Test that CORS headers are included in response."""
        from handler import lambda_handler

        result = lambda_handler(sample_api_event, None)

        assert "Access-Control-Allow-Origin" in result["headers"]
        assert "Access-Control-Allow-Headers" in result["headers"]

    @pytest.mark.unit
    def test_handler_invalid_route(self, mock_dynamodb):
        """Test 404 for unknown route."""
        event = {
            "version": "2.0",
            "routeKey": "GET /unknown/route",
            "rawPath": "/unknown/route",
            "headers": {},
            "requestContext": {"http": {"method": "GET"}},
        }

        from handler import lambda_handler

        result = lambda_handler(event, None)

        assert result["statusCode"] == 404

    @pytest.mark.unit
    def test_handler_missing_domain_param(self, mock_dynamodb):
        """Test 400 for missing domain parameter."""
        event = {
            "version": "2.0",
            "routeKey": "GET /analytics/stats/{domain}",
            "rawPath": "/analytics/stats/",
            "headers": {"authorization": "Bearer test-token"},
            "pathParameters": {},
            "requestContext": {"http": {"method": "GET"}},
        }

        from handler import lambda_handler

        result = lambda_handler(event, None)

        assert result["statusCode"] == 400
