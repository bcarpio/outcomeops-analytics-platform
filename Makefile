.PHONY: help deps fmt fmt-check tf-init validate plan-dev plan-prd test test-unit test-integration test-coverage test-ci lint ui-install ui-dev ui-build ui-build-dev ui-lint ui-typecheck ui-test ui-test-watch ui-test-coverage clean all

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Python dependencies
deps: ## Install Python dev dependencies
	@echo "Installing Python dependencies..."
	@pip install -r requirements-dev.txt

# Terraform targets
fmt: ## Format terraform code
	@echo "Formatting Terraform code..."
	@cd terraform && terraform fmt -recursive

fmt-check: ## Check terraform formatting (CI)
	@echo "Checking Terraform formatting..."
	@cd terraform && terraform fmt -check -recursive

tf-init: ## Initialize Terraform (no backend)
	@echo "Initializing Terraform..."
	@cd terraform && terraform init -input=false -backend=false

validate: ## Validate Terraform configuration
	@echo "Validating Terraform..."
	@cd terraform && terraform init -backend=false > /dev/null && terraform validate

plan-dev: ## Run terraform plan for dev environment
	@echo "Planning Terraform (dev)..."
	@cd terraform && terraform plan -var-file=dev.tfvars

plan-prd: ## Run terraform plan for prd environment
	@echo "Planning Terraform (prd)..."
	@cd terraform && terraform plan -var-file=prd.tfvars

# Lambda targets
test: ## Run all Lambda tests
	@echo "Running all Lambda tests..."
	@for dir in lambda/*/; do \
		if [ -f "$$dir/requirements.txt" ]; then \
			echo "Testing $$dir..."; \
			cd "$$dir" && \
			if [ -d "tests" ]; then \
				python3 -m pytest tests/ -v || exit 1; \
			else \
				echo "No tests directory found in $$dir"; \
			fi; \
			cd ../..; \
		fi; \
	done

test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	@for dir in lambda/*/; do \
		if [ -f "$$dir/requirements.txt" ] && [ -d "$$dir/tests/unit" ]; then \
			echo "Testing $$dir..."; \
			cd "$$dir" && python3 -m pytest tests/unit/ -v || exit 1; \
			cd ../..; \
		fi; \
	done

test-integration: ## Run integration tests only
	@echo "Running integration tests..."
	@for dir in lambda/*/; do \
		if [ -f "$$dir/requirements.txt" ] && [ -d "$$dir/tests/integration" ]; then \
			echo "Testing $$dir..."; \
			cd "$$dir" && python3 -m pytest tests/integration/ -v || exit 1; \
			cd ../..; \
		fi; \
	done

test-coverage: ## Run tests with coverage
	@echo "Running tests with coverage..."
	@for dir in lambda/*/; do \
		if [ -f "$$dir/requirements.txt" ] && [ -d "$$dir/tests" ]; then \
			echo "Testing $$dir with coverage..."; \
			cd "$$dir" && \
			python3 -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html || exit 1; \
			cd ../..; \
		fi; \
	done

test-ci: ## Run tests with coverage XML output (CI)
	@echo "Running tests for CI..."
	@rm -f .coverage .coverage.* coverage.xml junit.xml junit-*.xml
	@cd lambda/analytics-api && COVERAGE_FILE=$(CURDIR)/.coverage.api \
		python3 -m pytest tests/unit/ -v --cov=. --cov-report= --junitxml=$(CURDIR)/junit-api.xml
	@cd lambda/analytics-auth && COVERAGE_FILE=$(CURDIR)/.coverage.auth \
		python3 -m pytest tests/unit/ -v --cov=. --cov-report= --junitxml=$(CURDIR)/junit-auth.xml
	@cd lambda/log-parser && COVERAGE_FILE=$(CURDIR)/.coverage.parser \
		python3 -m pytest tests/unit/ -v --cov=. --cov-report= --junitxml=$(CURDIR)/junit-parser.xml
	@python3 -m coverage combine
	@python3 -m coverage xml -o coverage.xml
	@python3 -c "import xml.etree.ElementTree as ET; \
		root = ET.Element('testsuites'); \
		[root.append(ET.parse(f).getroot()) for f in ['junit-api.xml', 'junit-auth.xml', 'junit-parser.xml']]; \
		ET.ElementTree(root).write('junit.xml')"
	@rm -f junit-api.xml junit-auth.xml junit-parser.xml .coverage.*

lint: ## Lint Python code with ruff
	@echo "Linting Python code..."
	@for dir in lambda/*/; do \
		if [ -f "$$dir/requirements.txt" ]; then \
			echo "Linting $$dir..."; \
			ruff check "$$dir" || exit 1; \
		fi; \
	done

# UI targets
ui-install: ## Install UI dependencies
	@echo "Installing UI dependencies..."
	@cd ui && pnpm install

ui-dev: ## Run UI development server
	@echo "Starting UI development server..."
	@cd ui && pnpm run dev

ui-build: ## Build UI for production
	@echo "Building UI..."
	@cd ui && pnpm run build:prd

ui-build-dev: ## Build UI for development
	@echo "Building UI (dev)..."
	@cd ui && pnpm run build:dev

ui-lint: ## Lint UI code
	@echo "Linting UI code..."
	@cd ui && pnpm run lint

ui-typecheck: ## Type check UI code
	@echo "Type checking UI code..."
	@cd ui && pnpm run typecheck

ui-test: ## Run UI tests
	@echo "Running UI tests..."
	@cd ui && pnpm test

ui-test-watch: ## Run UI tests in watch mode
	@echo "Running UI tests in watch mode..."
	@cd ui && pnpm run test:watch

ui-test-coverage: ## Run UI tests with coverage
	@echo "Running UI tests with coverage..."
	@cd ui && pnpm run test:coverage

# Clean targets
clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@rm -rf terraform/.terraform/lambda-packages 2>/dev/null || true
	@find lambda -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf ui/dist 2>/dev/null || true
	@rm -rf ui/dist-server 2>/dev/null || true
	@echo "Clean complete"

all: fmt validate lint test ## Run fmt, validate, lint, and all tests
	@echo "All checks passed!"
