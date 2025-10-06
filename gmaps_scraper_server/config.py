"""
Configuration management with environment variable validation.
Loads and validates all configuration from environment variables.
"""
import os
from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = Field(default="google-maps-scraper", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Server
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8001, env="PORT")
    workers: int = Field(default=4, env="WORKERS")
    reload: bool = Field(default=False, env="RELOAD")
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")  # Required
    api_key_salt: str = Field(..., env="API_KEY_SALT")  # Required
    admin_password: str = Field(..., env="ADMIN_PASSWORD")  # Required
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")  # Required
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Redis
    redis_url: str = Field(default="redis://redis:6379/0", env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    cache_enabled: bool = Field(default=True, env="CACHE_ENABLED")
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=10, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=100, env="RATE_LIMIT_PER_HOUR")
    rate_limit_per_day: int = Field(default=1000, env="RATE_LIMIT_PER_DAY")
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    
    # Scraping
    max_places_limit: int = Field(default=500, env="MAX_PLACES_LIMIT")
    default_max_places: int = Field(default=20, env="DEFAULT_MAX_PLACES")
    scrape_timeout_seconds: int = Field(default=300, env="SCRAPE_TIMEOUT_SECONDS")
    scroll_pause_time: float = Field(default=1.5, env="SCROLL_PAUSE_TIME")
    max_scroll_attempts: int = Field(default=5, env="MAX_SCROLL_ATTEMPTS")
    
    # Playwright
    playwright_headless: bool = Field(default=True, env="PLAYWRIGHT_HEADLESS")
    playwright_timeout: int = Field(default=30000, env="PLAYWRIGHT_TIMEOUT")
    browser_pool_size: int = Field(default=5, env="BROWSER_POOL_SIZE")
    
    # Anti-Detection
    min_request_delay: float = Field(default=3.0, env="MIN_REQUEST_DELAY")
    max_request_delay: float = Field(default=8.0, env="MAX_REQUEST_DELAY")
    use_stealth_mode: bool = Field(default=True, env="USE_STEALTH_MODE")
    rotate_user_agents: bool = Field(default=True, env="ROTATE_USER_AGENTS")
    human_like_behavior: bool = Field(default=True, env="HUMAN_LIKE_BEHAVIOR")
    
    # Proxy
    proxy_provider: Optional[str] = Field(default=None, env="PROXY_PROVIDER")
    proxy_list: Optional[str] = Field(default=None, env="PROXY_LIST")
    proxy_rotation_strategy: str = Field(default="round-robin", env="PROXY_ROTATION_STRATEGY")
    proxy_health_check_interval: int = Field(default=300, env="PROXY_HEALTH_CHECK_INTERVAL")
    
    # Proxy providers
    brightdata_username: Optional[str] = Field(default=None, env="BRIGHTDATA_USERNAME")
    brightdata_password: Optional[str] = Field(default=None, env="BRIGHTDATA_PASSWORD")
    brightdata_zone: Optional[str] = Field(default=None, env="BRIGHTDATA_ZONE")
    smartproxy_username: Optional[str] = Field(default=None, env="SMARTPROXY_USERNAME")
    smartproxy_password: Optional[str] = Field(default=None, env="SMARTPROXY_PASSWORD")
    
    # Email Verification
    enable_email_verification: bool = Field(default=True, env="ENABLE_EMAIL_VERIFICATION")
    email_verifier_url: str = Field(
        default="https://rapid-email-verifier.fly.dev/",
        env="EMAIL_VERIFIER_URL"
    )
    email_verifier_timeout: int = Field(default=5, env="EMAIL_VERIFIER_TIMEOUT")
    
    # Data Quality
    enable_phone_normalization: bool = Field(default=True, env="ENABLE_PHONE_NORMALIZATION")
    enable_duplicate_detection: bool = Field(default=True, env="ENABLE_DUPLICATE_DETECTION")
    min_data_quality_score: float = Field(default=0.5, env="MIN_DATA_QUALITY_SCORE")
    
    # Async Jobs
    job_cleanup_interval: int = Field(default=3600, env="JOB_CLEANUP_INTERVAL")
    job_retention_days: int = Field(default=7, env="JOB_RETENTION_DAYS")
    max_batch_size: int = Field(default=50, env="MAX_BATCH_SIZE")
    webhook_timeout: int = Field(default=10, env="WEBHOOK_TIMEOUT")
    webhook_retry_attempts: int = Field(default=3, env="WEBHOOK_RETRY_ATTEMPTS")
    
    # Monitoring
    health_check_enabled: bool = Field(default=True, env="HEALTH_CHECK_ENABLED")
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    request_id_header: str = Field(default="X-Request-ID", env="REQUEST_ID_HEADER")
    
    # Logging
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file_enabled: bool = Field(default=True, env="LOG_FILE_ENABLED")
    log_file_path: str = Field(default="/app/logs/scraper.log", env="LOG_FILE_PATH")
    log_file_max_size: int = Field(default=10485760, env="LOG_FILE_MAX_SIZE")  # 10MB
    log_file_backup_count: int = Field(default=5, env="LOG_FILE_BACKUP_COUNT")
    
    # CORS
    cors_enabled: bool = Field(default=True, env="CORS_ENABLED")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    
    # Request Limits
    max_request_size: int = Field(default=1048576, env="MAX_REQUEST_SIZE")  # 1MB
    request_timeout: int = Field(default=60, env="REQUEST_TIMEOUT")
    
    # Google Maps
    google_maps_base_url: str = Field(
        default="https://www.google.com/maps/search/",
        env="GOOGLE_MAPS_BASE_URL"
    )
    google_maps_default_lang: str = Field(default="en", env="GOOGLE_MAPS_DEFAULT_LANG")
    
    @validator("secret_key", "api_key_salt", "admin_password")
    def validate_secrets(cls, v, field):
        """Ensure security-critical values are not defaults."""
        if not v or v in ["CHANGE_ME", "changeme", "password", "secret"]:
            raise ValueError(
                f"{field.name} must be set to a secure value. "
                f"Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if len(v) < 32:
            raise ValueError(f"{field.name} must be at least 32 characters long")
        return v
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment value."""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"environment must be one of: {allowed}")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"log_level must be one of: {allowed}")
        return v.upper()
    
    @validator("log_format")
    def validate_log_format(cls, v):
        """Validate log format."""
        allowed = ["json", "console"]
        if v not in allowed:
            raise ValueError(f"log_format must be one of: {allowed}")
        return v
    
    @validator("proxy_rotation_strategy")
    def validate_proxy_strategy(cls, v):
        """Validate proxy rotation strategy."""
        allowed = ["round-robin", "random", "least-used", "performance-based"]
        if v not in allowed:
            raise ValueError(f"proxy_rotation_strategy must be one of: {allowed}")
        return v
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from JSON string if needed."""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v.split(",")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def validate_environment():
    """
    Validate environment configuration on startup.
    Raises ValueError if required variables are missing or invalid.
    """
    try:
        settings = Settings()
        
        # Additional validation
        if settings.environment == "production":
            if settings.debug:
                raise ValueError("DEBUG must be False in production")
            if settings.reload:
                raise ValueError("RELOAD must be False in production")
            if settings.database_echo:
                raise ValueError("DATABASE_ECHO must be False in production")
        
        # Validate database URL format
        if not settings.database_url.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        
        # Validate Redis URL format
        if not settings.redis_url.startswith("redis://"):
            raise ValueError("REDIS_URL must be a Redis connection string")
        
        return settings
        
    except Exception as e:
        print(f"\n❌ Environment Configuration Error:")
        print(f"   {str(e)}\n")
        print("💡 Tip: Copy .env.example to .env and fill in your values")
        print("   Generate secrets with: python -c \"import secrets; print(secrets.token_hex(32))\"")
        raise


# Global settings instance
settings = validate_environment()


if __name__ == "__main__":
    """Test configuration loading."""
    print("✅ Environment configuration validated successfully!")
    print(f"\nConfiguration Summary:")
    print(f"  App: {settings.app_name} v{settings.app_version}")
    print(f"  Environment: {settings.environment}")
    print(f"  Debug: {settings.debug}")
    print(f"  Log Level: {settings.log_level}")
    print(f"  Server: {settings.host}:{settings.port}")
    print(f"  Database: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'configured'}")
    print(f"  Redis: {settings.redis_url}")
    print(f"  Cache Enabled: {settings.cache_enabled}")
    print(f"  Rate Limiting: {settings.rate_limit_enabled}")
    print(f"  Stealth Mode: {settings.use_stealth_mode}")
    print(f"  Proxy: {settings.proxy_provider or 'None'}")
    print(f"  Email Verification: {settings.enable_email_verification}")
    print(f"  Health Checks: {settings.health_check_enabled}")
    print(f"  Metrics: {settings.metrics_enabled}")
