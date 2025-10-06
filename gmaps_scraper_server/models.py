"""
Pydantic models for input validation and output serialization.

Security features:
- Max places limit (500) prevents resource exhaustion
- Query length validation prevents injection attacks
- Strict type validation for all fields
- ISO language code validation
- URL validation for webhooks
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, HttpUrl
import re


class LanguageCode(str, Enum):
    """ISO 639-1 language codes supported by Google Maps."""
    EN = "en"  # English
    ES = "es"  # Spanish
    FR = "fr"  # French
    DE = "de"  # German
    IT = "it"  # Italian
    PT = "pt"  # Portuguese
    RU = "ru"  # Russian
    JA = "ja"  # Japanese
    ZH = "zh"  # Chinese
    AR = "ar"  # Arabic
    HI = "hi"  # Hindi
    BN = "bn"  # Bengali


class SortBy(str, Enum):
    """Sorting options for results."""
    RELEVANCE = "relevance"
    RATING = "rating"
    REVIEWS = "reviews"
    DISTANCE = "distance"


class ScrapeRequest(BaseModel):
    """
    Request model for Google Maps scraping endpoint.
    
    Security validations:
    - Query: 1-200 chars (prevents injection)
    - Max places: 1-500 (prevents resource exhaustion)
    - Language: ISO 639-1 codes only
    - No special chars in sort_by
    """
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Search query (e.g., 'restaurants in New York')",
        examples=["coffee shops in Seattle", "dentists near 90210"]
    )
    
    max_places: int = Field(
        default=20,
        ge=1,
        le=500,
        description="Maximum number of places to scrape (1-500)"
    )
    
    language: LanguageCode = Field(
        default=LanguageCode.EN,
        description="Language code for results (ISO 639-1)"
    )
    
    extract_emails: bool = Field(
        default=False,
        description="Extract email addresses from websites"
    )
    
    extract_social: bool = Field(
        default=False,
        description="Extract social media links"
    )
    
    deduplicate: bool = Field(
        default=True,
        description="Remove duplicate entries"
    )
    
    sort_by: SortBy = Field(
        default=SortBy.RELEVANCE,
        description="Sort results by field"
    )
    
    webhook_url: Optional[HttpUrl] = Field(
        default=None,
        description="Webhook URL for async notifications (https only)"
    )
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """
        Validate search query for security.
        
        Prevents:
        - SQL injection attempts
        - Script injection
        - Control characters
        """
        # Remove leading/trailing whitespace
        v = v.strip()
        
        # Check for control characters
        if any(ord(c) < 32 for c in v):
            raise ValueError("Query contains invalid control characters")
        
        # Check for common injection patterns
        dangerous_patterns = [
            r"<script",
            r"javascript:",
            r"on\w+\s*=",  # event handlers
            r";\s*DROP\s+TABLE",
            r"UNION\s+SELECT",
            r"'\s*--",  # SQL comment after quote
            r"'\s*;",  # SQL statement after quote
            r"\.\./",  # path traversal
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(f"Query contains potentially dangerous pattern: {pattern}")
        
        return v
    
    @field_validator('webhook_url')
    @classmethod
    def validate_webhook_url(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        """Ensure webhook URL uses HTTPS only."""
        if v is not None and str(v).startswith('http://'):
            raise ValueError("Webhook URL must use HTTPS for security")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "italian restaurants in Rome",
                "max_places": 50,
                "language": "it",
                "extract_emails": True,
                "extract_social": True,
                "deduplicate": True,
                "sort_by": "rating",
                "webhook_url": "https://example.com/webhook"
            }
        }


class PlaceResult(BaseModel):
    """
    Output model for a single place result.
    
    Contains all extracted information with proper typing.
    """
    
    place_id: str = Field(..., description="Google Maps place ID")
    name: str = Field(..., description="Business name")
    
    # Contact information
    address: Optional[str] = Field(None, description="Full address")
    phone: Optional[str] = Field(None, description="Phone number")
    website: Optional[str] = Field(None, description="Website URL")
    email: Optional[str] = Field(None, description="Email address")
    
    # Location
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")
    
    # Business details
    category: Optional[str] = Field(None, description="Business category")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Rating (0-5)")
    reviews_count: Optional[int] = Field(None, ge=0, description="Number of reviews")
    price_level: Optional[int] = Field(None, ge=1, le=4, description="Price level (1-4)")
    
    # Hours
    hours: Optional[Dict[str, str]] = Field(None, description="Opening hours by day")
    is_open_now: Optional[bool] = Field(None, description="Currently open")
    
    # Social media
    facebook_url: Optional[str] = Field(None, description="Facebook page")
    instagram_url: Optional[str] = Field(None, description="Instagram profile")
    twitter_url: Optional[str] = Field(None, description="Twitter profile")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn page")
    
    # Quality metrics
    quality_score: Optional[float] = Field(None, ge=0, le=100, description="Data quality score (0-100)")
    completeness_score: Optional[float] = Field(None, ge=0, le=100, description="Completeness score (0-100)")
    
    # Metadata
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="Scrape timestamp")
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Normalize phone number format."""
        if v is None:
            return None
        
        # Remove common separators
        v = re.sub(r'[\s\-\(\)\.]', '', v)
        
        # Keep only digits and + sign
        v = re.sub(r'[^\d+]', '', v)
        
        return v if v else None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Basic email validation."""
        if v is None:
            return None
        
        # Simple regex for email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError(f"Invalid email format: {v}")
        
        return v.lower()
    
    class Config:
        json_schema_extra = {
            "example": {
                "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
                "name": "Google Sydney",
                "address": "48 Pirrama Rd, Pyrmont NSW 2009, Australia",
                "phone": "+61 2 9374 4000",
                "website": "https://www.google.com.au/",
                "email": "info@google.com",
                "latitude": -33.866489,
                "longitude": 151.195814,
                "category": "Corporate office",
                "rating": 4.6,
                "reviews_count": 5820,
                "price_level": None,
                "hours": {
                    "Monday": "9:00 AM – 5:00 PM",
                    "Tuesday": "9:00 AM – 5:00 PM"
                },
                "is_open_now": True,
                "facebook_url": "https://facebook.com/google",
                "quality_score": 95.5,
                "completeness_score": 88.0
            }
        }


class ScrapeResponse(BaseModel):
    """
    Response model for scrape endpoint.
    
    Contains results and metadata about the scraping operation.
    """
    
    success: bool = Field(..., description="Whether scrape was successful")
    total_results: int = Field(..., ge=0, description="Number of results found")
    results: List[PlaceResult] = Field(default_factory=list, description="List of places")
    
    # Job tracking
    job_id: Optional[str] = Field(None, description="Job ID for async tracking")
    status: Optional[str] = Field(None, description="Job status (pending/running/completed/failed)")
    
    # Performance metrics
    execution_time: Optional[float] = Field(None, ge=0, description="Execution time in seconds")
    pages_scraped: Optional[int] = Field(None, ge=0, description="Number of pages scraped")
    
    # Error information
    error: Optional[str] = Field(None, description="Error message if failed")
    errors: Optional[List[str]] = Field(default_factory=list, description="List of non-fatal errors")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "total_results": 50,
                "results": [],  # Would contain PlaceResult objects
                "job_id": "job_abc123",
                "status": "completed",
                "execution_time": 45.2,
                "pages_scraped": 5,
                "errors": []
            }
        }


class BatchScrapeRequest(BaseModel):
    """
    Request model for batch scraping endpoint.
    
    Allows multiple queries in a single request.
    """
    
    queries: List[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of search queries (1-10)"
    )
    
    max_places_per_query: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Max places per query (1-100)"
    )
    
    language: LanguageCode = Field(
        default=LanguageCode.EN,
        description="Language code for all queries"
    )
    
    webhook_url: Optional[HttpUrl] = Field(
        default=None,
        description="Webhook URL for completion notification"
    )
    
    @field_validator('webhook_url')
    @classmethod
    def validate_webhook_url(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        """Ensure webhook URL uses HTTPS only."""
        if v is not None and str(v).startswith('http://'):
            raise ValueError("Webhook URL must use HTTPS for security")
        return v
    
    @field_validator('queries')
    @classmethod
    def validate_queries(cls, v: List[str]) -> List[str]:
        """Validate each query in the batch."""
        if not v:
            raise ValueError("At least one query is required")
        
        # Note: max_length=10 is enforced by Field constraint above
        
        # Validate each query
        validated = []
        for query in v:
            query = query.strip()
            if len(query) < 1:
                raise ValueError("Empty query in batch")
            if len(query) > 200:
                raise ValueError(f"Query too long: {query[:50]}...")
            validated.append(query)
        
        return validated
    
    class Config:
        json_schema_extra = {
            "example": {
                "queries": [
                    "coffee shops in Seattle",
                    "restaurants in Portland",
                    "hotels in Vancouver"
                ],
                "max_places_per_query": 50,
                "language": "en",
                "webhook_url": "https://example.com/batch-webhook"
            }
        }
