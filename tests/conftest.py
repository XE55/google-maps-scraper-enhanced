"""Shared test fixtures"""
import pytest
from fastapi.testclient import TestClient
from typing import Generator
import uuid


@pytest.fixture
def test_api_key() -> str:
    """Generate a test API key"""
    return f"test_key_{uuid.uuid4().hex}"


@pytest.fixture
def test_admin_password() -> str:
    """Test admin password"""
    return "test-admin-pass-123"


@pytest.fixture
def sample_place_data() -> dict:
    """Sample Google Maps place data"""
    return {
        "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
        "name": "Test Restaurant",
        "address": "123 Main St, New York, NY 10001",
        "phone": "+1 (555) 123-4567",
        "website": "https://testrestaurant.com",
        "rating": 4.5,
        "reviews_count": 128,
        "link": "https://maps.google.com/?cid=123456789",
    }


@pytest.fixture
def sample_scrape_request() -> dict:
    """Sample scrape request payload"""
    return {
        "query": "restaurants in New York",
        "max_places": 10,
        "lang": "en",
        "headless": True,
    }


@pytest.fixture
def sample_invalid_place_data() -> dict:
    """Sample place data with invalid fields"""
    return {
        "name": "A" * 300,  # Too long
        "phone": "invalid-phone",
        "rating": 6.0,  # Rating > 5
        "reviews_count": -10,  # Negative reviews
    }
