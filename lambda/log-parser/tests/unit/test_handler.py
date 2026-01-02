"""Unit tests for log-parser Lambda handler."""

import pytest
import gzip
import json
from unittest.mock import patch, MagicMock
from moto import mock_aws
import boto3


@pytest.fixture
def mock_aws_services(aws_credentials):
    """Set up mocked S3 and DynamoDB together."""
    with mock_aws():
        # Create S3 bucket
        s3 = boto3.client("s3", region_name="us-west-2")
        s3.create_bucket(
            Bucket="test-analytics-logs",
            CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
        )

        # Create DynamoDB table
        dynamodb = boto3.resource("dynamodb", region_name="us-west-2")
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

        yield s3, dynamodb, table


class TestParseCloudFrontLogLine:
    """Tests for the log line parser function."""

    def test_parses_valid_log_line(self):
        """Test parsing a valid CloudFront log line."""
        # Import after env vars are set
        from handler import _parse_cloudfront_log_line

        log_line = "2024-01-15\t12:00:00\tSEA19\t1234\t192.168.1.1\tGET\tmyfantasy.ai\t/\t200\thttps://google.com/\tMozilla/5.0\t-\t-\tHit\tabcd1234\tmyfantasy.ai\thttps\t567\t0.001\t-\tTLSv1.3"

        result = _parse_cloudfront_log_line(log_line)

        assert result is not None
        assert result["domain"] == "myfantasy.ai"
        assert result["path"] == "/"
        assert result["status"] == "200"
        assert result["timestamp"] == "2024-01-15T12:00:00Z"

    def test_skips_comment_lines(self):
        """Test that comment lines are skipped."""
        from handler import _parse_cloudfront_log_line

        result = _parse_cloudfront_log_line("#Version: 1.0")
        assert result is None

        result = _parse_cloudfront_log_line("#Fields: date time ...")
        assert result is None

    def test_skips_malformed_lines(self):
        """Test that malformed lines are skipped."""
        from handler import _parse_cloudfront_log_line

        result = _parse_cloudfront_log_line("not enough fields")
        assert result is None

    def test_extracts_referrer_domain(self):
        """Test referrer domain extraction."""
        from handler import _parse_cloudfront_log_line

        log_line = "2024-01-15\t12:00:00\tSEA19\t1234\t192.168.1.1\tGET\tmyfantasy.ai\t/\t200\thttps://google.com/search\tMozilla/5.0\t-\t-\tHit\tabcd1234\tmyfantasy.ai\thttps\t567\t0.001\t-\tTLSv1.3"

        result = _parse_cloudfront_log_line(log_line)

        assert result is not None
        assert result["referrer_domain"] == "google.com"

    def test_handles_missing_referrer(self):
        """Test handling of missing referrer (-)."""
        from handler import _parse_cloudfront_log_line

        log_line = "2024-01-15\t12:00:00\tSEA19\t1234\t192.168.1.1\tGET\tmyfantasy.ai\t/about\t200\t-\tMozilla/5.0\t-\t-\tHit\tabcd1234\tmyfantasy.ai\thttps\t567\t0.001\t-\tTLSv1.3"

        result = _parse_cloudfront_log_line(log_line)

        assert result is not None
        assert result["referrer"] is None
        assert result["referrer_domain"] is None


class TestLambdaHandler:
    """Tests for the Lambda handler."""

    def test_handler_success_with_valid_log(
        self, mock_aws_services, sample_s3_event, sample_cloudfront_log
    ):
        """Test parsing valid CloudFront log file."""
        s3, dynamodb, table = mock_aws_services

        # Upload gzipped log file
        log_bytes = gzip.compress(sample_cloudfront_log.encode("utf-8"))
        s3.put_object(
            Bucket="test-analytics-logs",
            Key="logs/E1234567890.2024-01-15-12.abcd1234.gz",
            Body=log_bytes,
        )

        # Clear cached clients to use mocked ones
        import handler
        handler._s3_client = None
        handler._dynamodb = None

        result = handler.lambda_handler(sample_s3_event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["processed"] == 2  # Two valid log lines in sample
        assert body["written"] == 2

    def test_handler_skips_comment_lines(self, mock_aws_services, sample_s3_event):
        """Test that comment lines in logs are skipped."""
        s3, dynamodb, table = mock_aws_services

        log_content = """#Version: 1.0
#Fields: date time x-edge-location
# This is a comment
"""
        log_bytes = gzip.compress(log_content.encode("utf-8"))
        s3.put_object(
            Bucket="test-analytics-logs",
            Key="logs/E1234567890.2024-01-15-12.abcd1234.gz",
            Body=log_bytes,
        )

        import handler
        handler._s3_client = None
        handler._dynamodb = None

        result = handler.lambda_handler(sample_s3_event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["processed"] == 0

    def test_handler_fails_with_missing_s3_key(self, mock_aws_services, sample_s3_event):
        """Test error handling when S3 object doesn't exist."""
        s3, dynamodb, table = mock_aws_services

        import handler
        handler._s3_client = None
        handler._dynamodb = None

        # Don't upload any file - should raise exception
        with pytest.raises(Exception):
            handler.lambda_handler(sample_s3_event, None)
