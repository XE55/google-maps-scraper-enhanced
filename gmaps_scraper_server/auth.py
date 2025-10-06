"""
Authentication module with API key management
Provides secure API key generation, validation, and storage
"""
import os
import secrets
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

# In-memory storage (replace with database in production)
_api_keys_store: Dict[str, Dict[str, Any]] = {}


class APIKeyManager:
    """Manage API key generation, validation, and lifecycle"""
    
    def __init__(self, salt: Optional[str] = None):
        """
        Initialize API key manager
        
        Args:
            salt: Secret salt for key hashing (from environment)
        """
        self.salt = salt or os.getenv("API_KEY_SALT", "default-salt-change-me")
    
    def generate_api_key(
        self,
        name: str,
        rate_limit_per_day: int = 1000,
        expires_in_days: Optional[int] = None
    ) -> tuple[str, str]:
        """
        Generate a new API key
        
        Args:
            name: Human-readable name for the key
            rate_limit_per_day: Daily request limit
            expires_in_days: Expiration in days (None = no expiration)
        
        Returns:
            Tuple of (raw_key, key_id)
        """
        # Generate secure random key
        raw_key = f"gmaps_{secrets.token_urlsafe(32)}"
        key_id = str(uuid.uuid4())
        
        # Hash the key for storage
        key_hash = self._hash_api_key(raw_key)
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Store metadata
        _api_keys_store[key_id] = {
            "key_hash": key_hash,
            "name": name,
            "rate_limit_per_day": rate_limit_per_day,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "is_active": True,
            "requests_today": 0,
            "last_used": None,
        }
        
        return raw_key, key_id
    
    def _hash_api_key(self, raw_key: str) -> str:
        """Hash API key with salt"""
        salted = f"{raw_key}{self.salt}".encode()
        return hashlib.sha256(salted).hexdigest()
    
    def validate_api_key(self, raw_key: str) -> Dict[str, Any]:
        """
        Validate API key and return metadata
        
        Args:
            raw_key: The raw API key from request
        
        Returns:
            Key metadata dictionary
        
        Raises:
            HTTPException: If key is invalid, expired, or rate limited
        """
        key_hash = self._hash_api_key(raw_key)
        
        # Find matching key
        key_data = None
        key_id = None
        for kid, data in _api_keys_store.items():
            if data["key_hash"] == key_hash:
                key_data = data
                key_id = kid
                break
        
        if not key_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        # Check if active
        if not key_data.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has been deactivated"
            )
        
        # Check expiration
        if key_data.get("expires_at"):
            if datetime.utcnow() > key_data["expires_at"]:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key has expired"
                )
        
        # Check rate limit
        if key_data["requests_today"] >= key_data["rate_limit_per_day"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Daily rate limit exceeded"
            )
        
        # Update usage
        key_data["requests_today"] += 1
        key_data["last_used"] = datetime.utcnow()
        
        return {
            "key_id": key_id,
            "name": key_data["name"],
            "rate_limit_per_day": key_data["rate_limit_per_day"],
            "requests_today": key_data["requests_today"],
        }
    
    def revoke_api_key(self, key_id: str) -> bool:
        """
        Revoke (deactivate) an API key
        
        Args:
            key_id: The key ID to revoke
        
        Returns:
            True if revoked, False if not found
        """
        if key_id in _api_keys_store:
            _api_keys_store[key_id]["is_active"] = False
            return True
        return False
    
    def list_api_keys(self) -> list[Dict[str, Any]]:
        """List all API keys (without hashes)"""
        return [
            {
                "key_id": key_id,
                "name": data["name"],
                "rate_limit_per_day": data["rate_limit_per_day"],
                "created_at": data["created_at"].isoformat(),
                "expires_at": data["expires_at"].isoformat() if data["expires_at"] else None,
                "is_active": data["is_active"],
                "requests_today": data["requests_today"],
                "last_used": data["last_used"].isoformat() if data["last_used"] else None,
            }
            for key_id, data in _api_keys_store.items()
        ]
    
    def reset_daily_counters(self):
        """Reset daily request counters (call at midnight)"""
        for data in _api_keys_store.values():
            data["requests_today"] = 0


# Global instance
api_key_manager = APIKeyManager()


# FastAPI dependency
async def require_api_key(api_key: str = Security(api_key_header)) -> Dict[str, Any]:
    """
    FastAPI dependency to require and validate API key
    
    Usage:
        @app.get("/endpoint")
        async def endpoint(api_key_data: dict = Depends(require_api_key)):
            ...
    """
    return api_key_manager.validate_api_key(api_key)


# Admin password verification
def verify_admin_password(password: str) -> bool:
    """Verify admin password"""
    admin_pass = os.getenv("ADMIN_PASSWORD", "change-this-immediately")
    return password == admin_pass
