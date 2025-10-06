"""
Health check and monitoring endpoints for production readiness.
"""
import asyncio
import time
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

# Import dependencies
try:
    from gmaps_scraper_server.config import settings
    from gmaps_scraper_server.logging_config import get_logger
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False
    import logging
    get_logger = lambda name: logging.getLogger(name)

# Try to import database and redis clients
try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import NullPool
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False

try:
    import redis.asyncio as redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# Initialize router
router = APIRouter(prefix="/api/v1", tags=["health"])

# Global metrics storage
class Metrics:
    """Simple in-memory metrics storage"""
    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self.scraping_count = 0
        self.scraping_success = 0
        self.scraping_failure = 0
        self.total_places_scraped = 0
        self.last_scrape_duration_ms = 0.0
    
    def increment_requests(self):
        self.request_count += 1
    
    def increment_scraping(self, success: bool, places: int = 0, duration_ms: float = 0.0):
        self.scraping_count += 1
        if success:
            self.scraping_success += 1
            self.total_places_scraped += places
        else:
            self.scraping_failure += 1
        self.last_scrape_duration_ms = duration_ms
    
    def get_uptime_seconds(self) -> float:
        return time.time() - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        uptime = self.get_uptime_seconds()
        return {
            "uptime_seconds": round(uptime, 2),
            "uptime_human": self._format_uptime(uptime),
            "requests": {
                "total": self.request_count,
                "rate_per_second": round(self.request_count / uptime, 2) if uptime > 0 else 0,
            },
            "scraping": {
                "total": self.scraping_count,
                "success": self.scraping_success,
                "failure": self.scraping_failure,
                "success_rate": round(self.scraping_success / self.scraping_count * 100, 2) if self.scraping_count > 0 else 0,
                "total_places_scraped": self.total_places_scraped,
                "avg_places_per_scrape": round(self.total_places_scraped / self.scraping_success, 2) if self.scraping_success > 0 else 0,
                "last_duration_ms": round(self.last_scrape_duration_ms, 2),
            },
        }
    
    @staticmethod
    def _format_uptime(seconds: float) -> str:
        """Format uptime in human-readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m {secs}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"


# Global metrics instance
metrics = Metrics()


async def check_database() -> Dict[str, Any]:
    """Check database connectivity"""
    if not HAS_DATABASE or not HAS_CONFIG:
        return {
            "status": "disabled",
            "message": "Database check disabled (missing dependencies)"
        }
    
    try:
        # Create engine with minimal pooling for health check
        engine = create_engine(
            settings.database_url,
            poolclass=NullPool,
            connect_args={"connect_timeout": 5}
        )
        
        start = time.time()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        
        duration_ms = (time.time() - start) * 1000
        
        engine.dispose()
        
        return {
            "status": "healthy",
            "response_time_ms": round(duration_ms, 2),
        }
    except Exception as e:
        logger = get_logger("health")
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def check_redis() -> Dict[str, Any]:
    """Check Redis connectivity"""
    if not HAS_REDIS or not HAS_CONFIG:
        return {
            "status": "disabled",
            "message": "Redis check disabled (missing dependencies or not configured)"
        }
    
    if not settings.cache_enabled:
        return {
            "status": "disabled",
            "message": "Redis is disabled in configuration"
        }
    
    try:
        start = time.time()
        
        # Create Redis client
        client = redis.from_url(
            settings.redis_url,
            password=settings.redis_password,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
        )
        
        # Test connection with PING
        await client.ping()
        
        duration_ms = (time.time() - start) * 1000
        
        await client.close()
        
        return {
            "status": "healthy",
            "response_time_ms": round(duration_ms, 2),
        }
    except Exception as e:
        logger = get_logger("health")
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def check_playwright() -> Dict[str, Any]:
    """Check Playwright installation"""
    if not HAS_PLAYWRIGHT:
        return {
            "status": "disabled",
            "message": "Playwright not installed"
        }
    
    try:
        start = time.time()
        
        # Try to launch browser
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, timeout=5000)
            await browser.close()
        
        duration_ms = (time.time() - start) * 1000
        
        return {
            "status": "healthy",
            "response_time_ms": round(duration_ms, 2),
        }
    except Exception as e:
        logger = get_logger("health")
        logger.error(f"Playwright health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "hint": "Run 'playwright install chromium' to install browser"
        }


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    Returns 200 if service is running.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "gmaps-scraper",
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness check endpoint.
    Checks all critical dependencies (database, Redis, Playwright).
    Returns 200 only if all dependencies are healthy.
    """
    logger = get_logger("health")
    
    # Check all dependencies in parallel
    results = await asyncio.gather(
        check_database(),
        check_redis(),
        check_playwright(),
        return_exceptions=True,
    )
    
    db_check, redis_check, playwright_check = results
    
    # Determine overall status
    checks = {
        "database": db_check if not isinstance(db_check, Exception) else {"status": "error", "error": str(db_check)},
        "redis": redis_check if not isinstance(redis_check, Exception) else {"status": "error", "error": str(redis_check)},
        "playwright": playwright_check if not isinstance(playwright_check, Exception) else {"status": "error", "error": str(playwright_check)},
    }
    
    # Check if any critical component is unhealthy
    is_ready = all(
        check.get("status") in ["healthy", "disabled"]
        for check in checks.values()
    )
    
    status_code = 200 if is_ready else 503
    
    response = {
        "ready": is_ready,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
    }
    
    if not is_ready:
        logger.warning("Readiness check failed", checks=checks)
    
    return JSONResponse(content=response, status_code=status_code)


@router.get("/metrics")
async def get_metrics():
    """
    Get application metrics.
    Returns basic operational metrics like uptime, request count, scraping stats.
    """
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics.to_dict(),
    }


@router.get("/version")
async def get_version():
    """
    Get application version and configuration info.
    """
    version_info = {
        "service": "gmaps-scraper",
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    if HAS_CONFIG:
        version_info.update({
            "environment": settings.environment,
            "debug": settings.debug,
            "features": {
                "redis_caching": settings.cache_enabled,
                "rate_limiting": settings.rate_limit_enabled,
                "email_verification": settings.email_verification_enabled,
                "proxy_rotation": bool(settings.proxy_list),
                "stealth_mode": settings.stealth_mode_enabled,
            }
        })
    
    return version_info


# Export metrics instance for use in other modules
__all__ = ["router", "metrics"]
