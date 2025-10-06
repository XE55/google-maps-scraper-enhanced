"""
Tests for main API endpoints.

Basic integration tests for FastAPI application.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from gmaps_scraper_server.main_api import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestRootEndpoint:
    """Test root endpoint."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns message."""
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()
        assert "API is running" in response.json()["message"]


class TestScrapeEndpoint:
    """Test scrape POST endpoint."""
    
    @patch("gmaps_scraper_server.main_api.scrape_google_maps")
    def test_scrape_with_query(self, mock_scrape, client):
        """Test scrape endpoint with valid query."""
        mock_scrape.return_value = [
            {"name": "Test Place", "address": "123 Main St"}
        ]
        
        response = client.post(
            "/scrape",
            params={"query": "restaurants in NYC"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_scrape_requires_query(self, client):
        """Test scrape requires query parameter."""
        response = client.post("/scrape")
        assert response.status_code == 422  # Missing required parameter
    
    @patch("gmaps_scraper_server.main_api.scrape_google_maps")
    def test_scrape_with_max_places(self, mock_scrape, client):
        """Test scrape with max_places parameter."""
        mock_scrape.return_value = []
        
        response = client.post(
            "/scrape",
            params={"query": "restaurants", "max_places": 10}
        )
        assert response.status_code == 200
    
    @patch("gmaps_scraper_server.main_api.scrape_google_maps")
    def test_scrape_with_lang(self, mock_scrape, client):
        """Test scrape with lang parameter."""
        mock_scrape.return_value = []
        
        response = client.post(
            "/scrape",
            params={"query": "restaurants", "lang": "es"}
        )
        assert response.status_code == 200
    
    @patch("gmaps_scraper_server.main_api.scrape_google_maps")
    def test_scrape_with_headless(self, mock_scrape, client):
        """Test scrape with headless parameter."""
        mock_scrape.return_value = []
        
        response = client.post(
            "/scrape",
            params={"query": "restaurants", "headless": False}
        )
        assert response.status_code == 200
    
    @patch("gmaps_scraper_server.main_api.scrape_google_maps")
    def test_scrape_handles_exception(self, mock_scrape, client):
        """Test scrape handles exceptions."""
        mock_scrape.side_effect = Exception("Test error")
        
        response = client.post(
            "/scrape",
            params={"query": "restaurants"}
        )
        assert response.status_code == 500


class TestScrapeGetEndpoint:
    """Test scrape GET endpoint."""
    
    @patch("gmaps_scraper_server.main_api.scrape_google_maps")
    def test_scrape_get_with_query(self, mock_scrape, client):
        """Test scrape-get endpoint with valid query."""
        mock_scrape.return_value = [
            {"name": "Test Place", "address": "123 Main St"}
        ]
        
        response = client.get(
            "/scrape-get",
            params={"query": "restaurants in NYC"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_scrape_get_requires_query(self, client):
        """Test scrape-get requires query parameter."""
        response = client.get("/scrape-get")
        assert response.status_code == 422  # Missing required parameter
    
    @patch("gmaps_scraper_server.main_api.scrape_google_maps")
    def test_scrape_get_with_all_params(self, mock_scrape, client):
        """Test scrape-get with all parameters."""
        mock_scrape.return_value = []
        
        response = client.get(
            "/scrape-get",
            params={
                "query": "restaurants",
                "max_places": 5,
                "lang": "fr",
                "headless": True
            }
        )
        assert response.status_code == 200


class TestApplicationMetadata:
    """Test application metadata."""
    
    def test_app_creates_successfully(self):
        """Test FastAPI app can be created."""
        assert app is not None
        assert app.title == "Google Maps Scraper API"
    
    def test_app_has_description(self):
        """Test app has description."""
        assert hasattr(app, "description")
        assert "API to trigger" in app.description
    
    def test_app_version(self):
        """Test app version is set."""
        assert hasattr(app, "version")
        assert app.version == "0.1.0"
    
    def test_app_has_routes(self):
        """Test app has expected routes."""
        routes = [route.path for route in app.routes]
        assert "/" in routes
        assert "/scrape" in routes
        assert "/scrape-get" in routes


class TestErrorHandling:
    """Test error handling."""
    
    def test_invalid_endpoint_returns_404(self, client):
        """Test invalid endpoint returns 404."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
    
    def test_invalid_method_on_post_endpoint(self, client):
        """Test invalid method on POST endpoint."""
        response = client.get("/scrape")  # Should be POST
        assert response.status_code == 405  # Method not allowed
    
    @patch("gmaps_scraper_server.main_api.scrape_google_maps")
    def test_import_error_handling(self, mock_scrape, client):
        """Test import error is handled."""
        mock_scrape.side_effect = ImportError("Test import error")
        
        response = client.post(
            "/scrape",
            params={"query": "test"}
        )
        assert response.status_code == 500
        assert "configuration error" in response.json()["detail"].lower()
