# Simple test runner
Write-Host "🧪 Running Tests..." -ForegroundColor Cyan
Write-Host ""

docker compose -f docker-compose.dev.yml run --rm test

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ All tests passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Coverage report generated in htmlcov/" -ForegroundColor Cyan
    Write-Host "   Open htmlcov/index.html to view" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "❌ Tests failed!" -ForegroundColor Red
}
