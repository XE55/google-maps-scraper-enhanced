"""
Unit tests for Pydantic validation models.

Tests cover:
- Input validation and sanitization
- Security checks (injection prevention)
- Field constraints and limits
- Edge cases and error conditions
- Output serialization
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from gmaps_scraper_server.models import (
    ScrapeRequest,
    PlaceResult,
    ScrapeResponse,
    BatchScrapeRequest,
    LanguageCode,
    SortBy
)


class TestScrapeRequest:
    """Test suite for ScrapeRequest validation model."""
    
    def test_valid_request_minimal(self):
        """Test valid request with minimal required fields."""
        request = ScrapeRequest(query="coffee shops")
        
        assert request.query == "coffee shops"
        assert request.max_places == 20  # default
        assert request.language == LanguageCode.EN  # default
        assert request.extract_emails is False  # default
        assert request.extract_social is False  # default
        assert request.deduplicate is True  # default
        assert request.sort_by == SortBy.RELEVANCE  # default
        assert request.webhook_url is None  # default
    
    def test_valid_request_all_fields(self):
        """Test valid request with all fields specified."""
        request = ScrapeRequest(
            query="italian restaurants",
            max_places=100,
            language=LanguageCode.IT,
            extract_emails=True,
            extract_social=True,
            deduplicate=False,
            sort_by=SortBy.RATING,
            webhook_url="https://example.com/webhook"
        )
        
        assert request.query == "italian restaurants"
        assert request.max_places == 100
        assert request.language == LanguageCode.IT
        assert request.extract_emails is True
        assert request.extract_social is True
        assert request.deduplicate is False
        assert request.sort_by == SortBy.RATING
        assert str(request.webhook_url) == "https://example.com/webhook"
    
    def test_query_whitespace_trimming(self):
        """Test that leading/trailing whitespace is trimmed from query."""
        request = ScrapeRequest(query="  coffee shops  ")
        assert request.query == "coffee shops"
    
    def test_query_too_short(self):
        """Test that empty query is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ScrapeRequest(query="")
        
        errors = exc_info.value.errors()
        assert any("at least 1 character" in str(e) for e in errors)
    
    def test_query_too_long(self):
        """Test that query over 200 chars is rejected."""
        long_query = "a" * 201
        
        with pytest.raises(ValidationError) as exc_info:
            ScrapeRequest(query=long_query)
        
        errors = exc_info.value.errors()
        assert any("at most 200 character" in str(e) for e in errors)
    
    def test_query_xss_injection_prevented(self):
        """Test that XSS attempts are blocked."""
        dangerous_queries = [
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            "onclick=alert(1)",
            "<img src=x onerror=alert(1)>"
        ]
        
        for query in dangerous_queries:
            with pytest.raises(ValidationError) as exc_info:
                ScrapeRequest(query=query)
            
            errors = exc_info.value.errors()
            assert any("dangerous pattern" in str(e).lower() for e in errors), \
                f"Failed to block: {query}"
    
    def test_query_sql_injection_prevented(self):
        """Test that SQL injection attempts are blocked."""
        dangerous_queries = [
            "'; DROP TABLE users; --",
            "1' UNION SELECT * FROM passwords--",
            "admin'--"
        ]
        
        for query in dangerous_queries:
            with pytest.raises(ValidationError) as exc_info:
                ScrapeRequest(query=query)
            
            errors = exc_info.value.errors()
            assert any("dangerous pattern" in str(e).lower() for e in errors), \
                f"Failed to block: {query}"
    
    def test_query_path_traversal_prevented(self):
        """Test that path traversal attempts are blocked."""
        with pytest.raises(ValidationError) as exc_info:
            ScrapeRequest(query="../../../etc/passwd")
        
        errors = exc_info.value.errors()
        assert any("dangerous pattern" in str(e).lower() for e in errors)
    
    def test_query_control_characters_prevented(self):
        """Test that control characters are blocked."""
        query_with_null = "coffee\x00shops"
        query_with_tab = "coffee\tshops"  # Tab is allowed (ASCII 9)
        query_with_newline = "coffee\nshops"  # Newline might be blocked
        
        # Null byte should be blocked
        with pytest.raises(ValidationError) as exc_info:
            ScrapeRequest(query=query_with_null)
        
        errors = exc_info.value.errors()
        assert any("control character" in str(e).lower() for e in errors)
    
    def test_max_places_below_minimum(self):
        """Test that max_places below 1 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ScrapeRequest(query="test", max_places=0)
        
        errors = exc_info.value.errors()
        assert any("greater than or equal to 1" in str(e) for e in errors)
    
    def test_max_places_above_maximum(self):
        """Test that max_places above 500 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ScrapeRequest(query="test", max_places=501)
        
        errors = exc_info.value.errors()
        assert any("less than or equal to 500" in str(e) for e in errors)
    
    def test_max_places_boundary_values(self):
        """Test boundary values for max_places."""
        # Minimum
        request = ScrapeRequest(query="test", max_places=1)
        assert request.max_places == 1
        
        # Maximum
        request = ScrapeRequest(query="test", max_places=500)
        assert request.max_places == 500
    
    def test_invalid_language_code(self):
        """Test that invalid language codes are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ScrapeRequest(query="test", language="invalid")
        
        errors = exc_info.value.errors()
        assert any("language" in str(e).lower() for e in errors)
    
    def test_all_language_codes(self):
        """Test that all supported language codes work."""
        for lang in LanguageCode:
            request = ScrapeRequest(query="test", language=lang)
            assert request.language == lang
    
    def test_webhook_url_https_required(self):
        """Test that webhook URL must use HTTPS."""
        with pytest.raises(ValidationError) as exc_info:
            ScrapeRequest(
                query="test",
                webhook_url="http://insecure.com/webhook"
            )
        
        errors = exc_info.value.errors()
        assert any("https" in str(e).lower() for e in errors)
    
    def test_webhook_url_https_accepted(self):
        """Test that HTTPS webhook URL is accepted."""
        request = ScrapeRequest(
            query="test",
            webhook_url="https://secure.com/webhook"
        )
        assert str(request.webhook_url) == "https://secure.com/webhook"
    
    def test_webhook_url_invalid_format(self):
        """Test that malformed URLs are rejected."""
        with pytest.raises(ValidationError):
            ScrapeRequest(
                query="test",
                webhook_url="not-a-url"
            )
    
    def test_all_sort_by_options(self):
        """Test that all sorting options work."""
        for sort_option in SortBy:
            request = ScrapeRequest(query="test", sort_by=sort_option)
            assert request.sort_by == sort_option


class TestPlaceResult:
    """Test suite for PlaceResult model."""
    
    def test_minimal_place_result(self):
        """Test place result with only required fields."""
        result = PlaceResult(
            place_id="ChIJ123",
            name="Test Place"
        )
        
        assert result.place_id == "ChIJ123"
        assert result.name == "Test Place"
        assert result.address is None
        assert result.phone is None
        assert isinstance(result.scraped_at, datetime)
    
    def test_full_place_result(self):
        """Test place result with all fields."""
        result = PlaceResult(
            place_id="ChIJ123",
            name="Test Restaurant",
            address="123 Main St",
            phone="+1-555-123-4567",
            website="https://example.com",
            email="info@example.com",
            latitude=40.7128,
            longitude=-74.0060,
            category="Restaurant",
            rating=4.5,
            reviews_count=1250,
            price_level=2,
            hours={"Monday": "9 AM - 5 PM"},
            is_open_now=True,
            facebook_url="https://facebook.com/test",
            quality_score=85.5,
            completeness_score=90.0
        )
        
        assert result.name == "Test Restaurant"
        assert result.rating == 4.5
        assert result.quality_score == 85.5
    
    def test_phone_normalization(self):
        """Test that phone numbers are normalized."""
        # Test various formats
        test_cases = [
            ("+1 (555) 123-4567", "+15551234567"),
            ("555-123-4567", "5551234567"),
            ("555.123.4567", "5551234567"),
            ("+44 20 7123 4567", "+442071234567"),
        ]
        
        for input_phone, expected_phone in test_cases:
            result = PlaceResult(
                place_id="test",
                name="test",
                phone=input_phone
            )
            assert result.phone == expected_phone, \
                f"Failed for {input_phone}, got {result.phone}"
    
    def test_phone_empty_string(self):
        """Test that empty phone string becomes None."""
        result = PlaceResult(
            place_id="test",
            name="test",
            phone="   "
        )
        assert result.phone is None
    
    def test_email_validation_valid(self):
        """Test that valid emails are accepted."""
        valid_emails = [
            "user@example.com",
            "test.user@example.co.uk",
            "info+tag@company.org"
        ]
        
        for email in valid_emails:
            result = PlaceResult(
                place_id="test",
                name="test",
                email=email
            )
            assert result.email == email.lower()
    
    def test_email_validation_invalid(self):
        """Test that invalid emails are rejected."""
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user @example.com",
            "user@example"
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValidationError) as exc_info:
                PlaceResult(
                    place_id="test",
                    name="test",
                    email=email
                )
            
            errors = exc_info.value.errors()
            assert any("email" in str(e).lower() for e in errors), \
                f"Failed to reject: {email}"
    
    def test_email_lowercase_normalization(self):
        """Test that emails are normalized to lowercase."""
        result = PlaceResult(
            place_id="test",
            name="test",
            email="USER@EXAMPLE.COM"
        )
        assert result.email == "user@example.com"
    
    def test_latitude_bounds(self):
        """Test latitude boundary validation."""
        # Valid boundaries
        PlaceResult(place_id="test", name="test", latitude=-90.0)
        PlaceResult(place_id="test", name="test", latitude=90.0)
        PlaceResult(place_id="test", name="test", latitude=0.0)
        
        # Invalid boundaries
        with pytest.raises(ValidationError):
            PlaceResult(place_id="test", name="test", latitude=-90.1)
        
        with pytest.raises(ValidationError):
            PlaceResult(place_id="test", name="test", latitude=90.1)
    
    def test_longitude_bounds(self):
        """Test longitude boundary validation."""
        # Valid boundaries
        PlaceResult(place_id="test", name="test", longitude=-180.0)
        PlaceResult(place_id="test", name="test", longitude=180.0)
        PlaceResult(place_id="test", name="test", longitude=0.0)
        
        # Invalid boundaries
        with pytest.raises(ValidationError):
            PlaceResult(place_id="test", name="test", longitude=-180.1)
        
        with pytest.raises(ValidationError):
            PlaceResult(place_id="test", name="test", longitude=180.1)
    
    def test_rating_bounds(self):
        """Test rating boundary validation."""
        # Valid ratings
        PlaceResult(place_id="test", name="test", rating=0.0)
        PlaceResult(place_id="test", name="test", rating=2.5)
        PlaceResult(place_id="test", name="test", rating=5.0)
        
        # Invalid ratings
        with pytest.raises(ValidationError):
            PlaceResult(place_id="test", name="test", rating=-0.1)
        
        with pytest.raises(ValidationError):
            PlaceResult(place_id="test", name="test", rating=5.1)
    
    def test_reviews_count_non_negative(self):
        """Test that reviews count cannot be negative."""
        PlaceResult(place_id="test", name="test", reviews_count=0)
        PlaceResult(place_id="test", name="test", reviews_count=1000)
        
        with pytest.raises(ValidationError):
            PlaceResult(place_id="test", name="test", reviews_count=-1)
    
    def test_price_level_bounds(self):
        """Test price level boundary validation (1-4)."""
        for level in [1, 2, 3, 4]:
            PlaceResult(place_id="test", name="test", price_level=level)
        
        with pytest.raises(ValidationError):
            PlaceResult(place_id="test", name="test", price_level=0)
        
        with pytest.raises(ValidationError):
            PlaceResult(place_id="test", name="test", price_level=5)
    
    def test_quality_score_bounds(self):
        """Test quality score boundary validation (0-100)."""
        PlaceResult(place_id="test", name="test", quality_score=0.0)
        PlaceResult(place_id="test", name="test", quality_score=50.5)
        PlaceResult(place_id="test", name="test", quality_score=100.0)
        
        with pytest.raises(ValidationError):
            PlaceResult(place_id="test", name="test", quality_score=-0.1)
        
        with pytest.raises(ValidationError):
            PlaceResult(place_id="test", name="test", quality_score=100.1)


class TestScrapeResponse:
    """Test suite for ScrapeResponse model."""
    
    def test_minimal_response(self):
        """Test response with minimal fields."""
        response = ScrapeResponse(
            success=True,
            total_results=0
        )
        
        assert response.success is True
        assert response.total_results == 0
        assert response.results == []
        assert response.job_id is None
        assert response.errors == []
    
    def test_full_response(self):
        """Test response with all fields."""
        place = PlaceResult(place_id="test", name="Test Place")
        
        response = ScrapeResponse(
            success=True,
            total_results=1,
            results=[place],
            job_id="job_123",
            status="completed",
            execution_time=45.2,
            pages_scraped=5,
            error=None,
            errors=["Warning: Rate limit approaching"]
        )
        
        assert response.success is True
        assert len(response.results) == 1
        assert response.execution_time == 45.2
        assert len(response.errors) == 1
    
    def test_error_response(self):
        """Test error response structure."""
        response = ScrapeResponse(
            success=False,
            total_results=0,
            error="Authentication failed"
        )
        
        assert response.success is False
        assert response.error == "Authentication failed"
    
    def test_execution_time_non_negative(self):
        """Test that execution time cannot be negative."""
        ScrapeResponse(success=True, total_results=0, execution_time=0.0)
        ScrapeResponse(success=True, total_results=0, execution_time=100.5)
        
        with pytest.raises(ValidationError):
            ScrapeResponse(success=True, total_results=0, execution_time=-1.0)
    
    def test_total_results_non_negative(self):
        """Test that total_results cannot be negative."""
        with pytest.raises(ValidationError):
            ScrapeResponse(success=True, total_results=-1)


class TestBatchScrapeRequest:
    """Test suite for BatchScrapeRequest model."""
    
    def test_valid_batch_request(self):
        """Test valid batch request with multiple queries."""
        request = BatchScrapeRequest(
            queries=["coffee shops", "restaurants", "hotels"]
        )
        
        assert len(request.queries) == 3
        assert request.max_places_per_query == 20  # default
        assert request.language == LanguageCode.EN  # default
    
    def test_single_query_batch(self):
        """Test batch with single query."""
        request = BatchScrapeRequest(queries=["test"])
        assert len(request.queries) == 1
    
    def test_empty_queries_rejected(self):
        """Test that empty query list is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BatchScrapeRequest(queries=[])
        
        errors = exc_info.value.errors()
        assert any("at least 1" in str(e).lower() for e in errors)
    
    def test_too_many_queries_rejected(self):
        """Test that more than 10 queries is rejected."""
        queries = [f"query {i}" for i in range(11)]
        
        with pytest.raises(ValidationError) as exc_info:
            BatchScrapeRequest(queries=queries)
        
        errors = exc_info.value.errors()
        # Pydantic's max_length validation message
        assert any("at most 10" in str(e).lower() or "maximum" in str(e).lower() for e in errors)
    
    def test_max_queries_accepted(self):
        """Test that exactly 10 queries is accepted."""
        queries = [f"query {i}" for i in range(10)]
        request = BatchScrapeRequest(queries=queries)
        assert len(request.queries) == 10
    
    def test_empty_query_in_batch_rejected(self):
        """Test that empty string in query list is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BatchScrapeRequest(queries=["valid query", "", "another query"])
        
        errors = exc_info.value.errors()
        assert any("empty query" in str(e).lower() for e in errors)
    
    def test_query_whitespace_stripped(self):
        """Test that queries are stripped of whitespace."""
        request = BatchScrapeRequest(queries=["  test  ", "  query  "])
        assert request.queries == ["test", "query"]
    
    def test_too_long_query_in_batch_rejected(self):
        """Test that query over 200 chars in batch is rejected."""
        long_query = "a" * 201
        
        with pytest.raises(ValidationError) as exc_info:
            BatchScrapeRequest(queries=["valid", long_query])
        
        errors = exc_info.value.errors()
        assert any("too long" in str(e).lower() for e in errors)
    
    def test_max_places_per_query_bounds(self):
        """Test max_places_per_query boundary validation."""
        # Valid boundaries
        BatchScrapeRequest(queries=["test"], max_places_per_query=1)
        BatchScrapeRequest(queries=["test"], max_places_per_query=100)
        
        # Invalid boundaries
        with pytest.raises(ValidationError):
            BatchScrapeRequest(queries=["test"], max_places_per_query=0)
        
        with pytest.raises(ValidationError):
            BatchScrapeRequest(queries=["test"], max_places_per_query=101)
    
    def test_webhook_url_in_batch(self):
        """Test webhook URL validation in batch requests."""
        # Valid HTTPS
        request = BatchScrapeRequest(
            queries=["test"],
            webhook_url="https://example.com/webhook"
        )
        assert str(request.webhook_url) == "https://example.com/webhook"
        
        # Invalid HTTP
        with pytest.raises(ValidationError):
            BatchScrapeRequest(
                queries=["test"],
                webhook_url="http://insecure.com/webhook"
            )


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_unicode_in_query(self):
        """Test that Unicode characters are supported in queries."""
        unicode_queries = [
            "café in Paris",
            "寿司レストラン",
            "مطاعم في دبي",
            "ресторан в Москве"
        ]
        
        for query in unicode_queries:
            request = ScrapeRequest(query=query)
            assert request.query == query
    
    def test_special_characters_in_query(self):
        """Test that safe special characters are allowed."""
        special_queries = [
            "coffee & tea",
            "100% organic",
            "pizza (takeout)",
            "restaurants near me",
            "#1 burger place"
        ]
        
        for query in special_queries:
            request = ScrapeRequest(query=query)
            assert request.query == query
    
    def test_numeric_query(self):
        """Test that numeric queries work."""
        request = ScrapeRequest(query="90210 zip code")
        assert request.query == "90210 zip code"
    
    def test_model_serialization(self):
        """Test that models can be serialized to JSON."""
        request = ScrapeRequest(
            query="test",
            max_places=50,
            language=LanguageCode.EN
        )
        
        # Should not raise
        json_data = request.model_dump()
        assert json_data["query"] == "test"
        assert json_data["max_places"] == 50
    
    def test_place_result_with_missing_optional_fields(self):
        """Test that place result works with many None values."""
        result = PlaceResult(
            place_id="test",
            name="Minimal Place",
            # All other fields None
        )
        
        json_data = result.model_dump()
        assert json_data["place_id"] == "test"
        assert json_data["address"] is None
        assert json_data["phone"] is None
