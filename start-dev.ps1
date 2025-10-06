# Quick Start Script - Checks prerequisites and starts development
Write-Host "🚀 Google Maps Scraper - Setup Check" -ForegroundColor Magenta
Write-Host "=====================================" -ForegroundColor Magenta
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker..." -ForegroundColor Cyan
try {
    $dockerVersion = docker version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker not responding"
    }
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker Desktop is not running!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please start Docker Desktop and try again." -ForegroundColor Yellow
    Write-Host "After Docker starts, run this script again." -ForegroundColor Yellow
    exit 1
}

# Check if .env exists
Write-Host ""
Write-Host "Checking .env file..." -ForegroundColor Cyan
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  .env file not found. Creating from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✅ Created .env file" -ForegroundColor Green
    Write-Host ""
    Write-Host "📝 Please update .env with your API keys before running tests" -ForegroundColor Yellow
} else {
    Write-Host "✅ .env file exists" -ForegroundColor Green
}

# Build images
Write-Host ""
Write-Host "Building Docker images..." -ForegroundColor Cyan
Write-Host "(This may take 5-10 minutes on first run)" -ForegroundColor Yellow
docker compose -f docker-compose.dev.yml build
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Build complete" -ForegroundColor Green

# Start services
Write-Host ""
Write-Host "Starting services..." -ForegroundColor Cyan
docker compose -f docker-compose.dev.yml up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to start services!" -ForegroundColor Red
    exit 1
}

# Wait for services to be healthy
Write-Host ""
Write-Host "Waiting for services to be ready..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

# Check service status
Write-Host ""
Write-Host "Service Status:" -ForegroundColor Cyan
docker compose -f docker-compose.dev.yml ps

Write-Host ""
Write-Host "=====================================" -ForegroundColor Magenta
Write-Host "✅ Development environment is ready!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "🌐 API Server:      http://localhost:8001" -ForegroundColor Cyan
Write-Host "📚 API Docs:        http://localhost:8001/docs" -ForegroundColor Cyan
Write-Host "📊 Metrics:         http://localhost:9090/metrics" -ForegroundColor Cyan
Write-Host "🗄️  PostgreSQL:      localhost:5432 (user: gmaps_user, pass: dev_password_123)" -ForegroundColor Cyan
Write-Host "🔴 Redis:           localhost:6379" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Next Commands:" -ForegroundColor Yellow
Write-Host "  docker compose -f docker-compose.dev.yml logs -f api-dev    # Show logs" -ForegroundColor White
Write-Host "  docker compose -f docker-compose.dev.yml run --rm test      # Run tests" -ForegroundColor White
Write-Host "  docker compose -f docker-compose.dev.yml exec api-dev bash  # Open shell" -ForegroundColor White
Write-Host "  docker compose -f docker-compose.dev.yml down               # Stop everything" -ForegroundColor White
Write-Host ""
