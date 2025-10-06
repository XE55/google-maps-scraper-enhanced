"""
SQLAlchemy database models for persistent storage.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class APIKey(Base):
    """API key management table."""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    rate_limit_per_minute = Column(Integer, default=10, nullable=False)
    rate_limit_per_hour = Column(Integer, default=100, nullable=False)
    rate_limit_per_day = Column(Integer, default=1000, nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_api_key_active', 'key', 'is_active'),
    )


class RateLimitTracking(Base):
    """Rate limit tracking table."""
    __tablename__ = "rate_limit_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String, index=True, nullable=False)
    endpoint = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Indexes for efficient rate limit lookups
    __table_args__ = (
        Index('idx_rate_limit_lookup', 'api_key', 'timestamp'),
    )
