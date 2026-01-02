"""Pytest configuration and shared fixtures for log-parser tests."""

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
def mock_s3(aws_credentials):
    """Create mocked S3 bucket with sample log file."""
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-west-2")
        bucket_name = "test-analytics-logs"
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
        )
        yield s3, bucket_name


@pytest.fixture
def mock_dynamodb(aws_credentials):
    """Create mocked DynamoDB table."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-west-2")
        table = dynamodb.create_table(
            TableName="test-analytics-events",
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
        yield dynamodb, table


@pytest.fixture
def sample_s3_event():
    """Sample S3 event for Lambda trigger."""
    return {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "awsRegion": "us-west-2",
                "eventTime": "2024-01-15T12:00:00.000Z",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": "test-analytics-logs"},
                    "object": {"key": "logs/E1234567890.2024-01-15-12.abcd1234.gz"},
                },
            }
        ]
    }


@pytest.fixture
def sample_cloudfront_log():
    """Sample CloudFront access log content."""
    return """#Version: 1.0
#Fields: date time x-edge-location sc-bytes c-ip cs-method cs(Host) cs-uri-stem sc-status cs(Referer) cs(User-Agent) cs-uri-query cs(Cookie) x-edge-result-type x-edge-request-id x-host-header cs-protocol cs-bytes time-taken x-forwarded-for ssl-protocol ssl-cipher x-edge-response-result-type cs-protocol-version fle-status fle-encrypted-fields c-port time-to-first-byte x-edge-detailed-result-type sc-content-type sc-content-len sc-range-start sc-range-end
2024-01-15	12:00:00	SEA19-C1	1234	192.168.1.1	GET	d111111abcdef8.cloudfront.net	/	200	https://google.com/	Mozilla/5.0%20(Windows%20NT%2010.0;%20Win64;%20x64)	-	-	Hit	abcd1234	myfantasy.ai	https	567	0.001	-	TLSv1.3	TLS_AES_128_GCM_SHA256	Hit	HTTP/2.0	-	-	12345	0.001	Hit	text/html	5678	-	-
2024-01-15	12:00:01	SEA19-C1	2345	192.168.1.2	GET	d111111abcdef8.cloudfront.net	/about	200	-	Mozilla/5.0%20(Macintosh;%20Intel%20Mac%20OS%20X%2010_15_7)	-	-	Hit	efgh5678	myfantasy.ai	https	789	0.002	-	TLSv1.3	TLS_AES_128_GCM_SHA256	Hit	HTTP/2.0	-	-	12346	0.002	Hit	text/html	6789	-	-
"""
