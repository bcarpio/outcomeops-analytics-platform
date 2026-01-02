# Claude Guidance for OutcomeOps Analytics Platform

Multi-domain serverless analytics platform for myfantasy.ai, outcomeops.ai, and thetek.net.

## Knowledge Base

Query before implementing:
```bash
/home/bcarpio/Projects/github/outcome-ops-ai-assist-private/scripts/outcome-ops-assist "your question here" --topK 3
```

## Critical Rules

- **Ask, Don't Guess** - Use AskUserQuestion tool when unclear
- **No Push** - Do not push unless explicitly requested
- **No Amend** - Never use `git commit --amend`
- **No Emojis** - None in commits, docs, or code

## Commits

```
<type>(<scope>): <description>
```
Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`
Scopes: `lambda`, `terraform`, `api`, `ui`, `docs`

## Terraform

- Match existing module versions (check file first)
- Local only: `terraform fmt`, `terraform validate`, `terraform plan -var-file=dev.tfvars`
- Never run: `terraform apply`, `terraform destroy`
- All Lambdas need `kms:Decrypt` policy

## Lambda (Python 3.12)

- Use cached AWS clients for container reuse
- Include CORS headers in `_response()`
- See existing handlers for patterns

## Lambda Testing

Use the project-root virtual environment. Never pip install globally.

```bash
# Setup (one time from project root)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# Run tests (always activate venv first)
source .venv/bin/activate
make test-unit                    # All unit tests
make test                         # All tests

# Run specific Lambda tests
cd lambda/analytics-api && python3 -m pytest tests/unit/ -v
```

## API Endpoints

```
GET  /analytics/stats/{domain}?from=DATE&to=DATE
GET  /analytics/pages/{domain}?from=DATE&to=DATE
GET  /analytics/referrers/{domain}?from=DATE&to=DATE
GET  /analytics/countries/{domain}?from=DATE&to=DATE
POST /auth/magic-link
POST /auth/verify
```
