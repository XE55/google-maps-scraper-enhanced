"""
Unit tests for authentication module
Tests API key generation, validation, expiration, and rate limiting
"""
import pytest
from datetime import datetime, timedelta
from fastapi import HTTPException
from gmaps_scraper_server.auth import APIKeyManager, _api_keys_store


class TestAPIKeyManager:
    """Test suite for APIKeyManager"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Clear API keys before each test"""
        _api_keys_store.clear()
        yield
        _api_keys_store.clear()
    
    @pytest.fixture
    def manager(self):
        """Create APIKeyManager instance"""
        return APIKeyManager(salt="test-salt-123")
    
    def test_generate_api_key_format(self, manager):
        """Test that generated API keys have correct format"""
        raw_key, key_id = manager.generate_api_key("Test Key")
        
        # Key should start with gmaps_
        assert raw_key.startswith("gmaps_")
        
        # Key should be long enough (URL-safe base64)
        assert len(raw_key) > 40
        
        # Key ID should be valid UUID format
        assert len(key_id) == 36
        assert key_id.count("-") == 4
    
    def test_generate_api_key_stores_metadata(self, manager):
        """Test that key metadata is stored correctly"""
        raw_key, key_id = manager.generate_api_key(
            name="Test API Key",
            rate_limit_per_day=500,
            expires_in_days=30
        )
        
        assert key_id in _api_keys_store
        stored_data = _api_keys_store[key_id]
        
        assert stored_data["name"] == "Test API Key"
        assert stored_data["rate_limit_per_day"] == 500
        assert stored_data["is_active"] is True
        assert stored_data["requests_today"] == 0
        assert stored_data["last_used"] is None
        assert stored_data["expires_at"] is not None
    
    def test_generate_api_key_without_expiration(self, manager):
        """Test generating key without expiration"""
        raw_key, key_id = manager.generate_api_key("No Expiry Key")
        
        stored_data = _api_keys_store[key_id]
        assert stored_data["expires_at"] is None
    
    def test_validate_api_key_success(self, manager):
        """Test successful API key validation"""
        raw_key, key_id = manager.generate_api_key("Valid Key")
        
        # Should validate successfully
        result = manager.validate_api_key(raw_key)
        
        assert result["key_id"] == key_id
        assert result["name"] == "Valid Key"
        assert result["requests_today"] == 1
    
    def test_validate_api_key_invalid(self, manager):
        """Test validation of invalid API key"""
        with pytest.raises(HTTPException) as exc_info:
            manager.validate_api_key("invalid_key_123")
        
        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail
    
    def test_validate_api_key_deactivated(self, manager):
        """Test validation of deactivated key"""
        raw_key, key_id = manager.generate_api_key("Deactivated Key")
        _api_keys_store[key_id]["is_active"] = False
        
        with pytest.raises(HTTPException) as exc_info:
            manager.validate_api_key(raw_key)
        
        assert exc_info.value.status_code == 401
        assert "deactivated" in exc_info.value.detail.lower()
    
    def test_validate_api_key_expired(self, manager):
        """Test validation of expired key"""
        raw_key, key_id = manager.generate_api_key("Expired Key", expires_in_days=1)
        
        # Manually set expiration to past
        _api_keys_store[key_id]["expires_at"] = datetime.utcnow() - timedelta(days=1)
        
        with pytest.raises(HTTPException) as exc_info:
            manager.validate_api_key(raw_key)
        
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()
    
    def test_validate_api_key_rate_limit(self, manager):
        """Test rate limiting enforcement"""
        raw_key, key_id = manager.generate_api_key("Limited Key", rate_limit_per_day=3)
        
        # Use key 3 times (should succeed)
        manager.validate_api_key(raw_key)
        manager.validate_api_key(raw_key)
        manager.validate_api_key(raw_key)
        
        # 4th request should fail
        with pytest.raises(HTTPException) as exc_info:
            manager.validate_api_key(raw_key)
        
        assert exc_info.value.status_code == 429
        assert "rate limit" in exc_info.value.detail.lower()
    
    def test_validate_api_key_updates_last_used(self, manager):
        """Test that validation updates last_used timestamp"""
        raw_key, key_id = manager.generate_api_key("Track Usage Key")
        
        before = datetime.utcnow()
        manager.validate_api_key(raw_key)
        after = datetime.utcnow()
        
        last_used = _api_keys_store[key_id]["last_used"]
        assert last_used is not None
        assert before <= last_used <= after
    
    def test_revoke_api_key_success(self, manager):
        """Test successful key revocation"""
        raw_key, key_id = manager.generate_api_key("Revoke Me")
        
        result = manager.revoke_api_key(key_id)
        assert result is True
        assert _api_keys_store[key_id]["is_active"] is False
        
        # Key should no longer validate
        with pytest.raises(HTTPException):
            manager.validate_api_key(raw_key)
    
    def test_revoke_api_key_not_found(self, manager):
        """Test revoking non-existent key"""
        result = manager.revoke_api_key("non-existent-id")
        assert result is False
    
    def test_list_api_keys_empty(self, manager):
        """Test listing keys when none exist"""
        keys = manager.list_api_keys()
        assert keys == []
    
    def test_list_api_keys_multiple(self, manager):
        """Test listing multiple API keys"""
        manager.generate_api_key("Key 1")
        manager.generate_api_key("Key 2", rate_limit_per_day=500)
        manager.generate_api_key("Key 3", expires_in_days=30)
        
        keys = manager.list_api_keys()
        assert len(keys) == 3
        
        # Check that sensitive data (hash) is not exposed
        for key in keys:
            assert "key_hash" not in key
            assert "key_id" in key
            assert "name" in key
            assert "is_active" in key
    
    def test_list_api_keys_format(self, manager):
        """Test format of listed keys"""
        raw_key, key_id = manager.generate_api_key("Format Test", rate_limit_per_day=100)
        
        keys = manager.list_api_keys()
        key_data = keys[0]
        
        # Check all required fields
        assert key_data["key_id"] == key_id
        assert key_data["name"] == "Format Test"
        assert key_data["rate_limit_per_day"] == 100
        assert key_data["is_active"] is True
        assert key_data["requests_today"] == 0
        assert key_data["last_used"] is None
        
        # Timestamps should be ISO format strings
        assert isinstance(key_data["created_at"], str)
        assert "T" in key_data["created_at"]
    
    def test_reset_daily_counters(self, manager):
        """Test resetting daily request counters"""
        raw_key1, key_id1 = manager.generate_api_key("Key 1")
        raw_key2, key_id2 = manager.generate_api_key("Key 2")
        
        # Use keys multiple times
        manager.validate_api_key(raw_key1)
        manager.validate_api_key(raw_key1)
        manager.validate_api_key(raw_key2)
        
        assert _api_keys_store[key_id1]["requests_today"] == 2
        assert _api_keys_store[key_id2]["requests_today"] == 1
        
        # Reset counters
        manager.reset_daily_counters()
        
        assert _api_keys_store[key_id1]["requests_today"] == 0
        assert _api_keys_store[key_id2]["requests_today"] == 0
    
    def test_hash_api_key_consistency(self, manager):
        """Test that same key always produces same hash"""
        test_key = "gmaps_test_key_123"
        
        hash1 = manager._hash_api_key(test_key)
        hash2 = manager._hash_api_key(test_key)
        
        assert hash1 == hash2
    
    def test_hash_api_key_different_keys(self, manager):
        """Test that different keys produce different hashes"""
        hash1 = manager._hash_api_key("gmaps_key1")
        hash2 = manager._hash_api_key("gmaps_key2")
        
        assert hash1 != hash2
    
    def test_hash_api_key_uses_salt(self):
        """Test that salt affects hash output"""
        manager1 = APIKeyManager(salt="salt1")
        manager2 = APIKeyManager(salt="salt2")
        
        same_key = "gmaps_test_key"
        hash1 = manager1._hash_api_key(same_key)
        hash2 = manager2._hash_api_key(same_key)
        
        assert hash1 != hash2
    
    def test_concurrent_key_generation(self, manager):
        """Test generating multiple keys doesn't conflict"""
        keys = []
        for i in range(10):
            raw_key, key_id = manager.generate_api_key(f"Key {i}")
            keys.append((raw_key, key_id))
        
        # All keys should be unique
        raw_keys = [k[0] for k in keys]
        key_ids = [k[1] for k in keys]
        
        assert len(set(raw_keys)) == 10
        assert len(set(key_ids)) == 10
    
    def test_validate_increments_counter_atomically(self, manager):
        """Test that request counter increments correctly"""
        raw_key, key_id = manager.generate_api_key("Counter Test")
        
        for i in range(1, 6):
            result = manager.validate_api_key(raw_key)
            assert result["requests_today"] == i
            assert _api_keys_store[key_id]["requests_today"] == i


class TestAPIKeyEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Clear API keys before each test"""
        _api_keys_store.clear()
        yield
        _api_keys_store.clear()
    
    @pytest.fixture
    def manager(self):
        return APIKeyManager(salt="test-salt")
    
    def test_empty_key_name(self, manager):
        """Test generating key with empty name"""
        raw_key, key_id = manager.generate_api_key("")
        assert key_id in _api_keys_store
        assert _api_keys_store[key_id]["name"] == ""
    
    def test_very_long_key_name(self, manager):
        """Test generating key with very long name"""
        long_name = "X" * 1000
        raw_key, key_id = manager.generate_api_key(long_name)
        assert _api_keys_store[key_id]["name"] == long_name
    
    def test_zero_rate_limit(self, manager):
        """Test key with zero rate limit"""
        raw_key, key_id = manager.generate_api_key("Zero Limit", rate_limit_per_day=0)
        
        # Should immediately hit limit
        with pytest.raises(HTTPException) as exc_info:
            manager.validate_api_key(raw_key)
        
        assert exc_info.value.status_code == 429
    
    def test_negative_expiration_days(self, manager):
        """Test key with negative expiration (already expired)"""
        raw_key, key_id = manager.generate_api_key("Pre-expired", expires_in_days=-1)
        
        # Key should be expired immediately
        with pytest.raises(HTTPException) as exc_info:
            manager.validate_api_key(raw_key)
        
        assert exc_info.value.status_code == 401
    
    def test_validate_empty_string(self, manager):
        """Test validating empty string as key"""
        with pytest.raises(HTTPException) as exc_info:
            manager.validate_api_key("")
        
        assert exc_info.value.status_code == 401
    
    def test_validate_whitespace_key(self, manager):
        """Test validating whitespace as key"""
        with pytest.raises(HTTPException) as exc_info:
            manager.validate_api_key("   ")
        
        assert exc_info.value.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=gmaps_scraper_server.auth", "--cov-report=term-missing"])
