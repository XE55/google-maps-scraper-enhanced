"""
Tests for email verification module.

Tests cover:
- Email validation with Rapid Email Verifier API
- Batch email verification
- Place data enrichment
- Mock mode for testing without API
- Domain extraction
"""

import pytest
from gmaps_scraper_server.email_verifier import (
    EmailVerifier,
    EmailValidationResult,
    EmailStatus
)


class TestEmailValidation:
    """Test single email validation."""
    
    @pytest.mark.asyncio
    async def test_validate_valid_email(self):
        """Test validating valid business email."""
        verifier = EmailVerifier(mock_mode=True)
        result = await verifier.validate_email("user@company.com")
        
        assert result.email == "user@company.com"
        assert result.is_valid is True
        assert result.status == EmailStatus.VALID
        assert result.confidence_score > 0
    
    @pytest.mark.asyncio
    async def test_validate_invalid_format(self):
        """Test validating invalid email format."""
        verifier = EmailVerifier(mock_mode=True)
        result = await verifier.validate_email("not-an-email")
        
        assert result.is_valid is False
        assert result.status == EmailStatus.INVALID
        assert result.confidence_score == 0
    
    @pytest.mark.asyncio
    async def test_validate_disposable_email(self):
        """Test validating disposable email."""
        verifier = EmailVerifier(mock_mode=True)
        result = await verifier.validate_email("user@tempmail.com")
        
        assert result.is_disposable is True
        assert result.status == EmailStatus.DISPOSABLE
    
    @pytest.mark.asyncio
    async def test_validate_test_email(self):
        """Test validating test email."""
        verifier = EmailVerifier(mock_mode=True)
        result = await verifier.validate_email("test@example.com")
        
        assert result.is_valid is False
        assert result.is_disposable is True
    
    @pytest.mark.asyncio
    async def test_validate_fake_email(self):
        """Test validating fake email."""
        verifier = EmailVerifier(mock_mode=True)
        result = await verifier.validate_email("fake@example.com")
        
        assert result.is_valid is False
        assert result.is_disposable is True


class TestBatchValidation:
    """Test batch email validation."""
    
    @pytest.mark.asyncio
    async def test_validate_batch_multiple_emails(self):
        """Test validating multiple emails in batch."""
        verifier = EmailVerifier(mock_mode=True)
        emails = [
            "user1@company.com",
            "user2@business.com",
            "user3@example.org"
        ]
        
        results = await verifier.validate_batch(emails)
        
        assert len(results) == 3
        assert all(isinstance(r, EmailValidationResult) for r in results)
        assert all(r.email in emails for r in results)
    
    @pytest.mark.asyncio
    async def test_validate_batch_empty_list(self):
        """Test validating empty email list."""
        verifier = EmailVerifier(mock_mode=True)
        results = await verifier.validate_batch([])
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_validate_batch_mixed_validity(self):
        """Test batch with mix of valid and invalid emails."""
        verifier = EmailVerifier(mock_mode=True)
        emails = [
            "valid@company.com",
            "not-an-email",
            "test@fakeemail.com"
        ]
        
        results = await verifier.validate_batch(emails)
        
        assert len(results) == 3
        assert results[0].is_valid is True  # valid
        assert results[1].is_valid is False  # invalid format
        assert results[2].is_valid is False  # test email


class TestPlaceEnrichment:
    """Test place data enrichment."""
    
    @pytest.mark.asyncio
    async def test_enrich_place_with_email(self):
        """Test enriching place with valid email."""
        verifier = EmailVerifier(mock_mode=True)
        place_data = {
            "name": "Test Business",
            "email": "contact@business.com",
            "phone": "+12015550123"
        }
        
        enriched = await verifier.enrich_place_data(place_data)
        
        assert "email_is_valid" in enriched
        assert "email_is_disposable" in enriched
        assert "email_has_mx_record" in enriched
        assert "email_confidence_score" in enriched
        assert "email_status" in enriched
        assert enriched["email_is_valid"] is True
    
    @pytest.mark.asyncio
    async def test_enrich_place_without_email(self):
        """Test enriching place without email."""
        verifier = EmailVerifier(mock_mode=True)
        place_data = {
            "name": "Test Business",
            "phone": "+12015550123"
        }
        
        enriched = await verifier.enrich_place_data(place_data)
        
        assert "email_is_valid" not in enriched
        assert enriched == place_data
    
    @pytest.mark.asyncio
    async def test_enrich_place_preserves_original_data(self):
        """Test enrichment preserves original fields."""
        verifier = EmailVerifier(mock_mode=True)
        place_data = {
            "name": "Test Business",
            "email": "contact@business.com",
            "phone": "+12015550123",
            "rating": 4.5,
            "address": "123 Main St"
        }
        
        enriched = await verifier.enrich_place_data(place_data)
        
        assert enriched["name"] == "Test Business"
        assert enriched["phone"] == "+12015550123"
        assert enriched["rating"] == 4.5
        assert enriched["address"] == "123 Main St"
    
    @pytest.mark.asyncio
    async def test_enrich_place_with_disposable_email(self):
        """Test enriching place with disposable email."""
        verifier = EmailVerifier(mock_mode=True)
        place_data = {
            "name": "Test Business",
            "email": "user@tempmail.com"
        }
        
        enriched = await verifier.enrich_place_data(place_data)
        
        assert enriched["email_is_disposable"] is True
        assert enriched["email_status"] == "disposable"


class TestBatchEnrichment:
    """Test batch place enrichment."""
    
    @pytest.mark.asyncio
    async def test_enrich_batch_multiple_places(self):
        """Test enriching multiple places in batch."""
        verifier = EmailVerifier(mock_mode=True)
        places = [
            {"name": "Business 1", "email": "contact1@company.com"},
            {"name": "Business 2", "email": "contact2@business.com"}
        ]
        
        enriched = await verifier.enrich_batch(places)
        
        assert len(enriched) == 2
        assert all("email_is_valid" in p for p in enriched)
        assert enriched[0]["name"] == "Business 1"
        assert enriched[1]["name"] == "Business 2"
    
    @pytest.mark.asyncio
    async def test_enrich_batch_without_emails(self):
        """Test enriching places without email fields."""
        verifier = EmailVerifier(mock_mode=True)
        places = [
            {"name": "Business 1", "phone": "+12015550123"},
            {"name": "Business 2", "address": "123 Main St"}
        ]
        
        enriched = await verifier.enrich_batch(places)
        
        assert len(enriched) == 2
        assert enriched == places
    
    @pytest.mark.asyncio
    async def test_enrich_batch_mixed_emails(self):
        """Test enriching batch with some places having emails."""
        verifier = EmailVerifier(mock_mode=True)
        places = [
            {"name": "Business 1", "email": "contact@company.com"},
            {"name": "Business 2", "phone": "+12015550123"}
        ]
        
        enriched = await verifier.enrich_batch(places)
        
        assert len(enriched) == 2
        assert "email_is_valid" in enriched[0]
        assert "email_is_valid" not in enriched[1]


class TestEmailValidationResult:
    """Test EmailValidationResult dataclass."""
    
    def test_create_result(self):
        """Test creating EmailValidationResult."""
        result = EmailValidationResult(
            email="test@example.com",
            is_valid=True,
            is_disposable=False,
            has_mx_record=True
        )
        
        assert result.email == "test@example.com"
        assert result.is_valid is True
        assert result.is_disposable is False
        assert result.has_mx_record is True
    
    def test_status_property_valid(self):
        """Test status property for valid email."""
        result = EmailValidationResult(
            email="test@example.com",
            is_valid=True,
            is_disposable=False,
            has_mx_record=True
        )
        
        assert result.status == EmailStatus.VALID
    
    def test_status_property_invalid(self):
        """Test status property for invalid email."""
        result = EmailValidationResult(
            email="invalid",
            is_valid=False,
            is_disposable=False,
            has_mx_record=False
        )
        
        assert result.status == EmailStatus.INVALID
    
    def test_status_property_disposable(self):
        """Test status property for disposable email."""
        result = EmailValidationResult(
            email="test@tempmail.com",
            is_valid=True,
            is_disposable=True,
            has_mx_record=True
        )
        
        assert result.status == EmailStatus.DISPOSABLE
    
    def test_status_property_no_mx(self):
        """Test status property for email without MX record."""
        result = EmailValidationResult(
            email="test@example.com",
            is_valid=True,
            is_disposable=False,
            has_mx_record=False
        )
        
        assert result.status == EmailStatus.NO_MX_RECORD
    
    def test_confidence_score_perfect(self):
        """Test confidence score for perfect email."""
        result = EmailValidationResult(
            email="test@example.com",
            is_valid=True,
            is_disposable=False,
            has_mx_record=True
        )
        
        assert result.confidence_score == 100
    
    def test_confidence_score_no_mx(self):
        """Test confidence score without MX record."""
        result = EmailValidationResult(
            email="test@example.com",
            is_valid=True,
            is_disposable=False,
            has_mx_record=False
        )
        
        assert result.confidence_score == 70
    
    def test_confidence_score_disposable(self):
        """Test confidence score for disposable email."""
        result = EmailValidationResult(
            email="test@tempmail.com",
            is_valid=True,
            is_disposable=True,
            has_mx_record=True
        )
        
        assert result.confidence_score == 80
    
    def test_confidence_score_invalid(self):
        """Test confidence score for invalid email."""
        result = EmailValidationResult(
            email="invalid",
            is_valid=False,
            is_disposable=False,
            has_mx_record=False
        )
        
        assert result.confidence_score == 0


class TestEmailStatusEnum:
    """Test EmailStatus enum."""
    
    def test_status_values(self):
        """Test all email status values."""
        assert EmailStatus.VALID.value == "valid"
        assert EmailStatus.INVALID.value == "invalid"
        assert EmailStatus.DISPOSABLE.value == "disposable"
        assert EmailStatus.NO_MX_RECORD.value == "no_mx_record"
        assert EmailStatus.UNKNOWN.value == "unknown"


class TestInitialization:
    """Test EmailVerifier initialization."""
    
    def test_init_with_mock_mode(self):
        """Test initialization in mock mode."""
        verifier = EmailVerifier(mock_mode=True)
        assert verifier.mock_mode is True
        assert verifier.base_url == "https://rapid-email-verifier.fly.dev/api"
    
    def test_init_with_custom_api_url(self):
        """Test initialization with custom API URL."""
        verifier = EmailVerifier(api_url="https://custom-api.com/api", mock_mode=True)
        assert verifier.base_url == "https://custom-api.com/api"
    
    def test_init_default_url(self):
        """Test initialization uses default URL."""
        verifier = EmailVerifier(mock_mode=True)
        assert "rapid-email-verifier" in verifier.base_url


class TestDomainExtraction:
    """Test domain extraction from URLs."""
    
    def test_extract_domain_https(self):
        """Test extracting domain from HTTPS URL."""
        verifier = EmailVerifier(mock_mode=True)
        domain = verifier.extract_domain_from_url("https://example.com")
        assert domain == "example.com"
    
    def test_extract_domain_http(self):
        """Test extracting domain from HTTP URL."""
        verifier = EmailVerifier(mock_mode=True)
        domain = verifier.extract_domain_from_url("http://example.com")
        assert domain == "example.com"
    
    def test_extract_domain_with_www(self):
        """Test extracting domain with www."""
        verifier = EmailVerifier(mock_mode=True)
        domain = verifier.extract_domain_from_url("https://www.example.com")
        assert domain == "example.com"
    
    def test_extract_domain_with_path(self):
        """Test extracting domain from URL with path."""
        verifier = EmailVerifier(mock_mode=True)
        domain = verifier.extract_domain_from_url("https://example.com/about/us")
        assert domain == "example.com"
    
    def test_extract_domain_with_port(self):
        """Test extracting domain from URL with port."""
        verifier = EmailVerifier(mock_mode=True)
        domain = verifier.extract_domain_from_url("https://example.com:8080")
        assert domain == "example.com"
    
    def test_extract_domain_complex_url(self):
        """Test extracting domain from complex URL."""
        verifier = EmailVerifier(mock_mode=True)
        domain = verifier.extract_domain_from_url("https://www.example.com:8080/path/to/page?query=1")
        assert domain == "example.com"
    
    def test_extract_domain_empty_url(self):
        """Test extracting domain from empty URL."""
        verifier = EmailVerifier(mock_mode=True)
        domain = verifier.extract_domain_from_url("")
        assert domain is None
    
    def test_extract_domain_none_url(self):
        """Test extracting domain from None URL."""
        verifier = EmailVerifier(mock_mode=True)
        domain = verifier.extract_domain_from_url(None)
        assert domain is None


class TestMockValidation:
    """Test mock validation logic."""
    
    @pytest.mark.asyncio
    async def test_mock_validates_multiple_disposable_domains(self):
        """Test mock recognizes various disposable domains."""
        verifier = EmailVerifier(mock_mode=True)
        
        disposable_emails = [
            "user@tempmail.com",
            "user@throwaway.email",
            "user@guerrillamail.com",
            "user@10minutemail.com",
            "user@mailinator.com"
        ]
        
        for email in disposable_emails:
            result = await verifier.validate_email(email)
            assert result.is_disposable is True
    
    @pytest.mark.asyncio
    async def test_mock_detects_test_keywords(self):
        """Test mock detects test-related keywords."""
        verifier = EmailVerifier(mock_mode=True)
        
        test_emails = [
            "test@example.com",
            "fake@company.com",
            "invalid@business.com",
            "notreal@domain.com"
        ]
        
        for email in test_emails:
            result = await verifier.validate_email(email)
            assert result.is_valid is False
            assert result.is_disposable is True
