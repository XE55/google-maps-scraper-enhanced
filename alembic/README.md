# Database Migrations

This directory contains Alembic database migrations for the Google Maps Scraper.

## Initial Setup

1. **Install dependencies** (if not already done):
   ```bash
   pip install alembic sqlalchemy asyncpg psycopg2-binary
   ```

2. **Configure database URL** in `.env`:
   ```bash
   DATABASE_URL=postgresql://user:password@localhost:5432/gmaps_scraper
   ```

3. **Run migrations**:
   ```bash
   # Apply all migrations
   alembic upgrade head
   
   # Or run in Docker
   docker-compose exec api alembic upgrade head
   ```

## Creating New Migrations

### Auto-generate migration from model changes:
```bash
alembic revision --autogenerate -m "description of changes"
```

### Create empty migration:
```bash
alembic revision -m "description of changes"
```

### Review and edit the generated migration file in `alembic/versions/`

### Apply the migration:
```bash
alembic upgrade head
```

## Migration Commands

### Upgrade database to latest version:
```bash
alembic upgrade head
```

### Upgrade by one version:
```bash
alembic upgrade +1
```

### Downgrade by one version:
```bash
alembic downgrade -1
```

### Downgrade to specific revision:
```bash
alembic downgrade <revision_id>
```

### Show current version:
```bash
alembic current
```

### Show migration history:
```bash
alembic history --verbose
```

### Show pending migrations:
```bash
alembic current
alembic heads
```

## Migration Files

### 001_initial.py
Creates the initial database schema:
- **api_keys** table: Stores API keys for authentication
  - `id`: Primary key
  - `key`: Unique API key (64 chars)
  - `name`: Friendly name for the key
  - `is_active`: Whether the key is active
  - `created_at`: Creation timestamp
  - `last_used_at`: Last usage timestamp
  - `requests_count`: Total requests made with this key
  
- **rate_limit_tracking** table: Tracks rate limits per API key
  - `id`: Primary key
  - `api_key`: Foreign key to API key
  - `endpoint`: API endpoint path
  - `window_start`: Start of rate limit window
  - `window_type`: Type of window (minute/hour/day)
  - `request_count`: Requests in current window
  - `last_request_at`: Last request timestamp

## Indexes

Indexes are created for optimal query performance:
- `api_keys.key` (unique): Fast API key lookups
- `api_keys.is_active`: Filter active keys
- `rate_limit_tracking.api_key`: Join with api_keys
- `rate_limit_tracking (api_key, endpoint, window_start, window_type)`: Composite index for rate limit checks

## Docker Usage

When using Docker Compose:

```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Check current version
docker-compose exec api alembic current

# Rollback one version
docker-compose exec api alembic downgrade -1
```

## Troubleshooting

### "Target database is not up to date"
Run: `alembic upgrade head`

### "Can't locate revision identified by"
Check migration file names and revision IDs match.

### Database connection errors
Verify `DATABASE_URL` in `.env` is correct and database is running.

### Permission errors
Ensure database user has CREATE TABLE permissions.

## Production Deployment

1. **Always backup database before migrations**:
   ```bash
   pg_dump -U user -d gmaps_scraper > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Test migrations in staging first**

3. **Run migrations during maintenance window**:
   ```bash
   # Stop API service
   docker-compose stop api
   
   # Run migration
   docker-compose run api alembic upgrade head
   
   # Start API service
   docker-compose start api
   ```

4. **Verify migration success**:
   ```bash
   docker-compose exec api alembic current
   ```

## Rollback Strategy

If a migration causes issues:

```bash
# Rollback to previous version
docker-compose exec api alembic downgrade -1

# Or rollback to specific version
docker-compose exec api alembic downgrade <revision_id>

# Restore from backup if needed
psql -U user -d gmaps_scraper < backup_file.sql
```
