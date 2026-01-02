"""
Analytics Dashboard Authentication Lambda

Magic link authentication for the analytics dashboard.

Routes:
    POST /auth/magic-link - Request magic link email
    POST /auth/verify     - Verify magic link token and get access token
"""

import json
import logging
import os
import time
from typing import Any, Dict

import boto3
import jwt

# Configure logging
log_level = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

HANDLER_NAME = "analytics-auth"

# Environment variables
ENV = os.environ.get("ENV", "dev")
APP_NAME = os.environ.get("APP_NAME", "outcomeops-analytics")
ADMIN_USERS_TABLE = os.environ.get("ADMIN_USERS_TABLE")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "noreply@outcomeops.ai")

# Cached clients and secrets
_dynamodb = None
_ssm_client = None
_ses_client = None
_jwt_secret = None

# Base URL for magic links
BASE_URLS = {
    "dev": "https://analytics.dev.outcomeops.ai",
    "prd": "https://analytics.outcomeops.ai",
}


def _get_dynamodb():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb


def _get_ssm_client():
    global _ssm_client
    if _ssm_client is None:
        _ssm_client = boto3.client("ssm")
    return _ssm_client


def _get_ses_client():
    global _ses_client
    if _ses_client is None:
        _ses_client = boto3.client("ses")
    return _ses_client


def _get_jwt_secret() -> str:
    global _jwt_secret
    if _jwt_secret is None:
        client = _get_ssm_client()
        parameter_name = f"/{ENV}/{APP_NAME}/secrets/jwt_secret"
        response = client.get_parameter(Name=parameter_name, WithDecryption=True)
        _jwt_secret = response["Parameter"]["Value"]
    return _jwt_secret


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
        "body": json.dumps(body),
    }


def _error(status_code: int, message: str) -> Dict:
    return _response(status_code, {"error": message})


def _create_token(email: str, name: str, expires_in: int) -> str:
    """Create a JWT token."""
    now = int(time.time())
    payload = {
        "email": email,
        "name": name,
        "iat": now,
        "exp": now + expires_in,
    }
    secret = _get_jwt_secret()
    return jwt.encode(payload, secret, algorithm="HS256")


def _verify_token(token: str) -> Dict:
    """Verify and decode a JWT token."""
    secret = _get_jwt_secret()
    return jwt.decode(token, secret, algorithms=["HS256"])


def _get_admin_user(email: str) -> Dict | None:
    """Get admin user from DynamoDB."""
    dynamodb = _get_dynamodb()
    table = dynamodb.Table(ADMIN_USERS_TABLE)
    response = table.get_item(Key={"email": email.lower()})
    return response.get("Item")


def _send_magic_link_email(email: str, magic_link: str, name: str) -> None:
    """Send magic link email via SES."""
    ses = _get_ses_client()

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .button {{ display: inline-block; padding: 12px 24px; background-color: #0284c7; color: white; text-decoration: none; border-radius: 8px; font-weight: 500; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Sign in to Analytics Dashboard</h2>
            <p>Hi {name},</p>
            <p>Click the button below to sign in to the analytics dashboard. This link expires in 15 minutes.</p>
            <p style="margin: 30px 0;">
                <a href="{magic_link}" class="button">Sign In</a>
            </p>
            <p>Or copy and paste this URL into your browser:</p>
            <p style="word-break: break-all; color: #0284c7;">{magic_link}</p>
            <div class="footer">
                <p>If you didn't request this email, you can safely ignore it.</p>
                <p>OutcomeOps Analytics</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
Sign in to Analytics Dashboard

Hi {name},

Click the link below to sign in to the analytics dashboard. This link expires in 15 minutes.

{magic_link}

If you didn't request this email, you can safely ignore it.

OutcomeOps Analytics
"""

    ses.send_email(
        Source=SENDER_EMAIL,
        Destination={"ToAddresses": [email]},
        Message={
            "Subject": {"Data": "Your Analytics Dashboard Login Link"},
            "Body": {
                "Html": {"Data": html_body},
                "Text": {"Data": text_body},
            },
        },
    )


def handle_magic_link(event: Dict) -> Dict:
    """POST /auth/magic-link - Request magic link email."""
    try:
        body = json.loads(event.get("body", "{}"))
        email = body.get("email", "").lower().strip()

        if not email:
            return _error(400, "Missing email")

        # Check if user is an admin
        admin_user = _get_admin_user(email)
        if not admin_user:
            # Don't reveal if user exists or not
            logger.info(f"{HANDLER_NAME}: Magic link requested for non-admin email: {email}")
            return _response(200, {"message": "If you are an admin, check your email"})

        if not admin_user.get("active", True):
            logger.info(f"{HANDLER_NAME}: Magic link requested for inactive admin: {email}")
            return _response(200, {"message": "If you are an admin, check your email"})

        name = admin_user.get("name", email.split("@")[0])

        # Create magic link token (15 min expiry)
        token = _create_token(email, name, expires_in=900)
        base_url = BASE_URLS.get(ENV, BASE_URLS["dev"])
        magic_link = f"{base_url}/login?token={token}"

        # Send email
        _send_magic_link_email(email, magic_link, name)

        logger.info(f"{HANDLER_NAME}: Magic link sent to admin: {email}")
        return _response(200, {"message": "If you are an admin, check your email"})

    except Exception as e:
        logger.exception(f"{HANDLER_NAME}: Error in magic link request")
        return _error(500, f"Internal error: {e}")


def handle_verify(event: Dict) -> Dict:
    """POST /auth/verify - Verify magic link token."""
    try:
        body = json.loads(event.get("body", "{}"))
        token = body.get("token")

        if not token:
            return _error(400, "Missing token")

        # Verify token
        try:
            payload = _verify_token(token)
        except jwt.ExpiredSignatureError:
            return _error(401, "Token expired")
        except jwt.InvalidTokenError as e:
            return _error(401, f"Invalid token: {e}")

        email = payload.get("email")
        name = payload.get("name")

        # Verify user is still an admin
        admin_user = _get_admin_user(email)
        if not admin_user or not admin_user.get("active", True):
            return _error(401, "Unauthorized")

        # Create access token (24 hour expiry)
        access_token = _create_token(email, name, expires_in=86400)

        return _response(200, {
            "access_token": access_token,
            "user": {
                "email": email,
                "name": name,
            },
        })

    except Exception as e:
        logger.exception(f"{HANDLER_NAME}: Error in token verification")
        return _error(500, f"Internal error: {e}")


def lambda_handler(event: Dict, context: Any) -> Dict:
    """Main Lambda handler - routes requests to appropriate handlers."""
    logger.info(f"{HANDLER_NAME}: Received event: {json.dumps(event)}")

    # Handle CORS preflight
    http_method = event.get("requestContext", {}).get("http", {}).get("method")
    if http_method == "OPTIONS":
        return _response(200, {})

    route_key = event.get("routeKey", "")

    routes = {
        "POST /auth/magic-link": handle_magic_link,
        "POST /auth/verify": handle_verify,
    }

    handler = routes.get(route_key)
    if handler:
        return handler(event)

    return _error(404, f"Route not found: {route_key}")
