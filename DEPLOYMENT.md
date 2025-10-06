# Production Deployment Guide

## Pre-Deployment Checklist

### ✅ Configuration
- [ ] `.env` file created and configured with production values
- [ ] `SECRET_KEY` generated (32+ characters)
- [ ] `ADMIN_PASSWORD` set to strong password
- [ ] `API_KEY_SALT` generated (32+ characters)
- [ ] `ENVIRONMENT=production`
- [ ] `DEBUG=false`
- [ ] `RELOAD=false`
- [ ] `DATABASE_ECHO=false`

### ✅ Database
- [ ] PostgreSQL installed or configured
- [ ] Database created: `gmaps_scraper`
- [ ] Database credentials configured in `.env`
- [ ] Database migrations run: `alembic upgrade head`
- [ ] Database backup strategy in place
- [ ] Connection pool configured (`DATABASE_POOL_SIZE=20`)

### ✅ Redis
- [ ] Redis installed or configured (if `REDIS_ENABLED=true`)
- [ ] Redis credentials configured
- [ ] Redis connection tested
- [ ] Cache TTL configured (`REDIS_CACHE_TTL=3600`)

### ✅ Security
- [ ] CORS origins configured for production domains
- [ ] Rate limits configured appropriately
- [ ] HTTPS/TLS certificate obtained
- [ ] Firewall rules configured
- [ ] API keys created for authorized users
- [ ] Proxy configuration (if using proxies)

### ✅ Monitoring
- [ ] Logging configured (JSON format for production)
- [ ] Log rotation enabled
- [ ] Health check endpoints tested
- [ ] Metrics collection verified
- [ ] Alerting configured (optional)

### ✅ Testing
- [ ] All 484 tests passing locally
- [ ] Integration tests run successfully
- [ ] Load testing completed
- [ ] Backup restore tested

---

## Production Deployment Methods

### Method 1: Docker Compose (Recommended)

#### Step 1: Prepare Environment

```bash
# Clone repository
git clone <your-repo-url>
cd google-maps-scraper-enhanced

# Create production .env
cp .env.example .env

# Generate secrets
python -c "import secrets; print(f'SECRET_KEY={secrets.token_hex(32)}')" >> .env
python -c "import secrets; print(f'API_KEY_SALT={secrets.token_hex(32)}')" >> .env

# Edit .env with production settings
nano .env
```

**Critical .env settings for production:**

```bash
# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json

# Server
HOST=0.0.0.0
PORT=8001
WORKERS=4
RELOAD=false

# Database
DATABASE_URL=postgresql://user:secure_password@postgres:5432/gmaps_scraper
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_ECHO=false

# Security
SECRET_KEY=<your-32+-char-secret>
API_KEY_SALT=<your-32+-char-salt>
ADMIN_PASSWORD=<your-secure-password>
CORS_ENABLED=true
CORS_ORIGINS=["https://yourdomain.com"]

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_PER_HOUR=100
RATE_LIMIT_PER_DAY=1000
```

#### Step 2: Deploy Services

```bash
# Build and start services
docker-compose up -d --build

# Verify services are running
docker-compose ps

# Should show:
# api        - Up
# postgres   - Up
# redis      - Up (if enabled)
```

#### Step 3: Run Database Migrations

```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Verify current version
docker-compose exec api alembic current
```

#### Step 4: Create Initial API Key

```bash
# Connect to database
docker-compose exec postgres psql -U user -d gmaps_scraper

# Create API key
INSERT INTO api_keys (key, name, is_active, created_at, requests_count)
VALUES (
  'your-production-api-key-here',
  'Production API Key',
  true,
  NOW(),
  0
);

# Exit
\q
```

#### Step 5: Verify Deployment

```bash
# Health check
curl http://localhost:8001/api/v1/health

# Readiness check
curl http://localhost:8001/api/v1/ready

# Test scraping with API key
curl -H "X-API-Key: your-production-api-key-here" \
  "http://localhost:8001/scrape-get?query=pizza&max_places=2"
```

#### Step 6: Configure Reverse Proxy (Nginx)

Create `/etc/nginx/sites-available/gmaps-scraper`:

```nginx
upstream gmaps_api {
    server localhost:8001;
}

server {
    listen 80;
    server_name yourdomain.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Request limits
    client_max_body_size 1M;
    client_body_timeout 60s;
    
    # Proxy settings
    location / {
        proxy_pass http://gmaps_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;  # Allow long scraping operations
    }
    
    # Health check endpoint (no auth required)
    location /api/v1/health {
        proxy_pass http://gmaps_api;
        access_log off;
    }
}
```

Enable and restart Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/gmaps-scraper /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

### Method 2: Standalone Docker Container

```bash
# Build production image
docker build --target production -t gmaps-scraper:latest .

# Create Docker network
docker network create gmaps-network

# Run PostgreSQL
docker run -d \
  --name gmaps-postgres \
  --network gmaps-network \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=gmaps_scraper \
  -v gmaps-postgres-data:/var/lib/postgresql/data \
  postgres:15

# Run Redis
docker run -d \
  --name gmaps-redis \
  --network gmaps-network \
  -v gmaps-redis-data:/data \
  redis:7

# Run API
docker run -d \
  --name gmaps-api \
  --network gmaps-network \
  -p 8001:8001 \
  -v $(pwd)/.env:/app/.env \
  -v gmaps-logs:/var/log/gmaps-scraper \
  --restart unless-stopped \
  gmaps-scraper:latest

# Run migrations
docker exec gmaps-api alembic upgrade head
```

---

## HTTPS/TLS Configuration

### Using Let's Encrypt with Certbot

```bash
# Install Certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal is configured automatically
# Test renewal
sudo certbot renew --dry-run
```

### Using Custom SSL Certificate

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_trusted_certificate /path/to/your/ca-bundle.crt;
    
    # Rest of configuration...
}
```

---

## Database Backup Strategy

### Automated Daily Backups

Create `/usr/local/bin/backup-gmaps-db.sh`:

```bash
#!/bin/bash

# Configuration
BACKUP_DIR="/backups/gmaps-scraper"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="gmaps_scraper_${TIMESTAMP}.sql.gz"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Perform backup
docker-compose exec -T postgres pg_dump -U user gmaps_scraper | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

# Verify backup
if [ -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
    echo "Backup successful: ${BACKUP_FILE}"
    
    # Delete old backups
    find "${BACKUP_DIR}" -name "gmaps_scraper_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
    echo "Cleaned up backups older than ${RETENTION_DAYS} days"
else
    echo "Backup failed!" >&2
    exit 1
fi
```

Make executable and add to cron:

```bash
chmod +x /usr/local/bin/backup-gmaps-db.sh

# Add to crontab (daily at 2 AM)
echo "0 2 * * * /usr/local/bin/backup-gmaps-db.sh >> /var/log/gmaps-backup.log 2>&1" | crontab -
```

### Restore from Backup

```bash
# List available backups
ls -lh /backups/gmaps-scraper/

# Restore specific backup
gunzip < /backups/gmaps-scraper/gmaps_scraper_20240115_020000.sql.gz | \
  docker-compose exec -T postgres psql -U user -d gmaps_scraper

# Or restore with Docker command
docker exec -i gmaps-postgres psql -U user -d gmaps_scraper < backup.sql
```

---

## Monitoring & Logging

### Centralized Logging

Configure log shipping to external service:

```bash
# Example: Shipping to Elasticsearch/Logstash

# Add to docker-compose.yml
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
        labels: "service=gmaps-scraper"
```

### Health Check Monitoring

Create monitoring script `/usr/local/bin/monitor-gmaps-health.sh`:

```bash
#!/bin/bash

HEALTH_URL="http://localhost:8001/api/v1/ready"
ALERT_EMAIL="admin@yourdomain.com"

# Check health endpoint
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${HEALTH_URL}")

if [ "${RESPONSE}" != "200" ]; then
    # Send alert
    echo "Google Maps Scraper is unhealthy (HTTP ${RESPONSE})" | \
      mail -s "ALERT: GMaps Scraper Health Check Failed" "${ALERT_EMAIL}"
    
    # Log error
    echo "$(date): Health check failed (HTTP ${RESPONSE})" >> /var/log/gmaps-health.log
fi
```

Add to cron (every 5 minutes):

```bash
*/5 * * * * /usr/local/bin/monitor-gmaps-health.sh
```

### Metrics Collection

Access metrics endpoint:

```bash
# Get metrics
curl http://localhost:8001/api/v1/metrics | jq

# Save metrics to file
curl -s http://localhost:8001/api/v1/metrics | jq > /var/log/gmaps-metrics-$(date +%Y%m%d_%H%M%S).json
```

---

## Scaling & Performance

### Horizontal Scaling

Scale API instances:

```bash
# Scale to 3 instances
docker-compose up -d --scale api=3

# With load balancer (Nginx upstream)
upstream gmaps_api {
    least_conn;
    server api1:8001;
    server api2:8001;
    server api3:8001;
}
```

### Database Optimization

```sql
-- Create indexes for performance
CREATE INDEX CONCURRENTLY idx_api_keys_active ON api_keys(is_active) WHERE is_active = true;
CREATE INDEX CONCURRENTLY idx_rate_limit_lookup ON rate_limit_tracking(api_key, endpoint, window_start, window_type);

-- Analyze tables
ANALYZE api_keys;
ANALYZE rate_limit_tracking;

-- Monitor slow queries
ALTER DATABASE gmaps_scraper SET log_min_duration_statement = 1000;
```

### Redis Optimization

```bash
# Configure Redis persistence
# Add to redis.conf or docker-compose.yml

command: >
  --save 60 1000
  --appendonly yes
  --maxmemory 256mb
  --maxmemory-policy allkeys-lru
```

---

## Security Best Practices

### 1. Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (redirects to HTTPS)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 2. Fail2Ban Protection

```bash
# Install fail2ban
sudo apt install fail2ban

# Create jail for API
sudo nano /etc/fail2ban/jail.d/gmaps-scraper.conf
```

```ini
[gmaps-scraper]
enabled = true
port = 80,443
filter = gmaps-scraper
logpath = /var/log/nginx/access.log
maxretry = 5
bantime = 3600
```

### 3. Regular Security Updates

```bash
# Create update script
cat > /usr/local/bin/update-gmaps-scraper.sh << 'EOF'
#!/bin/bash

# Pull latest changes
cd /opt/google-maps-scraper-enhanced
git pull origin main

# Backup database
/usr/local/bin/backup-gmaps-db.sh

# Rebuild and restart
docker-compose down
docker-compose up -d --build

# Run migrations
docker-compose exec api alembic upgrade head

# Verify health
sleep 10
curl -f http://localhost:8001/api/v1/health || exit 1
EOF

chmod +x /usr/local/bin/update-gmaps-scraper.sh
```

### 4. API Key Rotation

```sql
-- Disable old key
UPDATE api_keys SET is_active = false WHERE key = 'old-api-key';

-- Create new key
INSERT INTO api_keys (key, name, is_active, created_at, requests_count)
VALUES ('new-api-key', 'Production Key (Rotated)', true, NOW(), 0);
```

---

## Troubleshooting Production Issues

### Service Won't Start

```bash
# Check logs
docker-compose logs api

# Check configuration
docker-compose exec api python -m gmaps_scraper_server.config

# Verify environment variables
docker-compose exec api env | grep -E "SECRET_KEY|DATABASE_URL|REDIS_URL"
```

### High Memory Usage

```bash
# Check memory usage
docker stats

# Restart services
docker-compose restart api

# Adjust worker count in .env
WORKERS=2  # Reduce from 4
```

### Database Connection Issues

```bash
# Test database connection
docker-compose exec postgres psql -U user -d gmaps_scraper -c "SELECT 1"

# Check connection pool
docker-compose exec api python -c "
from gmaps_scraper_server.config import settings
print(f'Pool size: {settings.database_pool_size}')
print(f'Max overflow: {settings.database_max_overflow}')
"

# Monitor connections
docker-compose exec postgres psql -U user -d gmaps_scraper -c "
SELECT count(*) as connection_count, state 
FROM pg_stat_activity 
WHERE datname = 'gmaps_scraper' 
GROUP BY state;
"
```

### Slow API Responses

```bash
# Enable debug logging temporarily
docker-compose exec api bash -c "
export DEBUG=true
export LOG_LEVEL=DEBUG
supervisorctl restart api
"

# Check metrics
curl http://localhost:8001/api/v1/metrics | jq '.metrics.scraping'

# Monitor PostgreSQL slow queries
docker-compose exec postgres tail -f /var/log/postgresql/postgresql.log
```

---

## Rollback Procedure

If deployment fails, follow these steps:

```bash
# 1. Stop services
docker-compose down

# 2. Restore database from backup
gunzip < /backups/gmaps-scraper/gmaps_scraper_YYYYMMDD_HHMMSS.sql.gz | \
  docker-compose exec -T postgres psql -U user -d gmaps_scraper

# 3. Revert to previous Docker image
docker tag gmaps-scraper:previous gmaps-scraper:latest

# 4. Restart services
docker-compose up -d

# 5. Verify health
curl http://localhost:8001/api/v1/ready
```

---

## Maintenance Windows

### Before Maintenance

1. Notify users of maintenance window
2. Enable maintenance mode (return 503)
3. Backup database
4. Stop accepting new jobs

### During Maintenance

```bash
# Stop API service
docker-compose stop api

# Run migrations
docker-compose run api alembic upgrade head

# Perform updates
docker-compose pull
docker-compose build --no-cache

# Restart services
docker-compose up -d

# Verify health
sleep 10
curl -f http://localhost:8001/api/v1/ready
```

### After Maintenance

1. Monitor logs for errors
2. Check metrics for anomalies
3. Verify key functionality
4. Notify users maintenance is complete

---

## Support & Escalation

### Log Collection for Support

```bash
# Collect all relevant logs
mkdir -p /tmp/gmaps-support-$(date +%Y%m%d)
cd /tmp/gmaps-support-$(date +%Y%m%d)

# Docker logs
docker-compose logs --tail=1000 > docker-logs.txt

# Configuration (sanitized)
docker-compose exec api env | grep -v "SECRET\|PASSWORD\|KEY" > config.txt

# Health status
curl http://localhost:8001/api/v1/ready > health.json
curl http://localhost:8001/api/v1/metrics > metrics.json

# Database stats
docker-compose exec postgres psql -U user -d gmaps_scraper -c "\dt+" > db-stats.txt

# Create archive
cd ..
tar -czf gmaps-support-$(date +%Y%m%d).tar.gz gmaps-support-$(date +%Y%m%d)/
```

---

## Production Readiness Checklist

- [ ] All tests passing (484/484)
- [ ] Code coverage > 90% (currently 90.88%)
- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] HTTPS/TLS configured
- [ ] Reverse proxy configured
- [ ] Firewall rules applied
- [ ] Backup strategy implemented
- [ ] Monitoring enabled
- [ ] Logging configured
- [ ] Health checks passing
- [ ] Load testing completed
- [ ] Security review completed
- [ ] Documentation reviewed
- [ ] Rollback procedure tested
- [ ] Support contacts established

---

**Deployment completed successfully! 🚀**
