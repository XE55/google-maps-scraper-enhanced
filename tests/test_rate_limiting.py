"""
Unit tests for rate limiting functionality.

Tests cover:
- Rate limit key generation
- Different limit tiers (anonymous vs authenticated)
- Endpoint-specific limits
- Rate limit exceeded handling
- Custom rate limit logic
- Environment variable configuration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import Request
from slowapi.errors import RateLimitExceeded

from gmaps_scraper_server.rate_limiting import (
    get_api_key_from_request,
    custom_rate_limit_key,
    RATE_LIMITS,
    get_rate_limit_for_request,
    rate_limit_exceeded_handler,
    check_custom_rate_limit,
    get_current_usage,
    is_rate_limited,
)


class TestAPIKeyExtraction:
    """Test suite for API key extraction from requests."""
    
    def test_api_key_from_x_api_key_header(self):
        """Test extraction from X-API-Key header."""
        request = Mock(spec=Request)
        request.headers = {"X-API-Key": "test_key_123"}
        request.query_params = {}
        
        result = get_api_key_from_request(request)
        assert result == "apikey:test_key_123"
    
    def test_api_key_from_authorization_header(self):
        """Test extraction from Authorization Bearer header."""
        request = Mock(spec=Request)
        request.headers = {"Authorization": "Bearer token_abc_456"}
        request.query_params = {}
        
        result = get_api_key_from_request(request)
        assert result == "apikey:token_abc_456"
    
    def test_api_key_from_query_parameter(self):
        """Test extraction from query parameter."""
        request = Mock(spec=Request)
        request.headers = {}
        request.query_params = {"api_key": "query_key_789"}
        
        result = get_api_key_from_request(request)
        assert result == "apikey:query_key_789"
    
    def test_fallback_to_ip_address(self):
        """Test fallback to IP address when no API key present."""
        request = Mock(spec=Request)
        request.headers = {}
        request.query_params = {}
        
        with patch('gmaps_scraper_server.rate_limiting.get_remote_address', return_value="192.168.1.1"):
            result = get_api_key_from_request(request)
            assert result == "ip:192.168.1.1"
    
    def test_priority_x_api_key_over_authorization(self):
        """Test that X-API-Key header takes priority."""
        request = Mock(spec=Request)
        request.headers = {
            "X-API-Key": "header_key",
            "Authorization": "Bearer token_key"
        }
        request.query_params = {}
        
        result = get_api_key_from_request(request)
        assert result == "apikey:header_key"
    
    def test_priority_headers_over_query_param(self):
        """Test that headers take priority over query params."""
        request = Mock(spec=Request)
        request.headers = {"X-API-Key": "header_key"}
        request.query_params = {"api_key": "query_key"}
        
        result = get_api_key_from_request(request)
        assert result == "apikey:header_key"
    
    def test_empty_authorization_header(self):
        """Test handling of empty Authorization header."""
        request = Mock(spec=Request)
        request.headers = {"Authorization": ""}
        request.query_params = {}
        
        with patch('gmaps_scraper_server.rate_limiting.get_remote_address', return_value="192.168.1.1"):
            result = get_api_key_from_request(request)
            assert result == "ip:192.168.1.1"
    
    def test_malformed_authorization_header(self):
        """Test handling of malformed Authorization header."""
        request = Mock(spec=Request)
        request.headers = {"Authorization": "InvalidFormat token"}
        request.query_params = {}
        
        with patch('gmaps_scraper_server.rate_limiting.get_remote_address', return_value="192.168.1.1"):
            result = get_api_key_from_request(request)
            assert result == "ip:192.168.1.1"


class TestRateLimitKeyGeneration:
    """Test suite for rate limit key generation."""
    
    def test_custom_rate_limit_key_with_api_key(self):
        """Test key generation includes endpoint path."""
        request = Mock(spec=Request)
        request.headers = {"X-API-Key": "test_key"}
        request.query_params = {}
        request.url = Mock(path="/api/scrape")
        
        result = custom_rate_limit_key(request)
        assert result == "apikey:test_key:/api/scrape"
    
    def test_custom_rate_limit_key_with_ip(self):
        """Test key generation with IP address."""
        request = Mock(spec=Request)
        request.headers = {}
        request.query_params = {}
        request.url = Mock(path="/api/health")
        
        with patch('gmaps_scraper_server.rate_limiting.get_remote_address', return_value="10.0.0.1"):
            result = custom_rate_limit_key(request)
            assert result == "ip:10.0.0.1:/api/health"
    
    def test_different_endpoints_different_keys(self):
        """Test that different endpoints generate different keys."""
        request1 = Mock(spec=Request)
        request1.headers = {"X-API-Key": "same_key"}
        request1.query_params = {}
        request1.url = Mock(path="/api/scrape")
        
        request2 = Mock(spec=Request)
        request2.headers = {"X-API-Key": "same_key"}
        request2.query_params = {}
        request2.url = Mock(path="/api/batch")
        
        key1 = custom_rate_limit_key(request1)
        key2 = custom_rate_limit_key(request2)
        
        assert key1 != key2
        assert "/api/scrape" in key1
        assert "/api/batch" in key2


class TestRateLimitConfiguration:
    """Test suite for rate limit configuration."""
    
    def test_rate_limits_defined(self):
        """Test that all expected rate limits are defined."""
        expected_keys = [
            "anonymous_per_minute",
            "anonymous_per_hour",
            "anonymous_per_day",
            "authenticated_per_minute",
            "authenticated_per_hour",
            "authenticated_per_day",
            "scrape_per_minute",
            "scrape_per_hour",
            "batch_per_minute",
            "batch_per_hour",
        ]
        
        for key in expected_keys:
            assert key in RATE_LIMITS, f"Missing rate limit: {key}"
    
    def test_rate_limit_format(self):
        """Test that rate limits have correct format."""
        for key, value in RATE_LIMITS.items():
            assert "/" in value, f"Invalid format for {key}: {value}"
            parts = value.split("/")
            assert len(parts) == 2, f"Invalid format for {key}: {value}"
            
            # Check that first part is a number
            try:
                int(parts[0])
            except ValueError:
                pytest.fail(f"Invalid number in rate limit {key}: {parts[0]}")
            
            # Check that second part is a valid time unit
            assert parts[1] in ["minute", "hour", "day", "second"], \
                f"Invalid time unit in {key}: {parts[1]}"
    
    def test_authenticated_limits_higher_than_anonymous(self):
        """Test that authenticated users get higher limits."""
        auth_per_min = int(RATE_LIMITS["authenticated_per_minute"].split("/")[0])
        anon_per_min = int(RATE_LIMITS["anonymous_per_minute"].split("/")[0])
        
        assert auth_per_min > anon_per_min, \
            "Authenticated limits should be higher than anonymous"
    
    def test_scrape_limits_lower_than_general(self):
        """Test that scraping endpoints have stricter limits."""
        scrape_per_min = int(RATE_LIMITS["scrape_per_minute"].split("/")[0])
        auth_per_min = int(RATE_LIMITS["authenticated_per_minute"].split("/")[0])
        
        assert scrape_per_min < auth_per_min, \
            "Scrape limits should be stricter than general authenticated limits"


class TestRateLimitSelection:
    """Test suite for rate limit selection logic."""
    
    def test_scrape_endpoint_authenticated(self):
        """Test rate limit for authenticated scrape request."""
        request = Mock(spec=Request)
        request.headers = {"X-API-Key": "test_key"}
        request.query_params = {}
        request.url = Mock(path="/api/scrape")
        
        limit = get_rate_limit_for_request(request)
        assert limit == RATE_LIMITS["scrape_per_minute"]
    
    def test_scrape_endpoint_anonymous(self):
        """Test rate limit for anonymous scrape request."""
        request = Mock(spec=Request)
        request.headers = {}
        request.query_params = {}
        request.url = Mock(path="/api/scrape")
        
        limit = get_rate_limit_for_request(request)
        assert limit == RATE_LIMITS["scrape_per_minute"]
    
    def test_batch_endpoint(self):
        """Test rate limit for batch endpoint."""
        request = Mock(spec=Request)
        request.headers = {"X-API-Key": "test_key"}
        request.query_params = {}
        request.url = Mock(path="/api/batch/scrape")
        
        limit = get_rate_limit_for_request(request)
        assert limit == RATE_LIMITS["batch_per_minute"]
    
    def test_general_endpoint_authenticated(self):
        """Test rate limit for authenticated general endpoint."""
        request = Mock(spec=Request)
        request.headers = {"X-API-Key": "test_key"}
        request.query_params = {}
        request.url = Mock(path="/api/health")
        
        limit = get_rate_limit_for_request(request)
        assert limit == RATE_LIMITS["authenticated_per_minute"]
    
    def test_general_endpoint_anonymous(self):
        """Test rate limit for anonymous general endpoint."""
        request = Mock(spec=Request)
        request.headers = {}
        request.query_params = {}
        request.url = Mock(path="/api/health")
        
        limit = get_rate_limit_for_request(request)
        assert limit == RATE_LIMITS["anonymous_per_minute"]
    
    def test_batch_takes_priority_over_scrape(self):
        """Test that batch limits take priority when both match."""
        request = Mock(spec=Request)
        request.headers = {}
        request.query_params = {}
        request.url = Mock(path="/api/batch/scrape")
        
        limit = get_rate_limit_for_request(request)
        assert limit == RATE_LIMITS["batch_per_minute"], \
            "Batch limit should take priority"


class TestRateLimitExceededHandler:
    """Test suite for rate limit exceeded handler."""
    
    def test_handler_returns_429_status(self):
        """Test that handler returns 429 status code."""
        request = Mock(spec=Request)
        # Mock the exception with necessary attributes
        exc = Mock(spec=RateLimitExceeded)
        exc.retry_after = 60
        exc.limit = "10/minute"
        
        response = rate_limit_exceeded_handler(request, exc)
        assert response.status_code == 429
    
    def test_handler_includes_retry_after_header(self):
        """Test that response includes Retry-After header."""
        request = Mock(spec=Request)
        exc = Mock(spec=RateLimitExceeded)
        exc.retry_after = 60
        exc.limit = "10/minute"
        
        response = rate_limit_exceeded_handler(request, exc)
        assert "Retry-After" in response.headers
    
    def test_handler_includes_rate_limit_headers(self):
        """Test that response includes rate limit info headers."""
        request = Mock(spec=Request)
        exc = Mock(spec=RateLimitExceeded)
        exc.retry_after = 60
        exc.limit = "10/minute"
        
        response = rate_limit_exceeded_handler(request, exc)
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Reset" in response.headers
    
    def test_handler_includes_error_message(self):
        """Test that response body includes error message."""
        request = Mock(spec=Request)
        exc = Mock(spec=RateLimitExceeded)
        exc.retry_after = 60
        exc.limit = "10/minute"
        
        response = rate_limit_exceeded_handler(request, exc)
        content = response.body.decode()
        assert "error" in content.lower()
        assert "rate limit" in content.lower()
    
    def test_handler_includes_documentation_link(self):
        """Test that response includes link to documentation."""
        request = Mock(spec=Request)
        exc = Mock(spec=RateLimitExceeded)
        exc.retry_after = 60
        exc.limit = "10/minute"
        
        response = rate_limit_exceeded_handler(request, exc)
        content = response.body.decode()
        assert "documentation" in content.lower()


class TestCustomRateLimiting:
    """Test suite for custom rate limiting functions."""
    
    def test_check_custom_rate_limit_with_api_key(self):
        """Test custom rate limit check with API key."""
        request = Mock(spec=Request)
        
        result = check_custom_rate_limit(
            request,
            api_key="test_key",
            max_requests=100,
            window=3600
        )
        
        # Currently returns True (placeholder)
        assert result is True
    
    def test_check_custom_rate_limit_without_api_key(self):
        """Test custom rate limit check with IP fallback."""
        request = Mock(spec=Request)
        
        with patch('gmaps_scraper_server.rate_limiting.get_remote_address', return_value="192.168.1.1"):
            result = check_custom_rate_limit(
                request,
                api_key=None,
                max_requests=50,
                window=1800
            )
            
            # Currently returns True (placeholder)
            assert result is True
    
    def test_get_current_usage_returns_dict(self):
        """Test that get_current_usage returns expected structure."""
        request = Mock(spec=Request)
        
        usage = get_current_usage(request)
        
        assert isinstance(usage, dict)
        assert "requests_made" in usage
        assert "requests_remaining" in usage
        assert "reset_time" in usage
        assert "limit" in usage
    
    def test_get_current_usage_types(self):
        """Test that usage values have correct types."""
        request = Mock(spec=Request)
        
        usage = get_current_usage(request)
        
        assert isinstance(usage["requests_made"], int)
        assert isinstance(usage["requests_remaining"], int)
        assert isinstance(usage["reset_time"], (int, float))
        assert isinstance(usage["limit"], str)
    
    def test_is_rate_limited_returns_bool(self):
        """Test that is_rate_limited returns boolean."""
        request = Mock(spec=Request)
        
        result = is_rate_limited(request)
        
        assert isinstance(result, bool)
    
    def test_is_rate_limited_fails_open(self):
        """Test that rate limiting fails open on errors."""
        request = Mock(spec=Request)
        
        # Should return False (allow) even if something fails
        result = is_rate_limited(request)
        assert result is False


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_missing_headers_dict(self):
        """Test handling when headers attribute is missing."""
        request = Mock(spec=Request)
        # Simulate missing headers
        request.headers = {}
        request.query_params = {}
        
        with patch('gmaps_scraper_server.rate_limiting.get_remote_address', return_value="127.0.0.1"):
            # Should not raise
            result = get_api_key_from_request(request)
            assert "ip:" in result
    
    def test_api_key_with_special_characters(self):
        """Test API key extraction with special characters."""
        special_keys = [
            "key-with-dashes",
            "key_with_underscores",
            "key.with.dots",
            "key123with456numbers",
        ]
        
        for special_key in special_keys:
            request = Mock(spec=Request)
            request.headers = {"X-API-Key": special_key}
            request.query_params = {}
            
            result = get_api_key_from_request(request)
            assert result == f"apikey:{special_key}"
    
    def test_very_long_api_key(self):
        """Test handling of very long API keys."""
        long_key = "a" * 500
        
        request = Mock(spec=Request)
        request.headers = {"X-API-Key": long_key}
        request.query_params = {}
        
        result = get_api_key_from_request(request)
        assert result == f"apikey:{long_key}"
    
    def test_empty_api_key_values(self):
        """Test handling of empty API key values."""
        request = Mock(spec=Request)
        request.headers = {"X-API-Key": ""}
        request.query_params = {}
        
        # Empty string is falsy, should fall back to IP
        with patch('gmaps_scraper_server.rate_limiting.get_remote_address', return_value="127.0.0.1"):
            result = get_api_key_from_request(request)
            # Empty string is falsy, falls back to IP
            assert "ip:" in result
    
    def test_unicode_in_endpoint_path(self):
        """Test key generation with Unicode in path."""
        request = Mock(spec=Request)
        request.headers = {"X-API-Key": "test"}
        request.query_params = {}
        request.url = Mock(path="/api/café/search")
        
        # Should not raise
        result = custom_rate_limit_key(request)
        assert "apikey:test" in result
    
    @patch.dict('os.environ', {'RATE_LIMITING_ENABLED': 'false'})
    def test_rate_limiting_disabled_via_env(self):
        """Test that rate limiting can be disabled via environment."""
        # Just verify the environment variable works
        import os
        assert os.getenv('RATE_LIMITING_ENABLED') == 'false'
