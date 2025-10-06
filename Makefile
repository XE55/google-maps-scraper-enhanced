# Makefile for Google Maps Scraper Development

.PHONY: help build up down restart logs test test-watch shell db-shell redis-shell clean lint format

help: ## Show this help message
	@echo "Google Maps Scraper - Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker images
	docker compose -f docker-compose.dev.yml build

up: ## Start development environment
	docker compose -f docker-compose.dev.yml up -d
	@echo ""
	@echo "✅ Development environment started!"
	@echo "📍 API: http://localhost:8001"
	@echo "📊 API Docs: http://localhost:8001/docs"
	@echo "📈 Metrics: http://localhost:9090/metrics"
	@echo ""
	@echo "Run 'make logs' to see logs"
	@echo "Run 'make test' to run tests"

down: ## Stop development environment
	docker compose -f docker-compose.dev.yml down

restart: ## Restart development environment
	docker compose -f docker-compose.dev.yml restart

logs: ## Show logs (follow mode)
	docker compose -f docker-compose.dev.yml logs -f api-dev

logs-all: ## Show all container logs
	docker compose -f docker-compose.dev.yml logs -f

test: ## Run tests in Docker
	docker compose -f docker-compose.dev.yml run --rm test
	@echo ""
	@echo "✅ Tests completed! Check htmlcov/index.html for coverage report"

test-watch: ## Run tests in watch mode
	docker compose -f docker-compose.dev.yml run --rm test pytest-watch

test-auth: ## Run authentication tests only
	docker compose -f docker-compose.dev.yml run --rm test pytest tests/test_auth.py -v

test-coverage: ## Run tests with coverage report
	docker compose -f docker-compose.dev.yml run --rm test
	@echo "Opening coverage report..."
	@start htmlcov/index.html || open htmlcov/index.html || xdg-open htmlcov/index.html

shell: ## Open shell in API container
	docker compose -f docker-compose.dev.yml exec api-dev /bin/bash

shell-test: ## Open shell in test container
	docker compose -f docker-compose.dev.yml run --rm test /bin/bash

db-shell: ## Open PostgreSQL shell
	docker compose -f docker-compose.dev.yml exec postgres psql -U gmaps_user -d gmaps_scraper

redis-shell: ## Open Redis CLI
	docker compose -f docker-compose.dev.yml exec redis redis-cli

worker-up: ## Start Celery worker
	docker compose -f docker-compose.dev.yml --profile worker up -d worker-dev beat-dev

worker-logs: ## Show Celery worker logs
	docker compose -f docker-compose.dev.yml logs -f worker-dev

clean: ## Clean up containers, volumes, and cache
	docker compose -f docker-compose.dev.yml down -v
	rm -rf htmlcov/ .coverage coverage.xml .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

lint: ## Run linting
	docker compose -f docker-compose.dev.yml run --rm test ruff check gmaps_scraper_server/ tests/

format: ## Format code with Black
	docker compose -f docker-compose.dev.yml run --rm test black gmaps_scraper_server/ tests/

type-check: ## Run type checking with mypy
	docker compose -f docker-compose.dev.yml run --rm test mypy gmaps_scraper_server/

security: ## Run security checks
	docker compose -f docker-compose.dev.yml run --rm test bandit -r gmaps_scraper_server/
	docker compose -f docker-compose.dev.yml run --rm test safety check

install-playwright: ## Install Playwright browsers in container
	docker compose -f docker-compose.dev.yml exec api-dev playwright install --with-deps

rebuild: ## Rebuild and restart everything
	docker compose -f docker-compose.dev.yml down
	docker compose -f docker-compose.dev.yml build --no-cache
	docker compose -f docker-compose.dev.yml up -d

status: ## Show container status
	docker compose -f docker-compose.dev.yml ps

stats: ## Show container resource usage
	docker stats

env-check: ## Verify environment configuration
	@echo "Checking .env file..."
	@if [ -f .env ]; then \
		echo "✅ .env file exists"; \
	else \
		echo "❌ .env file not found. Copying from .env.example..."; \
		cp .env.example .env; \
		echo "✅ Created .env file. Please update with your values."; \
	fi

quick-start: env-check build up ## Quick start (check env, build, start)
	@echo ""
	@echo "🚀 Quick start complete!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Update .env file with your API keys"
	@echo "2. Run 'make test' to verify setup"
	@echo "3. Visit http://localhost:8001/docs to see API"
