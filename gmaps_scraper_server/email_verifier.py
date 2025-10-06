"""
Email verification module using Rapid Email Verifier API.

Features:
- Email validation (format, MX records, disposable detection)
- Batch email verification
- Domain validation
- Mock support for testing
- Configurable API endpoint (for self-hosting)

Standards:
- RFC 5322 email validation
- MX record verification
- Disposable email detection
- Comprehensive error handling

API: https://rapid-email-verifier.fly.dev/
"""

import httpx
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum


class EmailStatus(Enum):
    """Email verification status."""
    VALID = "valid"
    INVALID = "invalid"
    DISPOSABLE = "disposable"
    NO_MX_RECORD = "no_mx_record"
    UNKNOWN = "unknown"


@dataclass
class EmailValidationResult:
    """Result from email validation."""
    email: str
    is_valid: bool
    is_disposable: bool
    has_mx_record: bool
    suggestion: Optional[str] = None
    
    @property
    def status(self) -> EmailStatus:
        """Get status enum based on validation results."""
        if not self.is_valid:
            return EmailStatus.INVALID
        if self.is_disposable:
            return EmailStatus.DISPOSABLE
        if not self.has_mx_record:
            return EmailStatus.NO_MX_RECORD
        return EmailStatus.VALID
    
    @property
    def confidence_score(self) -> int:
        """Calculate confidence score (0-100) based on validation."""
        if not self.is_valid:
            return 0  # Invalid emails get 0 score
        
        score = 50  # Base score for valid format
        if self.has_mx_record:
            score += 30
        if not self.is_disposable:
            score += 20
        return score


class EmailVerifier:
    """Email verification using Rapid Email Verifier API."""
    
    def __init__(self, api_url: Optional[str] = None, mock_mode: bool = False):
        """
        Initialize email verifier.
        
        Args:
            api_url: API base URL (default: https://rapid-email-verifier.fly.dev/api)
            mock_mode: Use mock responses for testing
        """
        self.mock_mode = mock_mode
        self.base_url = api_url or "https://rapid-email-verifier.fly.dev/api"
    
    async def validate_email(self, email: str) -> EmailValidationResult:
        """
        Validate a single email address.
        
        Args:
            email: Email address to validate
        
        Returns:
            EmailValidationResult with validation details
        
        Example:
            >>> verifier = EmailVerifier()
            >>> result = await verifier.validate_email("user@example.com")
            >>> print(result.is_valid)
            True
        """
        if self.mock_mode:
            return self._mock_validate_email(email)
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/validate",
                    params={"email": email}
                )
                response.raise_for_status()
                data = response.json()
                
                return EmailValidationResult(
                    email=email,
                    is_valid=data.get("is_valid", False),
                    is_disposable=data.get("is_disposable", False),
                    has_mx_record=data.get("has_mx_record", False),
                    suggestion=data.get("suggestion")
                )
        
        except httpx.HTTPStatusError as e:
            # Return conservative result on API error
            return EmailValidationResult(
                email=email,
                is_valid=False,
                is_disposable=False,
                has_mx_record=False
            )
        
        except Exception:
            # Return conservative result on any error
            return EmailValidationResult(
                email=email,
                is_valid=False,
                is_disposable=False,
                has_mx_record=False
            )
    
    async def validate_batch(self, emails: List[str]) -> List[EmailValidationResult]:
        """
        Validate multiple email addresses in a single request.
        
        Args:
            emails: List of email addresses to validate
        
        Returns:
            List of EmailValidationResult objects
        
        Example:
            >>> verifier = EmailVerifier()
            >>> results = await verifier.validate_batch([
            ...     "user1@example.com",
            ...     "user2@example.com"
            ... ])
            >>> print(len(results))
            2
        """
        if self.mock_mode:
            return [self._mock_validate_email(email) for email in emails]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/validate/batch",
                    json={"emails": emails}
                )
                response.raise_for_status()
                data = response.json()
                
                # Parse batch response
                results = []
                for email_data in data:
                    if isinstance(email_data, dict):
                        results.append(EmailValidationResult(
                            email=email_data.get("email", ""),
                            is_valid=email_data.get("is_valid", False),
                            is_disposable=email_data.get("is_disposable", False),
                            has_mx_record=email_data.get("has_mx_record", False),
                            suggestion=email_data.get("suggestion")
                        ))
                
                return results
        
        except Exception:
            # Return conservative results on error
            return [
                EmailValidationResult(
                    email=email,
                    is_valid=False,
                    is_disposable=False,
                    has_mx_record=False
                )
                for email in emails
            ]
    
    async def enrich_place_data(self, place_data: Dict) -> Dict:
        """
        Enrich place data by validating its email if present.
        
        Args:
            place_data: Dictionary with place information
        
        Returns:
            Enriched place data with email validation results
        
        Example:
            >>> verifier = EmailVerifier()
            >>> place = {
            ...     "name": "Test Business",
            ...     "email": "contact@business.com"
            ... }
            >>> enriched = await verifier.enrich_place_data(place)
            >>> print(enriched["email_is_valid"])
            True
        """
        enriched = place_data.copy()
        
        email = place_data.get("email")
        if not email:
            return enriched
        
        # Validate the email
        result = await self.validate_email(email)
        
        # Add validation metadata
        enriched["email_is_valid"] = result.is_valid
        enriched["email_is_disposable"] = result.is_disposable
        enriched["email_has_mx_record"] = result.has_mx_record
        enriched["email_confidence_score"] = result.confidence_score
        enriched["email_status"] = result.status.value
        
        # Add suggestion if provided
        if result.suggestion:
            enriched["email_suggestion"] = result.suggestion
        
        return enriched
    
    async def enrich_batch(self, places: List[Dict]) -> List[Dict]:
        """
        Enrich multiple places by validating their emails in batch.
        
        Args:
            places: List of place dictionaries with email fields
        
        Returns:
            List of enriched place dictionaries
        
        Example:
            >>> verifier = EmailVerifier()
            >>> places = [
            ...     {"name": "Business 1", "email": "contact1@example.com"},
            ...     {"name": "Business 2", "email": "contact2@example.com"}
            ... ]
            >>> enriched = await verifier.enrich_batch(places)
            >>> print(len(enriched))
            2
        """
        # Extract emails from places
        emails = [place.get("email") for place in places if place.get("email")]
        
        if not emails:
            return places
        
        # Validate all emails in batch
        results = await self.validate_batch(emails)
        
        # Create email -> result mapping
        email_results = {result.email: result for result in results}
        
        # Enrich each place with its validation result
        enriched_places = []
        for place in places:
            enriched = place.copy()
            email = place.get("email")
            
            if email and email in email_results:
                result = email_results[email]
                enriched["email_is_valid"] = result.is_valid
                enriched["email_is_disposable"] = result.is_disposable
                enriched["email_has_mx_record"] = result.has_mx_record
                enriched["email_confidence_score"] = result.confidence_score
                enriched["email_status"] = result.status.value
                
                if result.suggestion:
                    enriched["email_suggestion"] = result.suggestion
            
            enriched_places.append(enriched)
        
        return enriched_places
    
    def _mock_validate_email(self, email: str) -> EmailValidationResult:
        """
        Generate mock validation result for testing.
        
        Args:
            email: Email address to mock validate
        
        Returns:
            Mocked EmailValidationResult
        """
        # Simple heuristics for mock validation
        if "@" not in email or "." not in email.split("@")[-1]:
            # Invalid format
            return EmailValidationResult(
                email=email,
                is_valid=False,
                is_disposable=False,
                has_mx_record=False
            )
        
        # Check for disposable domains
        disposable_domains = [
            "tempmail.com", "throwaway.email", "guerrillamail.com",
            "10minutemail.com", "mailinator.com", "fakeinbox.com"
        ]
        domain = email.split("@")[-1].lower()
        is_disposable = any(d in domain for d in disposable_domains)
        
        # Check for test/fake emails
        if any(word in email.lower() for word in ["test", "fake", "invalid", "notreal"]):
            return EmailValidationResult(
                email=email,
                is_valid=False,
                is_disposable=True,
                has_mx_record=False
            )
        
        # Valid business email
        return EmailValidationResult(
            email=email,
            is_valid=True,
            is_disposable=is_disposable,
            has_mx_record=True,
            suggestion=None
        )
    
    def extract_domain_from_url(self, url: str) -> Optional[str]:
        """
        Extract domain from URL.
        
        Args:
            url: Website URL
        
        Returns:
            Domain name or None if extraction fails
        
        Example:
            >>> verifier = EmailVerifier()
            >>> verifier.extract_domain_from_url("https://www.example.com/about")
            'example.com'
        """
        if not url:
            return None
        
        # Remove protocol
        url = url.replace("http://", "").replace("https://", "")
        
        # Remove path
        url = url.split("/")[0]
        
        # Remove www
        url = url.replace("www.", "")
        
        # Remove port
        url = url.split(":")[0]
        
        return url if url else None
