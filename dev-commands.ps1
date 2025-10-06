# PowerShell Development Scripts for Windows
# Run these commands to manage the development environment

# Quick Start
function Start-Dev {
    Write-Host "🚀 Starting development environment..." -ForegroundColor Green
    docker compose -f docker-compose.dev.yml up -d
    Write-Host ""
    Write-Host "✅ Development environment started!" -ForegroundColor Green
    Write-Host "📍 API: http://localhost:8001" -ForegroundColor Cyan
    Write-Host "📊 API Docs: http://localhost:8001/docs" -ForegroundColor Cyan
    Write-Host "📈 Metrics: http://localhost:9090/metrics" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Run 'Show-Logs' to see logs" -ForegroundColor Yellow
    Write-Host "Run 'Test-All' to run tests" -ForegroundColor Yellow
}

# Stop environment
function Stop-Dev {
    Write-Host "🛑 Stopping development environment..." -ForegroundColor Yellow
    docker compose -f docker-compose.dev.yml down
}

# Restart
function Restart-Dev {
    Write-Host "🔄 Restarting development environment..." -ForegroundColor Yellow
    docker compose -f docker-compose.dev.yml restart
}

# Show logs
function Show-Logs {
    docker compose -f docker-compose.dev.yml logs -f api-dev
}

# Run all tests
function Test-All {
    Write-Host "🧪 Running tests..." -ForegroundColor Cyan
    docker compose -f docker-compose.dev.yml run --rm test
    Write-Host ""
    Write-Host "✅ Tests completed! Check htmlcov/index.html for coverage report" -ForegroundColor Green
}

# Run specific test file
function Test-File {
    param([string]$File)
    Write-Host "🧪 Running tests in $File..." -ForegroundColor Cyan
    docker compose -f docker-compose.dev.yml run --rm test pytest "tests/$File" -v
}

# Run authentication tests
function Test-Auth {
    Test-File "test_auth.py"
}

# Open coverage report
function Show-Coverage {
    if (Test-Path "htmlcov/index.html") {
        Start-Process "htmlcov/index.html"
    } else {
        Write-Host "❌ Coverage report not found. Run Test-All first." -ForegroundColor Red
    }
}

# Open shell in container
function Enter-Container {
    docker compose -f docker-compose.dev.yml exec api-dev /bin/bash
}

# Open database shell
function Enter-Database {
    docker compose -f docker-compose.dev.yml exec postgres psql -U gmaps_user -d gmaps_scraper
}

# Clean everything
function Clean-Dev {
    Write-Host "🧹 Cleaning up..." -ForegroundColor Yellow
    docker compose -f docker-compose.dev.yml down -v
    Remove-Item -Recurse -Force htmlcov, .coverage, coverage.xml, .pytest_cache -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -Directory __pycache__ | Remove-Item -Recurse -Force
    Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force
    Write-Host "✅ Cleanup complete!" -ForegroundColor Green
}

# Rebuild from scratch
function Rebuild-Dev {
    Write-Host "🔨 Rebuilding from scratch..." -ForegroundColor Yellow
    docker compose -f docker-compose.dev.yml down
    docker compose -f docker-compose.dev.yml build --no-cache
    docker compose -f docker-compose.dev.yml up -d
    Write-Host "✅ Rebuild complete!" -ForegroundColor Green
}

# Show container status
function Show-Status {
    docker compose -f docker-compose.dev.yml ps
}

# Format code
function Format-Code {
    Write-Host "💅 Formatting code with Black..." -ForegroundColor Cyan
    docker compose -f docker-compose.dev.yml run --rm test black gmaps_scraper_server/ tests/
}

# Run linting
function Lint-Code {
    Write-Host "🔍 Running linters..." -ForegroundColor Cyan
    docker compose -f docker-compose.dev.yml run --rm test ruff check gmaps_scraper_server/ tests/
}

# Security check
function Check-Security {
    Write-Host "🔒 Running security checks..." -ForegroundColor Cyan
    docker compose -f docker-compose.dev.yml run --rm test bandit -r gmaps_scraper_server/
}

# Check .env file
function Check-Env {
    if (Test-Path ".env") {
        Write-Host "✅ .env file exists" -ForegroundColor Green
    } else {
        Write-Host "❌ .env file not found. Creating from .env.example..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
        Write-Host "✅ Created .env file. Please update with your values." -ForegroundColor Green
    }
}

# Build images
function Build-Images {
    Write-Host "🏗️  Building Docker images..." -ForegroundColor Cyan
    docker compose -f docker-compose.dev.yml build
    Write-Host "✅ Build complete!" -ForegroundColor Green
}

# Quick start everything
function QuickStart {
    Write-Host "🚀 Quick Start Sequence" -ForegroundColor Magenta
    Write-Host "========================" -ForegroundColor Magenta
    Check-Env
    Build-Images
    Start-Dev
    Write-Host ""
    Write-Host "🎉 Setup complete! Next steps:" -ForegroundColor Green
    Write-Host "1. Update .env file with your API keys" -ForegroundColor Yellow
    Write-Host "2. Run Test-All to verify setup" -ForegroundColor Yellow
    Write-Host "3. Visit http://localhost:8001/docs to see API" -ForegroundColor Yellow
}

# Help
function Show-Help {
    Write-Host ""
    Write-Host "Google Maps Scraper - Development Commands" -ForegroundColor Magenta
    Write-Host "==========================================" -ForegroundColor Magenta
    Write-Host ""
    Write-Host "Setup & Start:" -ForegroundColor Cyan
    Write-Host "  QuickStart        - Complete setup and start" -ForegroundColor White
    Write-Host "  Check-Env         - Verify .env file" -ForegroundColor White
    Write-Host "  Build-Images      - Build Docker images" -ForegroundColor White
    Write-Host "  Start-Dev         - Start development environment" -ForegroundColor White
    Write-Host ""
    Write-Host "Testing:" -ForegroundColor Cyan
    Write-Host "  Test-All          - Run all tests with coverage" -ForegroundColor White
    Write-Host "  Test-Auth         - Run authentication tests only" -ForegroundColor White
    Write-Host "  Test-File <name>  - Run specific test file" -ForegroundColor White
    Write-Host "  Show-Coverage     - Open coverage report in browser" -ForegroundColor White
    Write-Host ""
    Write-Host "Development:" -ForegroundColor Cyan
    Write-Host "  Show-Logs         - Show API container logs" -ForegroundColor White
    Write-Host "  Enter-Container   - Open shell in API container" -ForegroundColor White
    Write-Host "  Enter-Database    - Open PostgreSQL shell" -ForegroundColor White
    Write-Host "  Format-Code       - Format code with Black" -ForegroundColor White
    Write-Host "  Lint-Code         - Run linting checks" -ForegroundColor White
    Write-Host "  Check-Security    - Run security scans" -ForegroundColor White
    Write-Host ""
    Write-Host "Management:" -ForegroundColor Cyan
    Write-Host "  Stop-Dev          - Stop environment" -ForegroundColor White
    Write-Host "  Restart-Dev       - Restart environment" -ForegroundColor White
    Write-Host "  Rebuild-Dev       - Rebuild from scratch" -ForegroundColor White
    Write-Host "  Show-Status       - Show container status" -ForegroundColor White
    Write-Host "  Clean-Dev         - Clean up everything" -ForegroundColor White
    Write-Host ""
}

# Export functions
Export-ModuleMember -Function *

# Show help on import
Show-Help
