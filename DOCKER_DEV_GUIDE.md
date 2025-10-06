# Docker Development Setup

## 🚀 Quick Start (Windows PowerShell)

### 1. Load development commands
```powershell
. .\dev-commands.ps1
```

### 2. Start everything
```powershell
QuickStart
```

That's it! Your development environment is running with:
- ✅ API server with hot reload: http://localhost:8001
- ✅ API documentation: http://localhost:8001/docs
- ✅ PostgreSQL database
- ✅ Redis cache
- ✅ Full testing suite

## 📋 Available Commands

After loading `dev-commands.ps1`, you have these commands:

### Setup & Start
- `QuickStart` - Complete setup and start (recommended first time)
- `Check-Env` - Verify .env file exists
- `Build-Images` - Build Docker images
- `Start-Dev` - Start development environment
- `Stop-Dev` - Stop everything
- `Restart-Dev` - Restart services

### Testing
- `Test-All` - Run all tests with coverage
- `Test-Auth` - Run authentication tests only
- `Test-File "test_name.py"` - Run specific test file
- `Show-Coverage` - Open coverage report in browser

### Development
- `Show-Logs` - Watch API logs
- `Enter-Container` - Open shell in API container
- `Enter-Database` - Open PostgreSQL shell
- `Format-Code` - Format code with Black
- `Lint-Code` - Run ruff linter
- `Check-Security` - Run security scans

### Management
- `Show-Status` - Show container status
- `Rebuild-Dev` - Rebuild from scratch
- `Clean-Dev` - Clean up everything (containers, volumes, cache)

## 🧪 Running Tests

### Run all tests
```powershell
Test-All
```

### Run specific test file
```powershell
Test-File "test_auth.py"
```

### Run with coverage report
```powershell
Test-All
Show-Coverage  # Opens htmlcov/index.html in browser
```

### Run tests in watch mode (auto-rerun on file changes)
```powershell
docker compose -f docker-compose.dev.yml run --rm test ptw
```

## 🔧 Development Workflow

### 1. Start development environment
```powershell
Start-Dev
```

### 2. Make code changes
Files are automatically reloaded:
- Edit `gmaps_scraper_server/*.py`
- API server detects changes and reloads
- No need to restart!

### 3. Run tests
```powershell
Test-All
```

### 4. Check logs
```powershell
Show-Logs
```

### 5. Format and lint
```powershell
Format-Code
Lint-Code
```

## 🐛 Debugging

### Access API container shell
```powershell
Enter-Container
```

Then inside container:
```bash
# Run Python shell
python

# Run specific test
pytest tests/test_auth.py -v -s

# Check installed packages
pip list

# Test API endpoint manually
curl http://localhost:8001/health
```

### Access database
```powershell
Enter-Database
```

Then inside PostgreSQL:
```sql
-- List tables
\dt

-- Query API keys
SELECT * FROM api_keys;

-- Check connection
\conninfo
```

### Check Redis
```powershell
docker compose -f docker-compose.dev.yml exec redis redis-cli
```

Then inside Redis:
```
KEYS *
GET some_key
INFO
```

## 📊 Viewing Test Coverage

After running tests:
```powershell
Show-Coverage
```

Or manually open: `htmlcov/index.html`

Coverage requirements:
- Minimum: 70%
- Target: 80%+
- Critical modules: 90%+

## 🏗️ Architecture

```
docker-compose.dev.yml
├── postgres (5432)      # PostgreSQL 16
├── redis (6379)         # Redis 7
├── api-dev (8001, 9090) # FastAPI with hot reload
├── test                 # pytest runner (on-demand)
├── worker-dev           # Celery worker (profile: worker)
└── beat-dev             # Celery beat (profile: worker)
```

## 📝 Environment Variables

Copy `.env.example` to `.env` and update:

```env
# Essential for development
SECRET_KEY=your-dev-secret-key
API_KEY_SALT=your-dev-salt
ADMIN_PASSWORD=your-admin-password

# API Keys (optional for testing)
HUNTER_API_KEY=your-hunter-key
NEVERBOUNCE_API_KEY=your-neverbounce-key
GOOGLE_GEOCODING_API_KEY=your-google-key
```

## 🔄 Celery Workers (Background Jobs)

Start workers for async scraping:
```powershell
docker compose -f docker-compose.dev.yml --profile worker up -d
```

View worker logs:
```powershell
docker compose -f docker-compose.dev.yml logs -f worker-dev
```

## 🧹 Cleanup

### Stop and remove containers
```powershell
Stop-Dev
```

### Complete cleanup (including volumes)
```powershell
Clean-Dev
```

### Rebuild from scratch
```powershell
Rebuild-Dev
```

## 🐧 Linux/Mac Users

Use the Makefile instead:

```bash
make help           # Show all commands
make quick-start    # Complete setup
make up            # Start dev environment
make test          # Run tests
make logs          # Show logs
make down          # Stop everything
```

## 🚨 Troubleshooting

### Port already in use
```powershell
# Check what's using port 8001
netstat -ano | findstr :8001

# Kill the process
taskkill /PID <PID> /F

# Or change port in docker-compose.dev.yml
ports:
  - "8002:8001"  # Use 8002 instead
```

### Permission denied on volumes
```powershell
# Stop everything
Stop-Dev

# Remove volumes
docker volume prune

# Restart
Start-Dev
```

### Container won't start
```powershell
# Check logs
docker compose -f docker-compose.dev.yml logs api-dev

# Rebuild
Rebuild-Dev
```

### Tests fail with import errors
```powershell
# Rebuild test container
docker compose -f docker-compose.dev.yml build test

# Verify Python path
docker compose -f docker-compose.dev.yml run --rm test python -c "import sys; print('\n'.join(sys.path))"
```

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Playwright Python](https://playwright.dev/python/)

## ✅ Verification Checklist

After setup, verify everything works:

- [ ] `Start-Dev` completes without errors
- [ ] API docs load at http://localhost:8001/docs
- [ ] `Test-All` passes all tests
- [ ] `Show-Coverage` shows >70% coverage
- [ ] Hot reload works (edit file, see changes)
- [ ] Database connection works (`Enter-Database`)
- [ ] Redis connection works

## 🎯 Next Steps

1. **Complete authentication tests**: `Test-Auth`
2. **Implement input validation**: See `IMPLEMENTATION_CHECKLIST.md`
3. **Add anti-detection**: See `ANTI_DETECTION_GUIDE.md`
4. **Set up data quality**: See `DATA_QUALITY_ENRICHMENT.md`
5. **Add n8n endpoints**: See `MISSING_FEATURES_COMPLETE.md`

---

**Need help?** Check the main documentation files or open an issue.
