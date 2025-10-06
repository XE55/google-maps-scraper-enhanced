# 🐳 Docker Dev Commands - Quick Reference

## Start/Stop
```powershell
# Build images
docker compose -f docker-compose.dev.yml build

# Start all services
docker compose -f docker-compose.dev.yml up -d

# Stop all services
docker compose -f docker-compose.dev.yml down

# Restart services
docker compose -f docker-compose.dev.yml restart
```

## Testing
```powershell
# Run all tests
docker compose -f docker-compose.dev.yml run --rm test

# Run specific test file
docker compose -f docker-compose.dev.yml run --rm test pytest tests/test_auth.py -v

# Run tests with output
docker compose -f docker-compose.dev.yml run --rm test pytest tests/test_auth.py -v -s

# Run single test function
docker compose -f docker-compose.dev.yml run --rm test pytest tests/test_auth.py::TestAPIKeyManager::test_generate_api_key_format -v
```

## Logs
```powershell
# Follow API logs
docker compose -f docker-compose.dev.yml logs -f api-dev

# View all logs
docker compose -f docker-compose.dev.yml logs -f

# Last 100 lines
docker compose -f docker-compose.dev.yml logs --tail=100 api-dev
```

## Shell Access
```powershell
# API container shell
docker compose -f docker-compose.dev.yml exec api-dev /bin/bash

# Database shell
docker compose -f docker-compose.dev.yml exec postgres psql -U gmaps_user -d gmaps_scraper

# Redis CLI
docker compose -f docker-compose.dev.yml exec redis redis-cli
```

## Code Quality
```powershell
# Format code
docker compose -f docker-compose.dev.yml run --rm test black gmaps_scraper_server/ tests/

# Lint
docker compose -f docker-compose.dev.yml run --rm test ruff check gmaps_scraper_server/

# Type check
docker compose -f docker-compose.dev.yml run --rm test mypy gmaps_scraper_server/

# Security scan
docker compose -f docker-compose.dev.yml run --rm test bandit -r gmaps_scraper_server/
```

## Status & Debug
```powershell
# Container status
docker compose -f docker-compose.dev.yml ps

# Resource usage
docker stats

# Container logs (last error)
docker compose -f docker-compose.dev.yml logs --tail=50 api-dev | Select-String "error"
```

## Cleanup
```powershell
# Stop and remove containers
docker compose -f docker-compose.dev.yml down

# Stop and remove containers + volumes (⚠️  deletes database data)
docker compose -f docker-compose.dev.yml down -v

# Clean up test artifacts
Remove-Item -Recurse -Force htmlcov, .coverage, .pytest_cache -ErrorAction SilentlyContinue
```

## Quick Workflows

### First Time Setup
```powershell
docker compose -f docker-compose.dev.yml build
docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml run --rm test
```

### After Code Changes
```powershell
# Services auto-reload, just run tests
docker compose -f docker-compose.dev.yml run --rm test
```

### Debug Test Failure
```powershell
# Run specific test with output
docker compose -f docker-compose.dev.yml run --rm test pytest tests/test_auth.py -v -s

# Or enter container and debug
docker compose -f docker-compose.dev.yml run --rm test /bin/bash
pytest tests/test_auth.py -v -s --pdb
```

### Fresh Start
```powershell
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml build --no-cache
docker compose -f docker-compose.dev.yml up -d
```

## URLs
- API: http://localhost:8001
- API Docs: http://localhost:8001/docs
- Metrics: http://localhost:9090/metrics
- PostgreSQL: localhost:5432 (user: gmaps_user, pass: dev_password_123)
- Redis: localhost:6379
