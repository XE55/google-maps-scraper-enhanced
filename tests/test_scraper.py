"""
Comprehensive tests for gmaps_scraper_server.scraper module.
Tests scraping logic with mocked Playwright interactions.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from gmaps_scraper_server.scraper import (
    create_search_url,
    scrape_google_maps,
    BASE_URL,
    DEFAULT_TIMEOUT,
    SCROLL_PAUSE_TIME,
    MAX_SCROLL_ATTEMPTS_WITHOUT_NEW_LINKS
)


class TestCreateSearchUrl:
    """Tests for create_search_url function."""
    
    def test_create_search_url_basic(self):
        """Test creating basic search URL."""
        result = create_search_url("restaurants in NYC")
        assert BASE_URL in result
        assert "restaurants+in+NYC" in result or "restaurants%20in%20NYC" in result
        assert "hl=en" in result
    
    def test_create_search_url_with_lang(self):
        """Test creating URL with custom language."""
        result = create_search_url("cafes", lang="es")
        assert "hl=es" in result
        assert "cafes" in result
    
    def test_create_search_url_special_characters(self):
        """Test URL encoding with special characters."""
        result = create_search_url("café & bar")
        assert "caf" in result.lower()
        assert "bar" in result.lower()
        # Special characters should be URL encoded
        assert " " not in result.split("?")[1]
    
    def test_create_search_url_empty_query(self):
        """Test with empty query."""
        result = create_search_url("")
        assert BASE_URL in result
        assert "q=" in result
    
    def test_create_search_url_unicode(self):
        """Test with unicode characters."""
        result = create_search_url("レストラン")
        assert BASE_URL in result
        assert "q=" in result


class TestScrapeGoogleMaps:
    """Tests for scrape_google_maps async function."""
    
    @pytest.fixture
    def mock_playwright(self):
        """Create mock playwright objects."""
        # Create mock hierarchy
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        # Setup page properties
        mock_page.url = "https://www.google.com/maps/search/test"
        mock_page.content = AsyncMock(return_value="<html>mock content</html>")
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.screenshot = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=1000)
        
        # Setup locator
        mock_locator = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.first = mock_locator
        mock_locator.click = AsyncMock()
        mock_locator.evaluate_all = AsyncMock(return_value=[])
        mock_page.locator = Mock(return_value=mock_locator)
        
        # Setup context and browser
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.is_connected = Mock(return_value=True)
        mock_browser.close = AsyncMock()
        
        # Setup playwright
        mock_chromium = AsyncMock()
        mock_chromium.launch = AsyncMock(return_value=mock_browser)
        
        mock_p = Mock()
        mock_p.chromium = mock_chromium
        
        return {
            'playwright': mock_p,
            'browser': mock_browser,
            'context': mock_context,
            'page': mock_page,
            'locator': mock_locator
        }
    
    @pytest.mark.asyncio
    async def test_scrape_basic_success(self, mock_playwright):
        """Test basic successful scrape."""
        mock_page = mock_playwright['page']
        
        # Mock no consent form
        mock_page.wait_for_selector = AsyncMock(
            side_effect=PlaywrightTimeoutError("No consent")
        )
        
        # Mock finding feed
        async def wait_for_feed(selector, **kwargs):
            if 'role="feed"' in selector:
                return None
            raise PlaywrightTimeoutError("Timeout")
        
        mock_page.wait_for_selector = AsyncMock(side_effect=wait_for_feed)
        
        # Mock scroll behavior - return empty links (no results)
        mock_locator = mock_playwright['locator']
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.evaluate_all = AsyncMock(return_value=[])
        
        with patch('gmaps_scraper_server.scraper.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.__aenter__.return_value = mock_playwright['playwright']
            
            with patch('gmaps_scraper_server.scraper.extractor.extract_place_data', return_value=None):
                result = await scrape_google_maps("test query", max_places=5)
        
        assert isinstance(result, list)
        assert mock_page.goto.called
    
    @pytest.mark.asyncio
    async def test_scrape_single_place_redirect(self, mock_playwright):
        """Test when Google redirects to single place page."""
        mock_page = mock_playwright['page']
        mock_page.url = "https://www.google.com/maps/place/SinglePlace"
        
        # Mock feed timeout (single result)
        mock_page.wait_for_selector = AsyncMock(
            side_effect=PlaywrightTimeoutError("No feed")
        )
        
        # Mock successful extraction
        mock_place_data = {
            "name": "Single Place",
            "address": "123 Main St"
        }
        
        with patch('gmaps_scraper_server.scraper.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.__aenter__.return_value = mock_playwright['playwright']
            
            with patch('gmaps_scraper_server.scraper.extractor.extract_place_data', return_value=mock_place_data):
                result = await scrape_google_maps("specific place")
        
        assert len(result) == 1
        assert result[0]["name"] == "Single Place"
        assert "link" in result[0]
    
    @pytest.mark.asyncio
    async def test_scrape_with_multiple_links(self, mock_playwright):
        """Test scraping multiple place links."""
        mock_page = mock_playwright['page']
        mock_locator = mock_playwright['locator']
        
        # Mock feed exists
        mock_locator.count = AsyncMock(return_value=1)
        
        # Mock place links found
        place_links = [
            "https://maps.google.com/maps/place/place1",
            "https://maps.google.com/maps/place/place2"
        ]
        
        # First call returns links, second returns same (end of scroll)
        mock_locator.evaluate_all = AsyncMock(side_effect=[
            place_links,
            place_links
        ])
        
        # Mock scroll height doesn't change
        mock_page.evaluate = AsyncMock(return_value=1000)
        
        # Mock end marker found
        end_marker_locator = AsyncMock()
        end_marker_locator.count = AsyncMock(return_value=1)
        
        def locator_factory(selector):
            if "end of the list" in selector:
                return end_marker_locator
            return mock_locator
        
        mock_page.locator = Mock(side_effect=locator_factory)
        
        # Mock extraction
        with patch('gmaps_scraper_server.scraper.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.__aenter__.return_value = mock_playwright['playwright']
            
            with patch('gmaps_scraper_server.scraper.extractor.extract_place_data') as mock_extract:
                mock_extract.side_effect = [
                    {"name": "Place 1", "address": "Address 1"},
                    {"name": "Place 2", "address": "Address 2"}
                ]
                
                result = await scrape_google_maps("test", max_places=10)
        
        assert len(result) == 2
        assert result[0]["name"] == "Place 1"
        assert result[1]["name"] == "Place 2"
    
    @pytest.mark.asyncio
    async def test_scrape_respects_max_places(self, mock_playwright):
        """Test that scraping respects max_places limit."""
        mock_page = mock_playwright['page']
        mock_locator = mock_playwright['locator']
        
        # Mock many links
        place_links = [f"https://maps.google.com/maps/place/place{i}" for i in range(10)]
        mock_locator.evaluate_all = AsyncMock(return_value=place_links)
        mock_locator.count = AsyncMock(return_value=1)
        
        with patch('gmaps_scraper_server.scraper.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.__aenter__.return_value = mock_playwright['playwright']
            
            with patch('gmaps_scraper_server.scraper.extractor.extract_place_data') as mock_extract:
                mock_extract.return_value = {"name": "Test Place"}
                
                result = await scrape_google_maps("test", max_places=3)
        
        # Should only process 3 places
        assert len(result) <= 3
    
    @pytest.mark.asyncio
    async def test_scrape_handles_page_timeout(self, mock_playwright):
        """Test handling page navigation timeout."""
        mock_page = mock_playwright['page']
        mock_page.goto = AsyncMock(side_effect=PlaywrightTimeoutError("Navigation timeout"))
        
        with patch('gmaps_scraper_server.scraper.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.__aenter__.return_value = mock_playwright['playwright']
            
            result = await scrape_google_maps("test")
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_scrape_scroll_stops_at_max_attempts(self, mock_playwright):
        """Test scrolling stops after max attempts with no new links."""
        mock_page = mock_playwright['page']
        mock_locator = mock_playwright['locator']
        
        # Mock same links every time (no new links)
        place_links = ["https://maps.google.com/maps/place/place1"]
        mock_locator.evaluate_all = AsyncMock(return_value=place_links)
        mock_locator.count = AsyncMock(return_value=1)
        
        # Scroll height doesn't change
        mock_page.evaluate = AsyncMock(return_value=1000)
        
        # No end marker
        end_marker_locator = AsyncMock()
        end_marker_locator.count = AsyncMock(return_value=0)
        
        def locator_factory(selector):
            if "end of the list" in selector:
                return end_marker_locator
            return mock_locator
        
        mock_page.locator = Mock(side_effect=locator_factory)
        
        with patch('gmaps_scraper_server.scraper.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.__aenter__.return_value = mock_playwright['playwright']
            
            with patch('gmaps_scraper_server.scraper.extractor.extract_place_data', return_value={"name": "Place"}):
                result = await scrape_google_maps("test", max_places=100)
        
        # Should have called evaluate_all multiple times (scrolling)
        assert mock_locator.evaluate_all.call_count >= MAX_SCROLL_ATTEMPTS_WITHOUT_NEW_LINKS
    
    @pytest.mark.asyncio
    async def test_scrape_headless_parameter(self, mock_playwright):
        """Test headless parameter is passed correctly."""
        with patch('gmaps_scraper_server.scraper.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.__aenter__.return_value = mock_playwright['playwright']
            mock_chromium = mock_playwright['playwright'].chromium
            
            with patch('gmaps_scraper_server.scraper.extractor.extract_place_data', return_value=None):
                # Test headless=False
                await scrape_google_maps("test", headless=False)
                mock_chromium.launch.assert_called()
                call_kwargs = mock_chromium.launch.call_args[1]
                assert call_kwargs['headless'] == False
                
                # Reset
                mock_chromium.launch.reset_mock()
                
                # Test headless=True (default)
                await scrape_google_maps("test", headless=True)
                call_kwargs = mock_chromium.launch.call_args[1]
                assert call_kwargs['headless'] == True
    
    @pytest.mark.asyncio
    async def test_scrape_browser_closes_on_error(self, mock_playwright):
        """Test browser closes even when error occurs."""
        mock_browser = mock_playwright['browser']
        mock_page = mock_playwright['page']
        
        # Simulate error during scraping
        mock_page.goto = AsyncMock(side_effect=Exception("Test error"))
        
        with patch('gmaps_scraper_server.scraper.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.__aenter__.return_value = mock_playwright['playwright']
            
            result = await scrape_google_maps("test")
        
        # Browser should be closed in finally block
        assert mock_browser.close.called
    
    @pytest.mark.asyncio
    async def test_scrape_context_creation_with_locale(self, mock_playwright):
        """Test browser context created with correct locale."""
        with patch('gmaps_scraper_server.scraper.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.__aenter__.return_value = mock_playwright['playwright']
            mock_browser = mock_playwright['browser']
            
            with patch('gmaps_scraper_server.scraper.extractor.extract_place_data', return_value=None):
                await scrape_google_maps("test", lang="fr")
            
            # Check context was created with correct locale
            mock_browser.new_context.assert_called()
            call_kwargs = mock_browser.new_context.call_args[1]
            assert call_kwargs['locale'] == "fr"
    
    @pytest.mark.asyncio
    async def test_scrape_handles_new_page_failure(self, mock_playwright):
        """Test handling when new_page returns None."""
        mock_context = mock_playwright['context']
        mock_context.new_page = AsyncMock(return_value=None)
        
        with patch('gmaps_scraper_server.scraper.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.__aenter__.return_value = mock_playwright['playwright']
            
            result = await scrape_google_maps("test")
        
        # Should handle gracefully and return empty list
        assert result == []
    
    @pytest.mark.asyncio
    async def test_scrape_scroll_height_increases(self, mock_playwright):
        """Test scroll continues when height increases."""
        mock_page = mock_playwright['page']
        mock_locator = mock_playwright['locator']
        
        # Mock increasing scroll heights
        scroll_heights = [1000, 1500, 2000, 2000]
        mock_page.evaluate = AsyncMock(side_effect=scroll_heights)
        
        place_links = ["https://maps.google.com/maps/place/place1"]
        mock_locator.evaluate_all = AsyncMock(return_value=place_links)
        mock_locator.count = AsyncMock(return_value=1)
        
        # End marker found on last scroll
        end_marker_locator = AsyncMock()
        end_marker_counts = [0, 0, 1]  # Found on third check
        end_marker_locator.count = AsyncMock(side_effect=end_marker_counts)
        
        def locator_factory(selector):
            if "end of the list" in selector:
                return end_marker_locator
            return mock_locator
        
        mock_page.locator = Mock(side_effect=locator_factory)
        
        with patch('gmaps_scraper_server.scraper.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.__aenter__.return_value = mock_playwright['playwright']
            
            with patch('gmaps_scraper_server.scraper.extractor.extract_place_data', return_value={"name": "Place"}):
                result = await scrape_google_maps("test", max_places=10)
        
        # Should have scrolled multiple times
        assert mock_page.evaluate.call_count >= 3


class TestConstants:
    """Tests for module constants."""
    
    def test_base_url_constant(self):
        """Test BASE_URL is correct."""
        assert BASE_URL == "https://www.google.com/maps/search/"
    
    def test_default_timeout_constant(self):
        """Test DEFAULT_TIMEOUT is reasonable."""
        assert DEFAULT_TIMEOUT == 30000
        assert isinstance(DEFAULT_TIMEOUT, int)
    
    def test_scroll_pause_time_constant(self):
        """Test SCROLL_PAUSE_TIME is reasonable."""
        assert SCROLL_PAUSE_TIME == 1.5
        assert isinstance(SCROLL_PAUSE_TIME, (int, float))
    
    def test_max_scroll_attempts_constant(self):
        """Test MAX_SCROLL_ATTEMPTS_WITHOUT_NEW_LINKS is reasonable."""
        assert MAX_SCROLL_ATTEMPTS_WITHOUT_NEW_LINKS == 5
        assert isinstance(MAX_SCROLL_ATTEMPTS_WITHOUT_NEW_LINKS, int)
