"""
Rate limiting middleware using slowapi.

Provides multiple rate limit tiers:
- Per-IP limits: Prevents abuse from single source
- Per-API-key limits: Enforces plan limits
- Global limits: Protects server resources

Security features:
- 429 Too Many Requests responses
- Retry-After headers
- Configurable limits via environment variables
"""

import os
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse


def get_api_key_from_request(request: Request) -> str:
    """
    Extract API key from request for rate limiting.
    
    Checks:
    1. X-API-Key header
    2. Authorization header (Bearer token)
    3. Query parameter (api_key)
    4. Falls back to IP address if no key
    
    Returns:
        API key or IP address as identifier
    """
    # Check X-API-Key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"apikey:{api_key}"
    
    # Check Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        return f"apikey:{token}"
    
    # Check query parameter
    api_key = request.query_params.get("api_key")
    if api_key:
        return f"apikey:{api_key}"
    
    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


def custom_rate_limit_key(request: Request) -> str:
    """
    Custom key function for rate limiting.
    
    Combines API key and endpoint to allow different limits per endpoint.
    """
    identifier = get_api_key_from_request(request)
    endpoint = request.url.path
    return f"{identifier}:{endpoint}"


# Rate limit configurations (can be overridden via environment)
RATE_LIMITS = {
    # Anonymous (IP-based) limits
    "anonymous_per_minute": os.getenv("RATE_LIMIT_ANON_PER_MIN", "10/minute"),
    "anonymous_per_hour": os.getenv("RATE_LIMIT_ANON_PER_HOUR", "100/hour"),
    "anonymous_per_day": os.getenv("RATE_LIMIT_ANON_PER_DAY", "1000/day"),
    
    # Authenticated (API key) limits
    "authenticated_per_minute": os.getenv("RATE_LIMIT_AUTH_PER_MIN", "60/minute"),
    "authenticated_per_hour": os.getenv("RATE_LIMIT_AUTH_PER_HOUR", "1000/hour"),
    "authenticated_per_day": os.getenv("RATE_LIMIT_AUTH_PER_DAY", "10000/day"),
    
    # Expensive endpoints (scraping)
    "scrape_per_minute": os.getenv("RATE_LIMIT_SCRAPE_PER_MIN", "5/minute"),
    "scrape_per_hour": os.getenv("RATE_LIMIT_SCRAPE_PER_HOUR", "50/hour"),
    
    # Batch endpoints
    "batch_per_minute": os.getenv("RATE_LIMIT_BATCH_PER_MIN", "2/minute"),
    "batch_per_hour": os.getenv("RATE_LIMIT_BATCH_PER_HOUR", "20/hour"),
}


# Create limiter instance
limiter = Limiter(
    key_func=custom_rate_limit_key,
    storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    enabled=os.getenv("RATE_LIMITING_ENABLED", "true").lower() == "true"
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.
    
    Returns JSON response with:
    - Error message
    - Retry-After header
    - Current usage information
    """
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Please retry after {exc.retry_after} seconds",
            "retry_after": exc.retry_after,
            "limit": str(exc.limit),
            "documentation": "https://docs.example.com/rate-limits"
        },
        headers={
            "Retry-After": str(exc.retry_after),
            "X-RateLimit-Limit": str(exc.limit),
            "X-RateLimit-Reset": str(exc.retry_after),
        }
    )


def get_rate_limit_for_request(request: Request) -> str:
    """
    Determine appropriate rate limit based on request.
    
    Logic:
    1. Check if authenticated (has API key)
    2. Check endpoint type (scrape, batch, general)
    3. Return strictest applicable limit
    """
    # Check if authenticated
    has_api_key = (
        request.headers.get("X-API-Key") or
        request.headers.get("Authorization", "").startswith("Bearer ") or
        request.query_params.get("api_key")
    )
    
    # Get endpoint path
    path = request.url.path
    
    # Determine rate limit
    if "/scrape" in path and "/batch" not in path:
        return RATE_LIMITS["scrape_per_minute"]
    elif "/batch" in path:
        return RATE_LIMITS["batch_per_minute"]
    elif has_api_key:
        return RATE_LIMITS["authenticated_per_minute"]
    else:
        return RATE_LIMITS["anonymous_per_minute"]


def apply_rate_limits(app) -> None:
    """
    Apply rate limiting to FastAPI application.
    
    Args:
        app: FastAPI application instance
    
    Sets up:
    - Rate limit exception handler
    - Middleware for tracking limits
    - Response headers with limit info
    """
    # Add rate limit exceeded handler
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    
    # Add state for limiter
    app.state.limiter = limiter
    
    # Note: Individual endpoints should be decorated with @limiter.limit()
    # This function just sets up the infrastructure


def check_custom_rate_limit(
    request: Request,
    api_key: Optional[str] = None,
    max_requests: int = 100,
    window: int = 3600
) -> bool:
    """
    Check custom rate limit for specific use cases.
    
    Args:
        request: FastAPI request object
        api_key: Optional API key to check
        max_requests: Maximum requests allowed
        window: Time window in seconds
    
    Returns:
        True if within limit, False if exceeded
    
    Raises:
        HTTPException: If limit exceeded
    """
    # Build key
    if api_key:
        key = f"custom:apikey:{api_key}"
    else:
        key = f"custom:ip:{get_remote_address(request)}"
    
    # This is a simplified placeholder implementation
    # In production, you would check Redis directly with the key
    # For now, we always return True (allow request)
    try:
        # Placeholder for actual Redis rate limit check
        # Example: limiter.storage.incr(key, window)
        return True
        
    except Exception as e:
        # If rate limiting fails, allow request but log error
        import logging
        logging.warning(f"Rate limit check failed: {e}")
        return True


def get_current_usage(request: Request) -> dict:
    """
    Get current rate limit usage for request.
    
    Returns:
        Dictionary with:
        - requests_made: Number of requests in current window
        - requests_remaining: Number of requests left
        - reset_time: When the limit resets (timestamp)
    """
    # This is a placeholder - actual implementation would query Redis
    # For now, return dummy data
    return {
        "requests_made": 0,
        "requests_remaining": 1000,
        "reset_time": 0,
        "limit": "1000/hour"
    }


def is_rate_limited(request: Request) -> bool:
    """
    Check if current request is rate limited.
    
    Returns:
        True if rate limited, False if allowed
    """
    try:
        # Get identifier
        identifier = custom_rate_limit_key(request)
        
        # Check against storage
        # This is simplified - actual implementation would check Redis
        return False
        
    except Exception:
        # If check fails, allow request (fail open)
        return False


# Decorator for custom rate limiting on specific endpoints
def custom_limit(limit: str):
    """
    Decorator to apply custom rate limit to endpoint.
    
    Usage:
        @custom_limit("10/minute")
        async def my_endpoint():
            ...
    
    Args:
        limit: Rate limit string (e.g., "10/minute", "100/hour")
    """
    def decorator(func):
        # Store limit on function for later use
        func._rate_limit = limit
        return func
    return decorator


# Pre-defined rate limit decorators for common use cases
def scrape_endpoint_limit():
    """Rate limit for scraping endpoints."""
    return limiter.limit(RATE_LIMITS["scrape_per_minute"])


def batch_endpoint_limit():
    """Rate limit for batch endpoints."""
    return limiter.limit(RATE_LIMITS["batch_per_minute"])


def authenticated_endpoint_limit():
    """Rate limit for authenticated endpoints."""
    return limiter.limit(RATE_LIMITS["authenticated_per_minute"])


def anonymous_endpoint_limit():
    """Rate limit for anonymous endpoints."""
    return limiter.limit(RATE_LIMITS["anonymous_per_minute"])
