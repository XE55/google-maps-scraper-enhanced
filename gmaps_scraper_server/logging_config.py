"""
Structured logging configuration with request tracking and rotation.
"""
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Dict

import structlog
from structlog.types import EventDict, Processor


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to all log entries."""
    event_dict["app"] = "gmaps-scraper"
    return event_dict


def add_log_level(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add log level to event dict."""
    if method_name == "warn":
        # Backward compatibility
        level = "warning"
    else:
        level = method_name
    event_dict["level"] = level
    return event_dict


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: str = None,
    log_max_bytes: int = 10485760,  # 10MB
    log_backup_count: int = 5,
) -> None:
    """
    Configure structured logging with rotation.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ('json' or 'console')
        log_file: Optional log file path
        log_max_bytes: Max log file size before rotation
        log_backup_count: Number of backup files to keep
    """
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
    )
    
    # Shared processors for all configurations
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        add_app_context,
        add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
    ]
    
    # Add format-specific processors
    if log_format == "json":
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ]
    else:
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Setup file logging with rotation if enabled
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=log_max_bytes,
            backupCount=log_backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(numeric_level)
        
        # Add handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    return structlog.get_logger(name)


def log_request_start(
    method: str,
    path: str,
    request_id: str,
    client_ip: str = None,
    **kwargs
) -> None:
    """
    Log incoming API request.
    
    Args:
        method: HTTP method
        path: Request path
        request_id: Unique request ID
        client_ip: Client IP address
        **kwargs: Additional context
    """
    logger = get_logger("api")
    logger.info(
        "request_start",
        method=method,
        path=path,
        request_id=request_id,
        client_ip=client_ip,
        **kwargs
    )


def log_request_end(
    method: str,
    path: str,
    request_id: str,
    status_code: int,
    duration_ms: float,
    **kwargs
) -> None:
    """
    Log completed API request.
    
    Args:
        method: HTTP method
        path: Request path
        request_id: Unique request ID
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        **kwargs: Additional context
    """
    logger = get_logger("api")
    logger.info(
        "request_end",
        method=method,
        path=path,
        request_id=request_id,
        status_code=status_code,
        duration_ms=duration_ms,
        **kwargs
    )


def log_scraping_start(
    search_query: str,
    max_places: int,
    request_id: str = None,
    **kwargs
) -> None:
    """
    Log scraping operation start.
    
    Args:
        search_query: Google Maps search query
        max_places: Maximum places to scrape
        request_id: Optional request ID
        **kwargs: Additional context
    """
    logger = get_logger("scraper")
    logger.info(
        "scraping_start",
        search_query=search_query,
        max_places=max_places,
        request_id=request_id,
        **kwargs
    )


def log_scraping_end(
    search_query: str,
    places_found: int,
    duration_ms: float,
    success: bool = True,
    error: str = None,
    request_id: str = None,
    **kwargs
) -> None:
    """
    Log scraping operation completion.
    
    Args:
        search_query: Google Maps search query
        places_found: Number of places scraped
        duration_ms: Operation duration in milliseconds
        success: Whether operation succeeded
        error: Error message if failed
        request_id: Optional request ID
        **kwargs: Additional context
    """
    logger = get_logger("scraper")
    
    if success:
        logger.info(
            "scraping_end",
            search_query=search_query,
            places_found=places_found,
            duration_ms=duration_ms,
            request_id=request_id,
            **kwargs
        )
    else:
        logger.error(
            "scraping_failed",
            search_query=search_query,
            places_found=places_found,
            duration_ms=duration_ms,
            error=error,
            request_id=request_id,
            **kwargs
        )


def log_email_verification(
    email: str,
    is_valid: bool,
    duration_ms: float,
    error: str = None,
    **kwargs
) -> None:
    """
    Log email verification attempt.
    
    Args:
        email: Email address (will be partially masked)
        is_valid: Verification result
        duration_ms: Operation duration in milliseconds
        error: Error message if failed
        **kwargs: Additional context
    """
    logger = get_logger("email_verifier")
    
    # Mask email for privacy
    if "@" in email:
        local, domain = email.split("@", 1)
        masked_email = f"{local[:2]}***@{domain}"
    else:
        masked_email = "***"
    
    logger.info(
        "email_verification",
        email=masked_email,
        is_valid=is_valid,
        duration_ms=duration_ms,
        error=error,
        **kwargs
    )


def log_proxy_rotation(
    old_proxy: str,
    new_proxy: str,
    reason: str,
    **kwargs
) -> None:
    """
    Log proxy rotation event.
    
    Args:
        old_proxy: Previous proxy URL
        new_proxy: New proxy URL
        reason: Reason for rotation
        **kwargs: Additional context
    """
    logger = get_logger("proxy_manager")
    logger.info(
        "proxy_rotation",
        old_proxy=old_proxy,
        new_proxy=new_proxy,
        reason=reason,
        **kwargs
    )


def log_rate_limit_exceeded(
    api_key: str,
    limit_type: str,
    limit_value: int,
    current_count: int,
    **kwargs
) -> None:
    """
    Log rate limit exceeded event.
    
    Args:
        api_key: Masked API key
        limit_type: Type of limit (minute/hour/day)
        limit_value: Limit threshold
        current_count: Current request count
        **kwargs: Additional context
    """
    logger = get_logger("rate_limiter")
    
    # Mask API key
    masked_key = f"{api_key[:8]}..." if len(api_key) > 8 else "***"
    
    logger.warning(
        "rate_limit_exceeded",
        api_key=masked_key,
        limit_type=limit_type,
        limit_value=limit_value,
        current_count=current_count,
        **kwargs
    )


def log_exception(
    exception: Exception,
    context: Dict[str, Any] = None,
    **kwargs
) -> None:
    """
    Log exception with full context.
    
    Args:
        exception: Exception instance
        context: Additional context dictionary
        **kwargs: Additional context
    """
    logger = get_logger("exception")
    
    log_data = {
        "exception_type": type(exception).__name__,
        "exception_message": str(exception),
        **(context or {}),
        **kwargs
    }
    
    logger.exception(
        "exception_occurred",
        **log_data
    )


# Example usage and testing
if __name__ == "__main__":
    # Setup logging in console format for testing
    setup_logging(log_level="DEBUG", log_format="console")
    
    # Test various log functions
    logger = get_logger(__name__)
    logger.info("Testing structured logging", test_id=12345)
    
    log_request_start("GET", "/api/scrape", "req-123", client_ip="192.168.1.1")
    log_request_end("GET", "/api/scrape", "req-123", 200, 1234.56)
    
    log_scraping_start("pizza near me", 50, "req-123")
    log_scraping_end("pizza near me", 45, 5678.90, request_id="req-123")
    
    log_email_verification("test@example.com", True, 123.45)
    log_proxy_rotation("http://proxy1:8080", "http://proxy2:8080", "health_check_failed")
    log_rate_limit_exceeded("test_api_key_12345", "minute", 10, 11)
    
    try:
        raise ValueError("Test exception")
    except Exception as e:
        log_exception(e, context={"operation": "test"})
    
    logger.info("Logging test complete")
