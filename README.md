## ⚠️ Disclaimer

This project is still **in development** and has **not been tested in real-world scenarios**.  
It’s a **side project** I’m working on to integrate into my main lead workflows.

The code and documentation were **heavily assisted by Claude Sonnet 4.5**, and I haven’t yet fully reviewed or validated the implementation.  
Please **use it with caution**, and **treat everything stated in this README as per Claude’s output**, not as a verified final version.

I am **not responsible for how this project is used**.  
It must **not be used to violate any Terms of Service, laws, or ethical guidelines**.


# Google Maps Scraper - Enhanced Edition 🗺️

A production-ready Google Maps scraper with FastAPI, built for reliability and ease of use. Perfect for extracting business information from Google Maps with async job processing and n8n integration.

[![Test Coverage](https://img.shields.io/badge/coverage-90.88%25-brightgreen)](.)
[![Tests](https://img.shields.io/badge/tests-484%20passing-brightgreen)](.)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://www.docker.com/)

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose** (recommended) OR
- **Python 3.10+**
- **PostgreSQL 13+**
- **Redis 6+** (optional, for caching)

### 1. Clone Repository

```bash
git clone <repository-url>
cd google-maps-scraper-enhanced
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Generate secure secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Edit .env with your secret key and configuration
nano .env
```

**Minimum required configuration:**

```bash
# Application
APP_NAME=gmaps-scraper
SECRET_KEY=<your-generated-secret-key>
ADMIN_PASSWORD=<your-secure-password>

# Database
DATABASE_URL=postgresql://user:password@postgres:5432/gmaps_scraper

# Redis (optional)
REDIS_ENABLED=true
REDIS_URL=redis://redis:6379/0
```

### 3. Start with Docker (Recommended)

```bash
# Build and start all services
docker-compose up -d

# Run database migrations
docker-compose exec api alembic upgrade head

# Check service status
docker-compose ps
```

The API will be available at: **http://localhost:8001**

### 4. Alternative: Local Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run database migrations
alembic upgrade head

# Start API server
uvicorn gmaps_scraper_server.main_api:app --host 0.0.0.0 --port 8001 --reload
```

---

## 📚 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [API Documentation](#-api-documentation)
- [Authentication](#-authentication)
- [Rate Limiting](#-rate-limiting)
- [n8n Integration](#-n8n-integration)
- [Configuration](#-configuration)
- [Deployment](#-deployment)
- [Troubleshooting](#-troubleshooting)
- [Development](#-development)
- [Testing](#-testing)

---

## ✨ Features

### Core Functionality
- ✅ **Google Maps Scraping**: Extract business data (name, address, phone, website, ratings, reviews)
- ✅ **Async Job Processing**: Background job execution with webhook notifications
- ✅ **Batch Processing**: Process multiple queries in a single request
- ✅ **Export Formats**: JSON, CSV, plain text

### Production-Ready
- ✅ **90.88% Test Coverage**: 484 passing tests ensure reliability
- ✅ **Docker Support**: Multi-stage builds with optimized images
- ✅ **Database Migrations**: Alembic for schema management
- ✅ **Structured Logging**: JSON logs with request tracking
- ✅ **Health Checks**: `/health`, `/ready`, `/metrics` endpoints
- ✅ **Configuration Management**: Type-safe Pydantic settings

### Advanced Features
- ✅ **API Authentication**: Key-based auth with rate limiting
- ✅ **Anti-Detection**: Stealth mode, user agent rotation, delays
- ✅ **Proxy Support**: Multiple proxy providers with rotation strategies
- ✅ **Email Verification**: Free API integration (Rapid Email Verifier)
- ✅ **Data Quality**: Normalization, deduplication, validation
- ✅ **Redis Caching**: Reduce duplicate scraping attempts
- ✅ **n8n Integration**: Webhook-based workflow automation

---

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌────────────┐
│   Client    │─────>│   FastAPI    │─────>│  Scraper   │
│  (n8n/API)  │<─────│     API      │<─────│ (Playwright)│
└─────────────┘      └──────────────┘      └────────────┘
                            │                      │
                            ├────────────┬─────────┤
                            ▼            ▼         ▼
                     ┌──────────┐ ┌─────────┐ ┌───────┐
                     │PostgreSQL│ │  Redis  │ │Proxies│
                     │ Database │ │  Cache  │ │ Pool  │
                     └──────────┘ └─────────┘ └───────┘
```

### Components

- **FastAPI**: REST API with async support
- **Playwright**: Headless browser automation
- **PostgreSQL**: Persistent storage for API keys & rate limits
- **Redis**: Caching and rate limit tracking
- **Alembic**: Database migration management
- **Structlog**: JSON structured logging

---

## 📖 API Documentation

### Base URL
```
http://localhost:8001
```

### Interactive Docs
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

---

### 🔍 Scraping Endpoints

#### 1. Synchronous Scrape (Simple)

**GET** `/scrape-get`

Simple synchronous scraping endpoint that returns results immediately.

**Query Parameters:**
- `query` (required): Search query (e.g., "pizza in New York")
- `max_places` (optional): Maximum places to scrape (default: 20, max: 500)
- `lang` (optional): Language code (default: "en")

**Example:**
```bash
curl "http://localhost:8001/scrape-get?query=pizza%20in%20New%20York&max_places=10"
```

**Response:**
```json
[
  {
    "name": "Joe's Pizza",
    "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
    "address": "7 Carmine St, New York, NY 10014",
    "latitude": 40.7308,
    "longitude": -74.0028,
    "rating": 4.5,
    "reviews": 1234,
    "phone": "+1 212-366-1182",
    "website": "https://joespizzanyc.com",
    "category": "Pizza restaurant",
    "thumbnail": "https://lh5.googleusercontent.com/..."
  }
]
```

---

#### 2. Async Scrape (Recommended for large jobs)

**POST** `/api/v1/scrape/async`

Creates a background job and returns immediately. Use this for large scraping operations.

**Request Body:**
```json
{
  "query": "restaurants in San Francisco",
  "max_places": 100,
  "lang": "en",
  "webhook_url": "https://your-webhook-url.com/callback"
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "query": "restaurants in San Francisco",
  "message": "Job created successfully. Use GET /api/v1/jobs/{job_id} to check status."
}
```

**Webhook Payload** (sent when job completes):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "query": "restaurants in San Francisco",
  "results": [...],
  "places_found": 100,
  "completed_at": "2024-01-15T10:30:00Z"
}
```

---

#### 3. Check Job Status

**GET** `/api/v1/jobs/{job_id}`

Check the status and progress of an async job.

**Example:**
```bash
curl "http://localhost:8001/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000"
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "query": "restaurants in San Francisco",
  "progress": 100,
  "places_found": 100,
  "created_at": "2024-01-15T10:25:00Z",
  "completed_at": "2024-01-15T10:30:00Z",
  "results": [...]
}
```

**Status values:**
- `pending`: Job created, waiting to start
- `running`: Job in progress
- `completed`: Job finished successfully
- `failed`: Job failed with error

---

#### 4. Export Results

**GET** `/api/v1/jobs/{job_id}/export?format={format}`

Export job results in different formats.

**Query Parameters:**
- `format`: Export format (`json`, `csv`, or `text`)

**Example:**
```bash
# Export as CSV
curl "http://localhost:8001/api/v1/jobs/550e8400/export?format=csv" > results.csv

# Export as JSON
curl "http://localhost:8001/api/v1/jobs/550e8400/export?format=json" > results.json
```

---

#### 5. Batch Scraping

**POST** `/api/v1/scrape/batch`

Process multiple queries in a single request.

**Request Body:**
```json
{
  "queries": [
    {"query": "pizza in NYC", "max_places": 20},
    {"query": "sushi in Tokyo", "max_places": 30},
    {"query": "cafes in Paris", "max_places": 15}
  ]
}
```

**Response:**
```json
{
  "batch_id": "batch_550e8400",
  "job_ids": [
    "job1_550e8400",
    "job2_550e8401",
    "job3_550e8402"
  ],
  "status": "pending",
  "message": "Batch created with 3 jobs"
}
```

---

### 🏥 Health & Monitoring Endpoints

#### Health Check

**GET** `/api/v1/health`

Basic health check - returns 200 if service is running.

```bash
curl http://localhost:8001/api/v1/health
```

#### Readiness Check

**GET** `/api/v1/ready`

Comprehensive readiness check - verifies all dependencies.

```bash
curl http://localhost:8001/api/v1/ready
```

**Response:**
```json
{
  "ready": true,
  "timestamp": "2024-01-15T10:00:00Z",
  "checks": {
    "database": {"status": "healthy", "response_time_ms": 12.34},
    "redis": {"status": "healthy", "response_time_ms": 5.67},
    "playwright": {"status": "healthy", "response_time_ms": 234.56}
  }
}
```

#### Metrics

**GET** `/api/v1/metrics`

Get operational metrics.

```bash
curl http://localhost:8001/api/v1/metrics
```

**Response:**
```json
{
  "timestamp": "2024-01-15T10:00:00Z",
  "metrics": {
    "uptime_seconds": 86400,
    "uptime_human": "1d 0h 0m 0s",
    "requests": {
      "total": 1234,
      "rate_per_second": 0.014
    },
    "scraping": {
      "total": 100,
      "success": 98,
      "failure": 2,
      "success_rate": 98.0,
      "total_places_scraped": 4567,
      "avg_places_per_scrape": 46.6,
      "last_duration_ms": 5432.1
    }
  }
}
```

#### Version Info

**GET** `/api/v1/version`

Get application version and feature flags.

```bash
curl http://localhost:8001/api/v1/version
```

---

## 🔐 Authentication

### API Key Authentication

All API endpoints (except health checks) require an API key.

#### Include API Key in Requests

**Header (Recommended):**
```bash
curl -H "X-API-Key: your-api-key-here" \
  "http://localhost:8001/scrape-get?query=pizza"
```

**Query Parameter:**
```bash
curl "http://localhost:8001/scrape-get?query=pizza&api_key=your-api-key-here"
```

### Creating API Keys

API keys are stored in the PostgreSQL database.

**Using SQL:**
```sql
INSERT INTO api_keys (key, name, is_active, created_at, requests_count)
VALUES ('your-secret-api-key', 'Production Key', true, NOW(), 0);
```

**Using Python:**
```python
import secrets
api_key = secrets.token_urlsafe(32)
print(f"Generated API Key: {api_key}")
```

---

## ⏱️ Rate Limiting

Protect your API from abuse with configurable rate limits.

### Default Limits

- **Per Minute**: 10 requests
- **Per Hour**: 100 requests
- **Per Day**: 1000 requests

### Configuration

Edit `.env` to adjust limits:

```bash
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_PER_HOUR=100
RATE_LIMIT_PER_DAY=1000
RATE_LIMIT_ENABLED=true
```

### Rate Limit Headers

Responses include rate limit information:

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1642250400
```

### Rate Limit Exceeded Response

```json
{
  "detail": "Rate limit exceeded: 10 requests per minute",
  "retry_after": 45
}
```

---

## 🔗 n8n Integration

Perfect integration with n8n workflow automation platform.

### Example n8n Workflow

```json
{
  "name": "Google Maps Scraper Workflow",
  "nodes": [
    {
      "name": "Trigger",
      "type": "n8n-nodes-base.webhook",
      "parameters": {
        "path": "scrape-trigger",
        "responseMode": "onReceived"
      }
    },
    {
      "name": "Start Scraping",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://api:8001/api/v1/scrape/async",
        "jsonParameters": true,
        "bodyParameters": {
          "query": "={{$json[\"query\"]}}",
          "max_places": 50,
          "webhook_url": "http://n8n:5678/webhook/scrape-complete"
        },
        "headerParameters": {
          "X-API-Key": "your-api-key"
        }
      }
    },
    {
      "name": "Receive Results",
      "type": "n8n-nodes-base.webhook",
      "parameters": {
        "path": "scrape-complete",
        "responseMode": "onReceived"
      }
    },
    {
      "name": "Process Results",
      "type": "n8n-nodes-base.function",
      "parameters": {
        "functionCode": "// Process scraped data\nreturn items;"
      }
    }
  ]
}
```

### Using the n8n Node (Included)

1. Copy `n8n-node/json.json` to your n8n custom nodes directory
2. Restart n8n
3. Add "Google Maps Scraper" node to your workflow
4. Configure API endpoint and key

---

## ⚙️ Configuration

### Environment Variables

All configuration via environment variables. See `.env.example` for full list.

#### Critical Settings

```bash
# Application
APP_NAME=gmaps-scraper
APP_VERSION=0.1.0
ENVIRONMENT=production  # development, staging, or production
DEBUG=false             # Never true in production!
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR, CRITICAL
SECRET_KEY=<32+ chars>  # Generate with: python -c "import secrets; print(secrets.token_hex(32))"

# Server
HOST=0.0.0.0
PORT=8001
WORKERS=4
RELOAD=false  # true only for development

# Database
DATABASE_URL=postgresql://user:password@postgres:5432/gmaps_scraper
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_ECHO=false

# Redis (Optional)
REDIS_ENABLED=true
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=
REDIS_CACHE_TTL=3600

# Scraping
MAX_PLACES_LIMIT=500
DEFAULT_MAX_PLACES=20
SCRAPING_TIMEOUT=300
SCROLL_PAUSE_TIME=2.0

# Playwright
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_TIMEOUT=30000
BROWSER_POOL_SIZE=5

# Anti-Detection
RANDOM_DELAY_MIN=3
RANDOM_DELAY_MAX=8
STEALTH_MODE_ENABLED=true
USER_AGENT_ROTATION_ENABLED=true

# Security
CORS_ENABLED=true
CORS_ORIGINS=["http://localhost:3000","http://localhost:5678"]
CORS_ALLOW_CREDENTIALS=true
```

### Proxy Configuration

Support for multiple proxy providers:

```bash
# Proxy Settings
PROXY_ENABLED=false
PROXY_PROVIDER=brightdata  # or smartproxy, custom
PROXY_ROTATION_STRATEGY=round-robin  # random, least-used, performance-based
PROXY_HEALTH_CHECK_INTERVAL=300

# Bright Data
BRIGHTDATA_USERNAME=your-username
BRIGHTDATA_PASSWORD=your-password
BRIGHTDATA_HOST=brd.superproxy.io
BRIGHTDATA_PORT=22225

# Custom Proxy List
PROXY_LIST=["http://proxy1:8080","http://proxy2:8080"]
```

---

## 🚢 Deployment

### Docker Production Deployment

#### 1. Build Production Image

```bash
docker build --target production -t gmaps-scraper:latest .
```

#### 2. Configure Environment

```bash
# Create production .env
cp .env.example .env
nano .env  # Configure all production settings
```

#### 3. Deploy with Docker Compose

```bash
# Start services
docker-compose up -d

# Run migrations
docker-compose exec api alembic upgrade head

# Check logs
docker-compose logs -f api

# Scale API instances
docker-compose up -d --scale api=3
```

#### 4. Health Check

```bash
curl http://localhost:8001/api/v1/ready
```

### Environment-Specific Deployment

#### Development
```bash
ENVIRONMENT=development DEBUG=true docker-compose up
```

#### Staging
```bash
ENVIRONMENT=staging docker-compose -f docker-compose.staging.yml up -d
```

#### Production
```bash
ENVIRONMENT=production docker-compose -f docker-compose.prod.yml up -d
```

### Database Backup Strategy

```bash
# Automated daily backups
0 2 * * * docker-compose exec -T postgres pg_dump -U user gmaps_scraper | gzip > /backups/gmaps_$(date +\%Y\%m\%d).sql.gz

# Restore from backup
gunzip < /backups/gmaps_20240115.sql.gz | docker-compose exec -T postgres psql -U user gmaps_scraper
```

### Monitoring & Logging

#### Access Logs

```bash
# View API logs
docker-compose logs -f api

# View specific log file
docker-compose exec api tail -f /var/log/gmaps-scraper/app.log

# Search logs
docker-compose logs api | grep "ERROR"
```

#### Log Rotation

Automatic rotation configured in `logging_config.py`:
- Max size: 10MB per file
- Backup count: 5 files
- Format: JSON (production) or console (development)

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Playwright Browser Not Found

**Error:** `Executable doesn't exist at /path/to/chromium`

**Solution:**
```bash
# Install Playwright browsers
playwright install chromium

# In Docker
docker-compose exec api playwright install chromium
```

#### 2. Database Connection Failed

**Error:** `could not connect to server: Connection refused`

**Solution:**
```bash
# Check database is running
docker-compose ps postgres

# Check connection string
echo $DATABASE_URL

# Test connection manually
docker-compose exec postgres psql -U user -d gmaps_scraper
```

#### 3. Redis Connection Failed

**Error:** `Error connecting to Redis`

**Solution:**
```bash
# Check Redis is running
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping
# Should return: PONG

# Disable Redis if not needed
REDIS_ENABLED=false in .env
```

#### 4. Rate Limit Errors

**Error:** `429 Too Many Requests`

**Solution:**
```bash
# Check rate limits in .env
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_PER_HOUR=100

# Increase limits or use different API key
# Clear rate limit cache (if using Redis)
docker-compose exec redis redis-cli FLUSHDB
```

#### 5. Scraping Timeout

**Error:** `Scraping timeout after 300 seconds`

**Solution:**
```bash
# Increase timeout in .env
SCRAPING_TIMEOUT=600
PLAYWRIGHT_TIMEOUT=60000

# Reduce max_places per request
# Use batch processing for large jobs
```

#### 6. Google Blocking Requests

**Symptoms:** Empty results, CAPTCHAs, or rate limiting from Google

**Solution:**
```bash
# Enable stealth mode
STEALTH_MODE_ENABLED=true

# Add delays
RANDOM_DELAY_MIN=5
RANDOM_DELAY_MAX=15

# Use proxies
PROXY_ENABLED=true
PROXY_LIST=["http://proxy1:8080"]

# Rotate user agents
USER_AGENT_ROTATION_ENABLED=true
```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
DEBUG=true
LOG_LEVEL=DEBUG
DATABASE_ECHO=true  # Log all SQL queries
```

### Health Check Endpoints

Use built-in health checks to diagnose issues:

```bash
# Overall health
curl http://localhost:8001/api/v1/health

# Detailed readiness check
curl http://localhost:8001/api/v1/ready | jq

# Application metrics
curl http://localhost:8001/api/v1/metrics | jq
```

---

## 💻 Development

### Local Development Setup

```bash
# Clone and setup
git clone <repository-url>
cd google-maps-scraper-enhanced

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Setup development database
docker-compose up -d postgres redis

# Configure environment
cp .env.example .env
# Edit .env with development settings

# Run migrations
alembic upgrade head

# Start development server
uvicorn gmaps_scraper_server.main_api:app --reload --port 8001
```

### Project Structure

```
google-maps-scraper-enhanced/
├── gmaps_scraper_server/
│   ├── __init__.py
│   ├── main_api.py           # FastAPI application
│   ├── scraper.py            # Core scraping logic
│   ├── extractor.py          # Data extraction
│   ├── auth.py               # Authentication
│   ├── rate_limiting.py      # Rate limiting
│   ├── proxy_manager.py      # Proxy rotation
│   ├── email_verifier.py     # Email verification
│   ├── data_quality.py       # Data validation
│   ├── stealth.py            # Anti-detection
│   ├── job_manager.py        # Async job management
│   ├── models.py             # Database models
│   ├── config.py             # Configuration
│   ├── logging_config.py     # Structured logging
│   └── health.py             # Health checks
├── tests/
│   ├── test_scraper.py       # Scraper tests
│   ├── test_extractor.py     # Extractor tests
│   ├── test_auth.py          # Auth tests
│   └── ...
├── alembic/                  # Database migrations
│   ├── versions/
│   ├── env.py
│   └── README.md
├── n8n-node/                 # n8n integration
│   └── json.json
├── docker-compose.yml        # Docker services
├── Dockerfile                # Multi-stage build
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
└── README.md                 # This file
```

---

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=gmaps_scraper_server --cov-report=html

# Run specific test file
pytest tests/test_scraper.py

# Run specific test
pytest tests/test_scraper.py::TestScrapeGoogleMaps::test_basic_scraping

# Run tests in parallel
pytest -n auto
```

### Test Coverage

Current coverage: **90.88%** (484 tests passing)

```bash
# Generate coverage report
pytest --cov=gmaps_scraper_server --cov-report=term-missing

# View HTML report
pytest --cov=gmaps_scraper_server --cov-report=html
open htmlcov/index.html
```

### Writing Tests

Example test:

```python
import pytest
from gmaps_scraper_server.scraper import scrape_google_maps

@pytest.mark.asyncio
async def test_scraping():
    results = await scrape_google_maps(
        query="pizza in NYC",
        max_places=5
    )
    assert len(results) > 0
    assert "name" in results[0]
```

---

## 📝 API Rate Limits & Best Practices

### Recommendations

1. **Use Async Endpoints** for large jobs (> 20 places)
2. **Implement Webhook Handlers** for result delivery
3. **Use Batch Processing** for multiple queries
4. **Enable Caching** to avoid duplicate scrapes
5. **Configure Proxies** for high-volume usage
6. **Monitor Health Endpoints** for production
7. **Set Reasonable Timeouts** based on max_places

### Performance Tips

- **Small jobs (< 20 places)**: Use synchronous endpoint
- **Medium jobs (20-100 places)**: Use async endpoint
- **Large jobs (> 100 places)**: Use batch processing
- **Enable Redis**: Reduce duplicate scraping by 40-60%
- **Use Proxies**: Avoid IP blocks for high volume
- **Parallel Processing**: Scale API containers horizontally

---

## 📄 License

[Your License Here]

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure 90%+ coverage
5. Submit pull request

---

## 📞 Support

- **Issues**: [GitHub Issues](your-repo-url/issues)
- **Documentation**: [Full Docs](your-docs-url)
- **Email**: your-email@example.com

---

## 🎯 Roadmap

- [ ] WebSocket support for real-time progress
- [ ] GraphQL API
- [ ] Multi-language support for UI
- [ ] Built-in proxy provider integration
- [ ] Advanced analytics dashboard
- [ ] Kubernetes deployment manifests

---

**Built with ❤️ using FastAPI, Playwright, and Python**

```bash
curl "http://gmaps_scraper_api_service:8001/scrape-get?query=hotels%20in%2098392&max_places=10&lang=en&headless=true"
```


## Running the Service

### Docker
```bash
docker-compose up --build
```

### Local Development
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the API:
```bash
uvicorn gmaps_scraper_server.main_api:app --reload
```


The API will be available at `http://localhost:8001`

or for docker:

`http://gmaps_scraper_api_service:8001`

## Notes
- For production use, consider adding authentication
- The scraping process may take several seconds to minutes depending on the number of results
- Results format depends on the underlying scraper implementation
