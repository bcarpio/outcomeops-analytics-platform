# OutcomeOps Analytics Platform

Multi-domain serverless analytics platform for first-party website traffic tracking.

## Architecture

```
CloudFront Logs → S3 → Lambda (log-parser) → DynamoDB
                                                  ↓
React Dashboard ← API Gateway ← Lambda (analytics-api)
```

### Components

| Component | Description |
|-----------|-------------|
| **Log Parser Lambda** | Parses CloudFront access logs and writes analytics events to DynamoDB |
| **Analytics API Lambda** | Query API for stats, pages, referrers, hours, journeys, sessions, and flows |
| **Analytics Auth Lambda** | Magic link authentication for dashboard access |
| **Journey Tracker Lambda** | First-party tracking endpoint for user journey/session data |
| **DynamoDB** | Single-table design for analytics events + sessions table + admin users table |
| **CloudFront** | Dashboard hosting at `analytics.outcomeops.ai` |
| **API Gateway** | HTTP API at `api.analytics.outcomeops.ai` |
| **Tracking API Gateways** | Per-domain tracking endpoints at `t.{domain}` |

### Domains

| Environment | Dashboard | API |
|-------------|-----------|-----|
| Production | `analytics.outcomeops.ai` | `api.analytics.outcomeops.ai` |
| Development | `analytics.dev.outcomeops.ai` | `api.analytics.dev.outcomeops.ai` |

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform >= 1.5
- Python 3.12
- Node.js 20+
- pnpm

## Pre-deployment Setup

Before deploying infrastructure, create the JWT secret in SSM Parameter Store:

```bash
# Dev environment
aws ssm put-parameter \
  --name "/dev/outcomeops-analytics/secrets/jwt_secret" \
  --type "SecureString" \
  --value "$(openssl rand -base64 32)"

# Prd environment (use a different secret!)
aws ssm put-parameter \
  --name "/prd/outcomeops-analytics/secrets/jwt_secret" \
  --type "SecureString" \
  --value "$(openssl rand -base64 32)"
```

## Project Structure

```
.
├── lambda/
│   ├── analytics-api/      # Query API Lambda
│   ├── analytics-auth/     # Magic link auth Lambda
│   ├── journey-tracker/    # First-party tracking Lambda
│   └── log-parser/         # CloudFront log parser Lambda
├── terraform/
│   ├── main.tf             # Provider configuration
│   ├── lambda.tf           # Lambda function modules
│   ├── dynamodb.tf         # DynamoDB tables
│   ├── s3.tf               # S3 buckets
│   ├── api-gateway.tf      # API Gateway + custom domain
│   ├── journey-tracking.tf # Per-domain tracking API Gateways
│   ├── cloudfront.tf       # Dashboard CloudFront distribution
│   └── *.tfvars            # Environment-specific variables
├── ui/
│   ├── src/
│   │   ├── api/            # API client
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── tracker/        # First-party tracking library
│   │   └── utils/          # Utilities (auth, etc.)
│   └── package.json
└── requirements-dev.txt    # Python test dependencies
```

## Development

### Setup

```bash
# Install UI dependencies
make ui-install

# Run UI development server
make ui-dev
```

### Testing

```bash
# Setup Python virtual environment (one time)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# Run all Lambda unit tests
source .venv/bin/activate
make test-unit

# Run tests with coverage
make test-coverage
```

### Terraform

```bash
# Initialize Terraform
make tf-init ENV=dev

# Plan changes
make tf-plan ENV=dev

# Apply changes
make tf-apply ENV=dev
```

### Deploy Dashboard

```bash
# Build and deploy UI to S3/CloudFront
make ui-deploy ENV=dev
```

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/magic-link` | Request magic link email |
| POST | `/auth/verify` | Verify magic link token |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analytics/stats/{domain}` | Get traffic stats |
| GET | `/analytics/pages/{domain}` | Get top pages |
| GET | `/analytics/referrers/{domain}` | Get top referrers |
| GET | `/analytics/hours/{domain}` | Get traffic by hour of day |
| GET | `/analytics/countries/{domain}` | Get visitor countries |
| GET | `/analytics/journeys/{domain}` | Get journey/session summary stats |
| GET | `/analytics/sessions/{domain}` | Get all sessions with referrer, filters, and rollup |
| GET | `/analytics/sessions/{domain}/{session_id}` | Get session detail with full page journey |
| GET | `/analytics/flows/{domain}` | Get page flow data (entry/exit pages, transitions) |
| GET | `/analytics/hallucinations/{domain}` | Get AI hallucination metrics from 404 tracking |

Query parameters: `from`, `to` (date range), `limit`, `referrer` (filter by referrer domain), `page` (filter by entry page)

### Tracking (First-Party)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `https://t.{domain}/t` | Single tracking event |
| POST | `https://t.{domain}/t/batch` | Batch tracking events (sendBeacon) |

Each tracked domain has its own tracking subdomain (e.g., `t.myfantasy.ai`, `t.outcomeops.ai`, `t.thetek.net`).

### Client Tracking Library

The tracking library (`outcomeops-tracker.ts`) is bundled directly into each client application rather than loaded as an external script. This avoids an additional network request and ensures the tracker is always available.

**Integration:**

1. Copy `ui/src/tracker/outcomeops-tracker.ts` to your project
2. Import and initialize in your app's entry point:

```typescript
import { OutcomeOpsTracker } from './lib/outcomeops-tracker'

OutcomeOpsTracker.init({
  domain: 'yourdomain.com',
  endpoint: 'https://t.yourdomain.com',
})
```

The tracker automatically:
- Tracks pageviews and SPA navigation
- Manages sessions with localStorage
- Batches events and uses sendBeacon for reliability
- Tracks scroll depth milestones (25%, 50%, 75%, 100%)
- Detects AI-hallucinated 404 URLs

## Tracked Domains

Configure domains in your tfvars file. Each domain's CloudFront distribution sends access logs to this platform's S3 bucket for processing.

## Metrics Definitions

### CloudFront Log Metrics (Server-Side)

Data from CloudFront access logs, parsed by the log-parser Lambda.

| Metric | Description |
|--------|-------------|
| **Total Requests** | Count of HTTP requests stored in DynamoDB (excludes filtered extensions like `.js`, `.css`, `.png`) |
| **Unique Visitors** | Distinct client IP addresses in the date range |
| **Daily Requests** | Request count broken down by date |
| **Top Pages** | Most requested URL paths |
| **Top Referrers** | Most common referrer domains (aggregated) |
| **Hourly Traffic** | Requests aggregated by hour of day (0-23 UTC) |

### Session Metrics (Client-Side)

Data from the first-party tracking library. All sessions are shown in a unified view with filtering.

| Metric | Description |
|--------|-------------|
| **Referrer** | Domain that sent traffic, or "(direct)" for no referrer/self-referral |
| **Entry Page** | First page visited in the session |
| **Pages** | Number of pages viewed in the session |
| **Duration** | Total time spent in the session |
| **Rollup** | When filtering by entry page, shows count by referrer domain |

### Journey Metrics (Client-Side)

Aggregated metrics from the first-party tracking library.

| Metric | Description |
|--------|-------------|
| **Total Sessions** | Count of unique browser sessions |
| **Total Pageviews** | Count of pageview events across all sessions |
| **Avg Pages/Session** | Mean number of pages viewed per session |
| **Avg Session Duration** | Mean time (seconds) from first to last event |
| **Bounce Rate** | % of sessions with 1 pageview and <10s duration |
| **Engaged Sessions** | Sessions with >30s duration or >1 pageview |
| **Engaged Rate** | % of sessions that are engaged |
| **Blog Sessions** | Sessions starting on `/blog*` paths |
| **Avg Blog Time** | Mean duration of blog sessions |

### AI Hallucination Metrics (Client-Side)

Tracks 404 errors and detects AI-generated URLs that don't exist on the site.

| Metric | Description |
|--------|-------------|
| **Total 404s** | Count of not_found events in the period |
| **AI Hallucinations** | Count of 404s matching AI-generated URL patterns |
| **AI Percentage** | Percentage of 404s that are AI hallucinations |
| **Patterns** | Breakdown by detected AI pattern type |
| **Top Paths** | Most common 404 paths with AI indicator |
| **Recent Hallucinations** | Last 10 AI-generated 404 events |

## Configuration

### Terraform Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `domain_list` | Domains to track | `["myfantasy.ai", "outcomeops.ai", "thetek.net"]` |
| `excluded_extensions` | File extensions to exclude from analytics | See below |

### Excluded Extensions

Static assets are filtered out before writing to DynamoDB. Configure via `excluded_extensions` in tfvars:

```hcl
excluded_extensions = [
  ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".webp",
  ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".map",
  ".txt", ".pdf", ".php"
]
```

To track all requests (no filtering), set to an empty list:

```hcl
excluded_extensions = []
```

## License

Proprietary - OutcomeOps
