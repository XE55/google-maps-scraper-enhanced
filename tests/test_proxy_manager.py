"""
Unit tests for proxy rotation system.

Tests cover:
- Proxy addition and removal
- Rotation strategies (round-robin, random, least-used, best-performance)
- Health checking
- Success/failure recording
- Statistics tracking
- URL parsing
- Concurrent operations
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
import time

from gmaps_scraper_server.proxy_manager import (
    ProxyManager,
    Proxy,
    ProxyStats,
    ProxyProtocol,
    RotationStrategy,
)


class TestProxyCreation:
    """Test suite for proxy creation and configuration."""
    
    def test_add_proxy_http(self):
        """Test adding HTTP proxy."""
        manager = ProxyManager()
        
        proxy = manager.add_proxy("http", "proxy1.com", 8080)
        
        assert len(manager.proxies) == 1
        assert proxy.host == "proxy1.com"
        assert proxy.port == 8080
        assert proxy.protocol == ProxyProtocol.HTTP
    
    def test_add_proxy_with_auth(self):
        """Test adding proxy with authentication."""
        manager = ProxyManager()
        
        proxy = manager.add_proxy("http", "proxy1.com", 8080, "user", "pass")
        
        assert proxy.username == "user"
        assert proxy.password == "pass"
        assert proxy.is_authenticated is True
    
    def test_add_proxy_without_auth(self):
        """Test adding proxy without authentication."""
        manager = ProxyManager()
        
        proxy = manager.add_proxy("http", "proxy1.com", 8080)
        
        assert proxy.username is None
        assert proxy.password is None
        assert proxy.is_authenticated is False
    
    def test_add_multiple_proxies(self):
        """Test adding multiple proxies."""
        manager = ProxyManager()
        
        manager.add_proxy("http", "proxy1.com", 8080)
        manager.add_proxy("http", "proxy2.com", 8080)
        manager.add_proxy("socks5", "proxy3.com", 1080)
        
        assert len(manager.proxies) == 3
    
    def test_add_proxy_invalid_protocol(self):
        """Test that invalid protocol raises error."""
        manager = ProxyManager()
        
        with pytest.raises(ValueError) as exc_info:
            manager.add_proxy("invalid", "proxy.com", 8080)
        
        assert "invalid protocol" in str(exc_info.value).lower()
    
    def test_proxy_url_without_auth(self):
        """Test proxy URL generation without auth."""
        manager = ProxyManager()
        proxy = manager.add_proxy("http", "proxy.com", 8080)
        
        assert proxy.url == "http://proxy.com:8080"
    
    def test_proxy_url_with_auth(self):
        """Test proxy URL generation with auth."""
        manager = ProxyManager()
        proxy = manager.add_proxy("http", "proxy.com", 8080, "user", "pass")
        
        assert proxy.url == "http://user:pass@proxy.com:8080"
    
    def test_add_proxy_from_url_simple(self):
        """Test adding proxy from URL string."""
        manager = ProxyManager()
        
        proxy = manager.add_proxy_from_url("http://proxy.com:8080")
        
        assert proxy.host == "proxy.com"
        assert proxy.port == 8080
        assert proxy.protocol == ProxyProtocol.HTTP
    
    def test_add_proxy_from_url_with_auth(self):
        """Test adding proxy from URL with authentication."""
        manager = ProxyManager()
        
        proxy = manager.add_proxy_from_url("http://user:pass@proxy.com:8080")
        
        assert proxy.host == "proxy.com"
        assert proxy.port == 8080
        assert proxy.username == "user"
        assert proxy.password == "pass"
    
    def test_add_proxy_from_url_invalid_no_protocol(self):
        """Test that URL without protocol raises error."""
        manager = ProxyManager()
        
        with pytest.raises(ValueError) as exc_info:
            manager.add_proxy_from_url("proxy.com:8080")
        
        assert "missing protocol" in str(exc_info.value).lower()
    
    def test_add_proxy_from_url_invalid_no_port(self):
        """Test that URL without port raises error."""
        manager = ProxyManager()
        
        with pytest.raises(ValueError) as exc_info:
            manager.add_proxy_from_url("http://proxy.com")
        
        assert "missing port" in str(exc_info.value).lower()
    
    def test_add_proxy_from_url_invalid_port(self):
        """Test that URL with invalid port raises error."""
        manager = ProxyManager()
        
        with pytest.raises(ValueError) as exc_info:
            manager.add_proxy_from_url("http://proxy.com:abc")
        
        assert "invalid port" in str(exc_info.value).lower()


class TestProxyRemoval:
    """Test suite for proxy removal."""
    
    def test_remove_proxy(self):
        """Test removing a proxy."""
        manager = ProxyManager()
        proxy = manager.add_proxy("http", "proxy.com", 8080)
        
        manager.remove_proxy(proxy)
        
        assert len(manager.proxies) == 0
    
    def test_remove_nonexistent_proxy(self):
        """Test removing proxy that doesn't exist (should not error)."""
        manager = ProxyManager()
        manager.add_proxy("http", "proxy1.com", 8080)
        
        fake_proxy = Proxy("fake.com", 9999, ProxyProtocol.HTTP)
        manager.remove_proxy(fake_proxy)
        
        assert len(manager.proxies) == 1
    
    def test_clear_all_proxies(self):
        """Test clearing all proxies."""
        manager = ProxyManager()
        manager.add_proxy("http", "proxy1.com", 8080)
        manager.add_proxy("http", "proxy2.com", 8080)
        
        manager.clear_proxies()
        
        assert len(manager.proxies) == 0


class TestRotationStrategies:
    """Test suite for proxy rotation strategies."""
    
    @pytest.mark.asyncio
    async def test_round_robin_strategy(self):
        """Test round-robin rotation."""
        manager = ProxyManager(strategy=RotationStrategy.ROUND_ROBIN)
        p1 = manager.add_proxy("http", "proxy1.com", 8080)
        p2 = manager.add_proxy("http", "proxy2.com", 8080)
        p3 = manager.add_proxy("http", "proxy3.com", 8080)
        
        # Get proxies in sequence
        proxies = [await manager.get_proxy() for _ in range(6)]
        
        # Should cycle through proxies in order
        assert proxies[0] == p1
        assert proxies[1] == p2
        assert proxies[2] == p3
        assert proxies[3] == p1  # Cycles back
        assert proxies[4] == p2
        assert proxies[5] == p3
    
    @pytest.mark.asyncio
    async def test_random_strategy(self):
        """Test random rotation."""
        manager = ProxyManager(strategy=RotationStrategy.RANDOM)
        manager.add_proxy("http", "proxy1.com", 8080)
        manager.add_proxy("http", "proxy2.com", 8080)
        manager.add_proxy("http", "proxy3.com", 8080)
        
        # Get many proxies
        proxies = [await manager.get_proxy() for _ in range(30)]
        
        # Should have some variation (not all the same)
        unique_proxies = set(p.host for p in proxies if p)
        assert len(unique_proxies) > 1
    
    @pytest.mark.asyncio
    async def test_least_used_strategy(self):
        """Test least-used rotation."""
        manager = ProxyManager(strategy=RotationStrategy.LEAST_USED)
        p1 = manager.add_proxy("http", "proxy1.com", 8080)
        p2 = manager.add_proxy("http", "proxy2.com", 8080)
        
        # Use p1 once
        p1.stats.total_requests = 1
        
        # Next proxy should be p2 (less used)
        proxy = await manager.get_proxy()
        assert proxy == p2
    
    @pytest.mark.asyncio
    async def test_best_performance_strategy(self):
        """Test best-performance rotation."""
        manager = ProxyManager(strategy=RotationStrategy.BEST_PERFORMANCE)
        p1 = manager.add_proxy("http", "proxy1.com", 8080)
        p2 = manager.add_proxy("http", "proxy2.com", 8080)
        
        # Set different success rates
        p1.stats.total_requests = 10
        p1.stats.successful_requests = 5  # 50% success
        
        p2.stats.total_requests = 10
        p2.stats.successful_requests = 9  # 90% success
        
        # Should pick p2 (better performance)
        proxy = await manager.get_proxy()
        assert proxy == p2
    
    @pytest.mark.asyncio
    async def test_get_proxy_no_healthy_proxies(self):
        """Test get_proxy when no healthy proxies available."""
        manager = ProxyManager()
        p1 = manager.add_proxy("http", "proxy1.com", 8080)
        
        # Mark as unhealthy
        p1.stats.is_healthy = False
        
        proxy = await manager.get_proxy()
        assert proxy is None
    
    @pytest.mark.asyncio
    async def test_get_proxy_empty_pool(self):
        """Test get_proxy with no proxies."""
        manager = ProxyManager()
        
        proxy = await manager.get_proxy()
        assert proxy is None


class TestStatisticsTracking:
    """Test suite for statistics tracking."""
    
    @pytest.mark.asyncio
    async def test_record_success(self):
        """Test recording successful request."""
        manager = ProxyManager()
        proxy = manager.add_proxy("http", "proxy.com", 8080)
        
        await manager.record_success(proxy, response_time=0.5)
        
        assert proxy.stats.total_requests == 1
        assert proxy.stats.successful_requests == 1
        assert proxy.stats.failed_requests == 0
        assert proxy.stats.total_response_time == 0.5
        assert proxy.stats.consecutive_failures == 0
    
    @pytest.mark.asyncio
    async def test_record_multiple_successes(self):
        """Test recording multiple successes."""
        manager = ProxyManager()
        proxy = manager.add_proxy("http", "proxy.com", 8080)
        
        await manager.record_success(proxy, 0.5)
        await manager.record_success(proxy, 0.3)
        await manager.record_success(proxy, 0.7)
        
        assert proxy.stats.total_requests == 3
        assert proxy.stats.successful_requests == 3
        assert proxy.stats.total_response_time == 1.5
    
    @pytest.mark.asyncio
    async def test_record_failure(self):
        """Test recording failed request."""
        manager = ProxyManager()
        proxy = manager.add_proxy("http", "proxy.com", 8080)
        
        await manager.record_failure(proxy, is_ban=False)
        
        assert proxy.stats.total_requests == 1
        assert proxy.stats.successful_requests == 0
        assert proxy.stats.failed_requests == 1
        assert proxy.stats.consecutive_failures == 1
    
    @pytest.mark.asyncio
    async def test_record_failure_with_ban(self):
        """Test recording failure due to ban."""
        manager = ProxyManager()
        proxy = manager.add_proxy("http", "proxy.com", 8080)
        
        await manager.record_failure(proxy, is_ban=True)
        
        assert proxy.stats.ban_count == 1
    
    @pytest.mark.asyncio
    async def test_mark_unhealthy_after_failures(self):
        """Test that proxy is marked unhealthy after consecutive failures."""
        manager = ProxyManager(max_consecutive_failures=3)
        proxy = manager.add_proxy("http", "proxy.com", 8080)
        
        # Record failures
        await manager.record_failure(proxy)
        await manager.record_failure(proxy)
        assert proxy.stats.is_healthy is True  # Still healthy
        
        await manager.record_failure(proxy)
        assert proxy.stats.is_healthy is False  # Now unhealthy
    
    @pytest.mark.asyncio
    async def test_success_resets_consecutive_failures(self):
        """Test that success resets consecutive failure counter."""
        manager = ProxyManager()
        proxy = manager.add_proxy("http", "proxy.com", 8080)
        
        await manager.record_failure(proxy)
        await manager.record_failure(proxy)
        assert proxy.stats.consecutive_failures == 2
        
        await manager.record_success(proxy, 0.5)
        assert proxy.stats.consecutive_failures == 0
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        stats = ProxyStats()
        
        # No requests yet
        assert stats.success_rate == 1.0
        
        # Some successes and failures
        stats.total_requests = 10
        stats.successful_requests = 7
        assert stats.success_rate == 0.7
    
    def test_average_response_time_calculation(self):
        """Test average response time calculation."""
        stats = ProxyStats()
        
        # No requests yet
        assert stats.average_response_time == 0.0
        
        # Some requests
        stats.successful_requests = 4
        stats.total_response_time = 2.0
        assert stats.average_response_time == 0.5


class TestHealthChecking:
    """Test suite for proxy health checking."""
    
    @pytest.mark.asyncio
    async def test_check_proxy_health_success(self):
        """Test health check for working proxy."""
        manager = ProxyManager()
        proxy = manager.add_proxy("http", "proxy.com", 8080)
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await manager.check_proxy_health(proxy)
        
        assert result is True
        assert proxy.stats.is_healthy is True
        assert proxy.stats.consecutive_failures == 0
    
    @pytest.mark.asyncio
    async def test_check_proxy_health_failure(self):
        """Test health check for non-working proxy."""
        manager = ProxyManager()
        proxy = manager.add_proxy("http", "proxy.com", 8080)
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Connection failed")
            )
            
            result = await manager.check_proxy_health(proxy)
        
        assert result is False
        assert proxy.stats.is_healthy is False
    
    @pytest.mark.asyncio
    async def test_check_all_proxies(self):
        """Test checking health of all proxies."""
        manager = ProxyManager()
        manager.add_proxy("http", "proxy1.com", 8080)
        manager.add_proxy("http", "proxy2.com", 8080)
        manager.add_proxy("http", "proxy3.com", 8080)
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            stats = await manager.check_all_proxies()
        
        assert stats["healthy"] == 3
        assert stats["unhealthy"] == 0


class TestAggregateStats:
    """Test suite for aggregate statistics."""
    
    def test_get_stats_empty_pool(self):
        """Test getting stats with no proxies."""
        manager = ProxyManager()
        
        stats = manager.get_stats()
        
        assert stats["total_proxies"] == 0
        assert stats["healthy_proxies"] == 0
        assert stats["total_requests"] == 0
    
    def test_get_stats_with_proxies(self):
        """Test getting aggregate stats."""
        manager = ProxyManager()
        p1 = manager.add_proxy("http", "proxy1.com", 8080)
        p2 = manager.add_proxy("http", "proxy2.com", 8080)
        
        p1.stats.total_requests = 10
        p1.stats.successful_requests = 8
        p1.stats.failed_requests = 2
        
        p2.stats.total_requests = 5
        p2.stats.successful_requests = 4
        p2.stats.failed_requests = 1
        
        stats = manager.get_stats()
        
        assert stats["total_proxies"] == 2
        assert stats["healthy_proxies"] == 2
        assert stats["total_requests"] == 15
        assert stats["successful_requests"] == 12
        assert stats["failed_requests"] == 3
    
    def test_get_proxy_by_host(self):
        """Test finding proxy by hostname."""
        manager = ProxyManager()
        p1 = manager.add_proxy("http", "proxy1.com", 8080)
        manager.add_proxy("http", "proxy2.com", 8080)
        
        found = manager.get_proxy_by_host("proxy1.com")
        
        assert found == p1
    
    def test_get_proxy_by_host_not_found(self):
        """Test finding non-existent proxy."""
        manager = ProxyManager()
        manager.add_proxy("http", "proxy1.com", 8080)
        
        found = manager.get_proxy_by_host("nonexistent.com")
        
        assert found is None
    
    def test_reset_proxy_stats(self):
        """Test resetting proxy statistics."""
        manager = ProxyManager()
        proxy = manager.add_proxy("http", "proxy.com", 8080)
        
        # Set some stats
        proxy.stats.total_requests = 10
        proxy.stats.successful_requests = 5
        
        manager.reset_proxy_stats(proxy)
        
        assert proxy.stats.total_requests == 0
        assert proxy.stats.successful_requests == 0


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_all_proxy_protocols_valid(self):
        """Test that all proxy protocols can be used."""
        manager = ProxyManager()
        
        for protocol in ProxyProtocol:
            proxy = manager.add_proxy(protocol.value, "proxy.com", 8080)
            assert proxy.protocol == protocol
        
        assert len(manager.proxies) == len(ProxyProtocol)
    
    @pytest.mark.asyncio
    async def test_concurrent_get_proxy(self):
        """Test concurrent proxy retrieval."""
        manager = ProxyManager()
        manager.add_proxy("http", "proxy1.com", 8080)
        manager.add_proxy("http", "proxy2.com", 8080)
        
        # Get proxies concurrently
        proxies = await asyncio.gather(*[manager.get_proxy() for _ in range(10)])
        
        # All should be valid proxies
        assert all(p is not None for p in proxies)
    
    @pytest.mark.asyncio
    async def test_concurrent_record_operations(self):
        """Test concurrent success/failure recording."""
        manager = ProxyManager()
        proxy = manager.add_proxy("http", "proxy.com", 8080)
        
        # Record operations concurrently
        await asyncio.gather(
            manager.record_success(proxy, 0.5),
            manager.record_success(proxy, 0.3),
            manager.record_failure(proxy),
            manager.record_success(proxy, 0.7)
        )
        
        # Stats should be consistent
        assert proxy.stats.total_requests == 4
        assert proxy.stats.successful_requests == 3
        assert proxy.stats.failed_requests == 1
    
    def test_proxy_url_special_characters_in_password(self):
        """Test proxy URL with special characters in password."""
        manager = ProxyManager()
        proxy = manager.add_proxy("http", "proxy.com", 8080, "user", "p@ss:w0rd!")
        
        # Should still generate valid URL
        assert "user:p@ss:w0rd!@proxy.com" in proxy.url
    
    def test_add_proxy_from_url_socks5(self):
        """Test adding SOCKS5 proxy from URL."""
        manager = ProxyManager()
        
        proxy = manager.add_proxy_from_url("socks5://proxy.com:1080")
        
        assert proxy.protocol == ProxyProtocol.SOCKS5
        assert proxy.port == 1080
