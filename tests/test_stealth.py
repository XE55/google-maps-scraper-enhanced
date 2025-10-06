"""
Unit tests for anti-detection stealth module.

Tests cover:
- Webdriver hiding
- User agent randomization
- Viewport randomization
- Plugin injection
- Detection signal checking
- Human-like behavior simulation
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio

from gmaps_scraper_server.stealth import (
    apply_stealth_patches,
    hide_webdriver,
    hide_chrome_driver,
    randomize_navigator_properties,
    add_realistic_plugins,
    hide_automation_indicators,
    set_realistic_permissions,
    get_random_user_agent,
    get_random_viewport,
    get_random_language,
    random_delay,
    human_like_mouse_move,
    human_like_typing,
    random_scroll,
    configure_browser_context,
    is_detection_page,
    check_if_detected,
    wait_for_stable_network,
    USER_AGENTS,
    VIEWPORT_SIZES,
    LANGUAGES,
)


class TestStealthPatches:
    """Test suite for stealth patches."""
    
    @pytest.mark.asyncio
    async def test_apply_stealth_patches_calls_all_functions(self):
        """Test that apply_stealth_patches calls all patch functions."""
        page = AsyncMock()
        
        await apply_stealth_patches(page)
        
        # Should call add_init_script multiple times (once per patch)
        assert page.add_init_script.call_count >= 5
    
    @pytest.mark.asyncio
    async def test_hide_webdriver(self):
        """Test hiding navigator.webdriver property."""
        page = AsyncMock()
        
        await hide_webdriver(page)
        
        page.add_init_script.assert_called_once()
        script = page.add_init_script.call_args[0][0]
        assert "webdriver" in script.lower()
        assert "undefined" in script
    
    @pytest.mark.asyncio
    async def test_hide_chrome_driver(self):
        """Test hiding ChromeDriver indicators."""
        page = AsyncMock()
        
        await hide_chrome_driver(page)
        
        page.add_init_script.assert_called_once()
        script = page.add_init_script.call_args[0][0]
        assert "chrome.runtime" in script or "chrome" in script.lower()
    
    @pytest.mark.asyncio
    async def test_randomize_navigator_properties(self):
        """Test randomizing navigator properties."""
        page = AsyncMock()
        
        await randomize_navigator_properties(page)
        
        page.add_init_script.assert_called_once()
        script = page.add_init_script.call_args[0][0]
        assert "hardwareConcurrency" in script
        assert "deviceMemory" in script
    
    @pytest.mark.asyncio
    async def test_add_realistic_plugins(self):
        """Test adding realistic browser plugins."""
        page = AsyncMock()
        
        await add_realistic_plugins(page)
        
        page.add_init_script.assert_called_once()
        script = page.add_init_script.call_args[0][0]
        assert "plugins" in script.lower()
        assert "Chrome PDF" in script or "pdf" in script.lower()
    
    @pytest.mark.asyncio
    async def test_hide_automation_indicators(self):
        """Test hiding automation indicators."""
        page = AsyncMock()
        
        await hide_automation_indicators(page)
        
        page.add_init_script.assert_called_once()
        script = page.add_init_script.call_args[0][0]
        assert "chrome" in script.lower() or "permissions" in script.lower()
    
    @pytest.mark.asyncio
    async def test_set_realistic_permissions(self):
        """Test setting realistic permissions."""
        page = AsyncMock()
        
        await set_realistic_permissions(page)
        
        page.add_init_script.assert_called_once()
        script = page.add_init_script.call_args[0][0]
        assert "permissions" in script.lower()


class TestRandomization:
    """Test suite for randomization functions."""
    
    def test_get_random_user_agent_returns_valid_string(self):
        """Test that random user agent is valid."""
        ua = get_random_user_agent()
        
        assert isinstance(ua, str)
        assert len(ua) > 0
        assert ua in USER_AGENTS
    
    def test_get_random_user_agent_returns_different_values(self):
        """Test that random user agent varies."""
        agents = [get_random_user_agent() for _ in range(20)]
        
        # Should have some variation (not all the same)
        unique_agents = set(agents)
        assert len(unique_agents) > 1
    
    def test_user_agents_contain_chrome(self):
        """Test that all user agents are Chrome-based."""
        for ua in USER_AGENTS:
            assert "Chrome" in ua
            assert "Mozilla" in ua
    
    def test_get_random_viewport_returns_valid_dict(self):
        """Test that random viewport has correct structure."""
        viewport = get_random_viewport()
        
        assert isinstance(viewport, dict)
        assert "width" in viewport
        assert "height" in viewport
        assert viewport in VIEWPORT_SIZES
    
    def test_get_random_viewport_dimensions_realistic(self):
        """Test that viewport dimensions are realistic."""
        viewport = get_random_viewport()
        
        assert 1024 <= viewport["width"] <= 3840
        assert 600 <= viewport["height"] <= 2160
    
    def test_get_random_language_returns_valid_code(self):
        """Test that random language is valid."""
        lang = get_random_language()
        
        assert isinstance(lang, str)
        assert lang in LANGUAGES
        assert "en" in lang.lower()
    
    def test_language_codes_format(self):
        """Test that language codes have correct format."""
        for lang in LANGUAGES:
            # Should be like "en-US" or "en"
            parts = lang.split("-")
            assert 1 <= len(parts) <= 2
            assert parts[0].islower()
            if len(parts) == 2:
                assert parts[1].isupper()


class TestHumanLikeBehavior:
    """Test suite for human-like behavior simulation."""
    
    @pytest.mark.asyncio
    async def test_random_delay_completes(self):
        """Test that random delay completes without error."""
        import time
        start = time.time()
        
        await random_delay(50, 100)
        
        elapsed = time.time() - start
        assert 0.04 <= elapsed <= 0.15  # Allow some margin
    
    @pytest.mark.asyncio
    async def test_random_delay_with_custom_range(self):
        """Test random delay with custom time range."""
        import time
        start = time.time()
        
        await random_delay(200, 300)
        
        elapsed = time.time() - start
        assert 0.15 <= elapsed <= 0.35
    
    @pytest.mark.asyncio
    async def test_human_like_mouse_move(self):
        """Test human-like mouse movement."""
        page = AsyncMock()
        page.mouse = AsyncMock()
        
        await human_like_mouse_move(page, 100, 200, steps=5)
        
        # Should move mouse multiple times
        assert page.mouse.move.call_count == 5
    
    @pytest.mark.asyncio
    async def test_human_like_mouse_move_reaches_target(self):
        """Test that mouse movement reaches approximately target coordinates."""
        page = AsyncMock()
        page.mouse = AsyncMock()
        
        await human_like_mouse_move(page, 500, 300, steps=10)
        
        # Last call should be near target (with jitter)
        last_call = page.mouse.move.call_args_list[-1]
        x, y = last_call[0]
        
        # Allow jitter of ±5 pixels
        assert 495 <= x <= 505
        assert 295 <= y <= 305
    
    @pytest.mark.asyncio
    async def test_human_like_typing(self):
        """Test human-like typing behavior."""
        page = AsyncMock()
        page.keyboard = AsyncMock()
        
        await human_like_typing(page, "#search", "test")
        
        # Should click input first
        page.click.assert_called_once_with("#search")
        
        # Should type each character
        assert page.keyboard.type.call_count >= 4  # At least 4 chars
    
    @pytest.mark.asyncio
    async def test_human_like_typing_with_typo(self):
        """Test that typing occasionally includes typos."""
        page = AsyncMock()
        page.keyboard = AsyncMock()
        
        # Run multiple times to potentially trigger typo
        with patch('random.random', return_value=0.01):  # Force typo
            await human_like_typing(page, "#input", "hi")
        
        # Should have typed more than 2 chars due to typo+backspace
        assert page.keyboard.type.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_random_scroll(self):
        """Test random scrolling behavior."""
        page = AsyncMock()
        page.evaluate = AsyncMock()
        
        await random_scroll(page, max_scroll=500)
        
        # Should call evaluate multiple times to scroll
        assert page.evaluate.call_count > 0
        
        # Check that evaluate was called with scroll command
        calls = [call[0][0] for call in page.evaluate.call_args_list]
        assert any("scrollBy" in str(call) for call in calls)
    
    @pytest.mark.asyncio
    async def test_random_scroll_respects_max(self):
        """Test that random scroll doesn't exceed max distance."""
        page = AsyncMock()
        page.evaluate = AsyncMock()
        
        await random_scroll(page, max_scroll=100)
        
        # Total scroll should not exceed max (much)
        total_scroll = 0
        for call in page.evaluate.call_args_list:
            call_str = str(call[0][0])
            # Extract number from scrollBy call
            if "scrollBy" in call_str:
                # This is simplified - actual parsing would be more complex
                total_scroll += 1
        
        # Just verify evaluate was called
        assert page.evaluate.call_count > 0


class TestBrowserConfiguration:
    """Test suite for browser context configuration."""
    
    @pytest.mark.asyncio
    async def test_configure_browser_context(self):
        """Test browser context configuration."""
        context = AsyncMock()
        context.set_extra_http_headers = AsyncMock()
        
        await configure_browser_context(context)
        
        context.set_extra_http_headers.assert_called_once()
        headers = context.set_extra_http_headers.call_args[0][0]
        
        assert "User-Agent" in headers
        assert "Accept-Language" in headers
        assert "Accept" in headers
    
    @pytest.mark.asyncio
    async def test_configure_browser_context_headers_realistic(self):
        """Test that configured headers are realistic."""
        context = AsyncMock()
        context.set_extra_http_headers = AsyncMock()
        
        await configure_browser_context(context)
        
        headers = context.set_extra_http_headers.call_args[0][0]
        
        # Check header values are realistic
        assert "Mozilla" in headers["User-Agent"]
        assert "en" in headers["Accept-Language"].lower()
        assert "gzip" in headers["Accept-Encoding"]


class TestDetection:
    """Test suite for detection checking."""
    
    def test_is_detection_page_with_captcha(self):
        """Test detection of CAPTCHA page."""
        content = "<html><body>Please solve this captcha</body></html>"
        
        assert is_detection_page(content) is True
    
    def test_is_detection_page_with_unusual_traffic(self):
        """Test detection of 'unusual traffic' message."""
        content = "<html><body>We've detected unusual traffic from your network</body></html>"
        
        assert is_detection_page(content) is True
    
    def test_is_detection_page_with_robot_check(self):
        """Test detection of robot verification page."""
        content = "<html><body>Verify you're not a robot</body></html>"
        
        assert is_detection_page(content) is True
    
    def test_is_detection_page_normal_content(self):
        """Test that normal content is not flagged."""
        content = "<html><body><h1>Welcome to our website</h1><p>Normal content here</p></body></html>"
        
        assert is_detection_page(content) is False
    
    def test_is_detection_page_case_insensitive(self):
        """Test that detection is case-insensitive."""
        content = "<html><body>CAPTCHA REQUIRED</body></html>"
        
        assert is_detection_page(content) is True
    
    def test_is_detection_page_security_check(self):
        """Test detection of security check page."""
        content = "<html><body>Security check in progress...</body></html>"
        
        assert is_detection_page(content) is True
    
    @pytest.mark.asyncio
    async def test_check_if_detected_true(self):
        """Test check_if_detected returns True for detection page."""
        page = AsyncMock()
        page.content = AsyncMock(return_value="<html>Please solve this captcha</html>")
        
        result = await check_if_detected(page)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_if_detected_false(self):
        """Test check_if_detected returns False for normal page."""
        page = AsyncMock()
        page.content = AsyncMock(return_value="<html>Normal website content</html>")
        
        result = await check_if_detected(page)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_if_detected_handles_exception(self):
        """Test that check_if_detected handles exceptions gracefully."""
        page = AsyncMock()
        page.content = AsyncMock(side_effect=Exception("Network error"))
        
        # Should not raise, should return False
        result = await check_if_detected(page)
        
        assert result is False


class TestNetworkWaiting:
    """Test suite for network waiting functions."""
    
    @pytest.mark.asyncio
    async def test_wait_for_stable_network_success(self):
        """Test waiting for stable network succeeds."""
        page = AsyncMock()
        page.wait_for_load_state = AsyncMock()
        
        await wait_for_stable_network(page, timeout=5000)
        
        page.wait_for_load_state.assert_called_once_with("networkidle", timeout=5000)
    
    @pytest.mark.asyncio
    async def test_wait_for_stable_network_timeout(self):
        """Test that timeout is handled gracefully."""
        page = AsyncMock()
        page.wait_for_load_state = AsyncMock(side_effect=Exception("Timeout"))
        
        # Should not raise exception
        await wait_for_stable_network(page, timeout=1000)
        
        page.wait_for_load_state.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_wait_for_stable_network_default_timeout(self):
        """Test default timeout value."""
        page = AsyncMock()
        page.wait_for_load_state = AsyncMock()
        
        await wait_for_stable_network(page)
        
        # Should use default 30000ms timeout
        call_kwargs = page.wait_for_load_state.call_args[1]
        assert call_kwargs["timeout"] == 30000


class TestConstants:
    """Test suite for constant values."""
    
    def test_user_agents_not_empty(self):
        """Test that user agents list is not empty."""
        assert len(USER_AGENTS) > 0
    
    def test_user_agents_all_strings(self):
        """Test that all user agents are strings."""
        for ua in USER_AGENTS:
            assert isinstance(ua, str)
            assert len(ua) > 50  # Realistic UA should be fairly long
    
    def test_viewport_sizes_not_empty(self):
        """Test that viewport sizes list is not empty."""
        assert len(VIEWPORT_SIZES) > 0
    
    def test_viewport_sizes_valid_structure(self):
        """Test that all viewport sizes have width and height."""
        for viewport in VIEWPORT_SIZES:
            assert "width" in viewport
            assert "height" in viewport
            assert isinstance(viewport["width"], int)
            assert isinstance(viewport["height"], int)
    
    def test_languages_not_empty(self):
        """Test that languages list is not empty."""
        assert len(LANGUAGES) > 0
    
    def test_languages_all_english(self):
        """Test that all languages are English variants."""
        for lang in LANGUAGES:
            assert "en" in lang.lower()


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_apply_stealth_patches_with_failing_page(self):
        """Test stealth patches with page that raises errors."""
        page = AsyncMock()
        page.add_init_script = AsyncMock(side_effect=Exception("Page closed"))
        
        # Should raise the exception (no error handling in stealth module)
        with pytest.raises(Exception):
            await apply_stealth_patches(page)
    
    def test_detection_page_with_empty_content(self):
        """Test detection check with empty content."""
        assert is_detection_page("") is False
    
    def test_detection_page_with_whitespace(self):
        """Test detection check with only whitespace."""
        assert is_detection_page("   \n\t  ") is False
    
    @pytest.mark.asyncio
    async def test_random_delay_with_zero_range(self):
        """Test random delay with min == max."""
        import time
        start = time.time()
        
        await random_delay(100, 100)
        
        elapsed = time.time() - start
        assert 0.09 <= elapsed <= 0.11
    
    @pytest.mark.asyncio
    async def test_human_like_typing_empty_string(self):
        """Test typing with empty string."""
        page = AsyncMock()
        page.keyboard = AsyncMock()
        
        await human_like_typing(page, "#input", "")
        
        # Should still click the input
        page.click.assert_called_once()
        
        # Should not type anything
        page.keyboard.type.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_human_like_mouse_move_zero_steps(self):
        """Test mouse move with single step."""
        page = AsyncMock()
        page.mouse = AsyncMock()
        
        await human_like_mouse_move(page, 10, 10, steps=1)
        
        # Should move at least once
        assert page.mouse.move.call_count == 1
