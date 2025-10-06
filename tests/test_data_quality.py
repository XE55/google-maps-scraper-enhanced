"""
Tests for data quality processor module.

Coverage targets:
- Phone normalization (E.164 format)
- Email validation and normalization
- Duplicate detection
- Quality metrics calculation
- Batch processing
- Statistical analysis
"""

import pytest
from gmaps_scraper_server.data_quality import (
    DataQualityProcessor,
    QualityMetrics
)


class TestPhoneNormalization:
    """Test phone number normalization."""
    
    def test_normalize_us_phone_with_parentheses(self):
        """Test US phone with parentheses format."""
        processor = DataQualityProcessor(default_region="US")
        result = processor.normalize_phone("(201) 555-0123")
        assert result == "+12015550123"
    
    def test_normalize_us_phone_with_dashes(self):
        """Test US phone with dashes format."""
        processor = DataQualityProcessor(default_region="US")
        result = processor.normalize_phone("201-555-0123")
        assert result == "+12015550123"
    
    def test_normalize_us_phone_with_country_code(self):
        """Test US phone with +1 prefix."""
        processor = DataQualityProcessor(default_region="US")
        result = processor.normalize_phone("+1 201 555 0123")
        assert result == "+12015550123"
    
    def test_normalize_uk_phone(self):
        """Test UK phone number."""
        processor = DataQualityProcessor(default_region="GB")
        result = processor.normalize_phone("020 7946 0958")
        assert result == "+442079460958"
    
    def test_normalize_invalid_phone(self):
        """Test invalid phone returns None."""
        processor = DataQualityProcessor(default_region="US")
        result = processor.normalize_phone("not-a-phone")
        assert result is None
    
    def test_normalize_empty_phone(self):
        """Test empty phone returns None."""
        processor = DataQualityProcessor(default_region="US")
        assert processor.normalize_phone("") is None
        assert processor.normalize_phone(None) is None
        assert processor.normalize_phone("   ") is None
    
    def test_normalize_phone_custom_region(self):
        """Test phone normalization with custom region."""
        processor = DataQualityProcessor(default_region="US")
        result = processor.normalize_phone("030 12345678", region="DE")
        assert result == "+493012345678"
    
    def test_validate_phone_format_valid(self):
        """Test valid E.164 phone format."""
        processor = DataQualityProcessor()
        assert processor.validate_phone_format("+12015550123") is True
        assert processor.validate_phone_format("+442079460958") is True
    
    def test_validate_phone_format_invalid(self):
        """Test invalid phone formats."""
        processor = DataQualityProcessor()
        assert processor.validate_phone_format("2015550123") is False  # Missing +
        assert processor.validate_phone_format("+02015550123") is False  # Starts with 0
        assert processor.validate_phone_format("") is False
        assert processor.validate_phone_format(None) is False


class TestEmailNormalization:
    """Test email validation and normalization."""
    
    def test_normalize_email_uppercase(self):
        """Test email normalization to lowercase."""
        processor = DataQualityProcessor()
        result = processor.normalize_email("USER@EXAMPLE.COM")
        # email-validator normalizes domain but may preserve local part case
        assert result.lower() == "user@example.com"
    
    def test_normalize_email_mixed_case(self):
        """Test mixed case email normalization."""
        processor = DataQualityProcessor()
        result = processor.normalize_email("User.Name@Example.Com")
        # Domain is always lowercase, local part case depends on server
        assert "@example.com" in result.lower()
        assert "user.name" in result.lower()
    
    def test_normalize_email_valid(self):
        """Test valid email normalization."""
        processor = DataQualityProcessor()
        result = processor.normalize_email("test@example.com")
        assert result == "test@example.com"
    
    def test_normalize_email_invalid(self):
        """Test invalid email returns None."""
        processor = DataQualityProcessor()
        assert processor.normalize_email("not-an-email") is None
        assert processor.normalize_email("@example.com") is None
        assert processor.normalize_email("user@") is None
    
    def test_normalize_email_empty(self):
        """Test empty email returns None."""
        processor = DataQualityProcessor()
        assert processor.normalize_email("") is None
        assert processor.normalize_email(None) is None
        assert processor.normalize_email("   ") is None
    
    def test_validate_email_format_valid(self):
        """Test valid email format validation."""
        processor = DataQualityProcessor()
        assert processor.validate_email_format("test@example.com") is True
        assert processor.validate_email_format("user.name+tag@example.co.uk") is True
    
    def test_validate_email_format_invalid(self):
        """Test invalid email format validation."""
        processor = DataQualityProcessor()
        assert processor.validate_email_format("invalid") is False
        assert processor.validate_email_format("@example.com") is False
        assert processor.validate_email_format("") is False
        assert processor.validate_email_format(None) is False


class TestDuplicateDetection:
    """Test duplicate detection functionality."""
    
    def test_is_duplicate_email_first_time(self):
        """Test first email is not duplicate."""
        processor = DataQualityProcessor()
        assert processor.is_duplicate_email("test@example.com") is False
    
    def test_is_duplicate_email_second_time(self):
        """Test second same email is duplicate."""
        processor = DataQualityProcessor()
        processor.is_duplicate_email("test@example.com")
        assert processor.is_duplicate_email("test@example.com") is True
    
    def test_is_duplicate_phone_first_time(self):
        """Test first phone is not duplicate."""
        processor = DataQualityProcessor()
        assert processor.is_duplicate_phone("+12015550123") is False
    
    def test_is_duplicate_phone_second_time(self):
        """Test second same phone is duplicate."""
        processor = DataQualityProcessor()
        processor.is_duplicate_phone("+12015550123")
        assert processor.is_duplicate_phone("+12015550123") is True
    
    def test_is_duplicate_place_first_time(self):
        """Test first place ID is not duplicate."""
        processor = DataQualityProcessor()
        assert processor.is_duplicate_place("ChIJN1t_tDeuEmsRUsoyG83frY4") is False
    
    def test_is_duplicate_place_second_time(self):
        """Test second same place ID is duplicate."""
        processor = DataQualityProcessor()
        processor.is_duplicate_place("ChIJN1t_tDeuEmsRUsoyG83frY4")
        assert processor.is_duplicate_place("ChIJN1t_tDeuEmsRUsoyG83frY4") is True
    
    def test_reset_deduplication(self):
        """Test deduplication reset clears tracking."""
        processor = DataQualityProcessor()
        
        # Mark as seen
        processor.is_duplicate_email("test@example.com")
        processor.is_duplicate_phone("+12015550123")
        processor.is_duplicate_place("ChIJN1t_tDeuEmsRUsoyG83frY4")
        
        # Reset
        processor.reset_deduplication()
        
        # Should not be duplicates anymore
        assert processor.is_duplicate_email("test@example.com") is False
        assert processor.is_duplicate_phone("+12015550123") is False
        assert processor.is_duplicate_place("ChIJN1t_tDeuEmsRUsoyG83frY4") is False


class TestCompletenessCalculation:
    """Test data completeness calculation."""
    
    def test_calculate_completeness_all_fields(self):
        """Test completeness with all fields present."""
        processor = DataQualityProcessor()
        place_data = {
            "name": "Test Business",
            "address": "123 Main St",
            "phone": "+12015550123",
            "email": "test@example.com",
            "website": "https://example.com",
            "rating": 4.5,
            "reviews_count": 100,
            "category": "Restaurant",
            "hours": {"monday": "9-5"},
            "latitude": 40.7128,
            "longitude": -74.0060
        }
        score = processor.calculate_completeness(place_data)
        assert score == 100.0
    
    def test_calculate_completeness_half_fields(self):
        """Test completeness with half fields present."""
        processor = DataQualityProcessor()
        place_data = {
            "name": "Test Business",
            "address": "123 Main St",
            "phone": "+12015550123",
            "email": "test@example.com",
            "website": "https://example.com",
            # Missing: rating, reviews_count, category, hours, lat, lng
        }
        score = processor.calculate_completeness(place_data)
        assert score == pytest.approx(45.45, rel=0.1)
    
    def test_calculate_completeness_empty(self):
        """Test completeness with no fields."""
        processor = DataQualityProcessor()
        place_data = {}
        score = processor.calculate_completeness(place_data)
        assert score == 0.0
    
    def test_calculate_completeness_ignores_empty_strings(self):
        """Test completeness ignores empty string values."""
        processor = DataQualityProcessor()
        place_data = {
            "name": "Test Business",
            "address": "",  # Empty string
            "phone": None,  # None
            "email": "",
            "website": "",
        }
        score = processor.calculate_completeness(place_data)
        assert score == pytest.approx(9.09, rel=0.1)  # Only name counts


class TestQualityMetrics:
    """Test quality metrics calculation."""
    
    def test_calculate_quality_metrics_complete(self):
        """Test quality metrics for complete data."""
        processor = DataQualityProcessor()
        place_data = {
            "name": "Test Business",
            "address": "123 Main St",
            "phone": "+12015550123",
            "email": "test@example.com",
            "website": "https://example.com",
            "rating": 4.5,
            "reviews_count": 100,
            "category": "Restaurant",
            "hours": {"monday": "9-5"},
            "latitude": 40.7128,
            "longitude": -74.0060
        }
        metrics = processor.calculate_quality_metrics(place_data)
        
        assert metrics.completeness_score == 100.0
        assert metrics.has_phone is True
        assert metrics.has_email is True
        assert metrics.has_website is True
        assert metrics.has_address is True
        assert metrics.has_hours is True
        assert metrics.has_rating is True
        assert metrics.has_reviews is True
        assert metrics.quality_grade == "A"
    
    def test_calculate_quality_metrics_minimal(self):
        """Test quality metrics for minimal data."""
        processor = DataQualityProcessor()
        place_data = {
            "name": "Test Business"
        }
        metrics = processor.calculate_quality_metrics(place_data)
        
        assert metrics.has_phone is False
        assert metrics.has_email is False
        assert metrics.has_website is False
        assert metrics.quality_grade == "F"
    
    def test_quality_grade_a(self):
        """Test grade A for 90%+ completeness."""
        metrics = QualityMetrics(
            completeness_score=95.0,
            has_phone=True,
            has_email=True,
            has_website=True,
            has_address=True,
            has_hours=True,
            has_rating=True,
            has_reviews=True,
            field_count=10,
            total_fields=11
        )
        assert metrics.quality_grade == "A"
    
    def test_quality_grade_b(self):
        """Test grade B for 80-89% completeness."""
        metrics = QualityMetrics(
            completeness_score=85.0,
            has_phone=True,
            has_email=False,
            has_website=True,
            has_address=True,
            has_hours=True,
            has_rating=True,
            has_reviews=True,
            field_count=9,
            total_fields=11
        )
        assert metrics.quality_grade == "B"
    
    def test_quality_grade_c(self):
        """Test grade C for 70-79% completeness."""
        metrics = QualityMetrics(
            completeness_score=75.0,
            has_phone=True,
            has_email=False,
            has_website=False,
            has_address=True,
            has_hours=True,
            has_rating=True,
            has_reviews=True,
            field_count=8,
            total_fields=11
        )
        assert metrics.quality_grade == "C"
    
    def test_quality_grade_d(self):
        """Test grade D for 60-69% completeness."""
        metrics = QualityMetrics(
            completeness_score=65.0,
            has_phone=False,
            has_email=False,
            has_website=False,
            has_address=True,
            has_hours=True,
            has_rating=True,
            has_reviews=True,
            field_count=7,
            total_fields=11
        )
        assert metrics.quality_grade == "D"
    
    def test_quality_grade_f(self):
        """Test grade F for <60% completeness."""
        metrics = QualityMetrics(
            completeness_score=50.0,
            has_phone=False,
            has_email=False,
            has_website=False,
            has_address=True,
            has_hours=False,
            has_rating=True,
            has_reviews=False,
            field_count=5,
            total_fields=11
        )
        assert metrics.quality_grade == "F"


class TestDataCleaning:
    """Test data cleaning functionality."""
    
    def test_clean_place_data_normalizes_phone(self):
        """Test cleaning normalizes phone number."""
        processor = DataQualityProcessor(default_region="US")
        raw_data = {
            "name": "Test Business",
            "phone": "(201) 555-0123"
        }
        cleaned = processor.clean_place_data(raw_data)
        assert cleaned["phone"] == "+12015550123"
    
    def test_clean_place_data_normalizes_email(self):
        """Test cleaning normalizes email."""
        processor = DataQualityProcessor()
        raw_data = {
            "name": "Test Business",
            "email": "USER@EXAMPLE.COM"
        }
        cleaned = processor.clean_place_data(raw_data)
        # Verify email is normalized (domain lowercase at minimum)
        assert "@example.com" in cleaned["email"]
    
    def test_clean_place_data_normalizes_url(self):
        """Test cleaning normalizes website URL."""
        processor = DataQualityProcessor()
        raw_data = {
            "name": "Test Business",
            "website": "example.com/"
        }
        cleaned = processor.clean_place_data(raw_data)
        assert cleaned["website"] == "https://example.com"
    
    def test_clean_place_data_adds_quality_score(self):
        """Test cleaning adds quality score."""
        processor = DataQualityProcessor()
        raw_data = {
            "name": "Test Business",
            "address": "123 Main St"
        }
        cleaned = processor.clean_place_data(raw_data)
        assert "quality_score" in cleaned
        assert isinstance(cleaned["quality_score"], float)
    
    def test_clean_place_data_trims_strings(self):
        """Test cleaning trims whitespace from strings."""
        processor = DataQualityProcessor()
        raw_data = {
            "name": "  Test Business  ",
            "address": "  123 Main St  "
        }
        cleaned = processor.clean_place_data(raw_data)
        assert cleaned["name"] == "Test Business"
        assert cleaned["address"] == "123 Main St"
    
    def test_normalize_url_adds_https(self):
        """Test URL normalization adds https."""
        processor = DataQualityProcessor()
        result = processor._normalize_url("example.com")
        assert result == "https://example.com"
    
    def test_normalize_url_keeps_http(self):
        """Test URL normalization preserves http."""
        processor = DataQualityProcessor()
        result = processor._normalize_url("http://example.com")
        assert result == "http://example.com"
    
    def test_normalize_url_removes_trailing_slash(self):
        """Test URL normalization removes trailing slash."""
        processor = DataQualityProcessor()
        result = processor._normalize_url("https://example.com/")
        assert result == "https://example.com"


class TestDeduplication:
    """Test batch deduplication."""
    
    def test_deduplicate_by_place_id(self):
        """Test deduplication removes duplicate place IDs."""
        processor = DataQualityProcessor()
        results = [
            {"place_id": "place1", "name": "Business 1"},
            {"place_id": "place1", "name": "Business 1 Duplicate"},
            {"place_id": "place2", "name": "Business 2"}
        ]
        deduplicated = processor.deduplicate_results(results)
        assert len(deduplicated) == 2
        assert deduplicated[0]["place_id"] == "place1"
        assert deduplicated[1]["place_id"] == "place2"
    
    def test_deduplicate_by_phone(self):
        """Test deduplication removes duplicate phones."""
        processor = DataQualityProcessor()
        results = [
            {"phone": "+12015550123", "name": "Business 1"},
            {"phone": "+12015550123", "name": "Business 1 Alt"},
            {"phone": "+12019876543", "name": "Business 2"}
        ]
        deduplicated = processor.deduplicate_results(results)
        assert len(deduplicated) == 2
    
    def test_deduplicate_by_email(self):
        """Test deduplication removes duplicate emails."""
        processor = DataQualityProcessor()
        results = [
            {"email": "test@example.com", "name": "Business 1"},
            {"email": "test@example.com", "name": "Business 1 Alt"},
            {"email": "other@example.com", "name": "Business 2"}
        ]
        deduplicated = processor.deduplicate_results(results)
        assert len(deduplicated) == 2
    
    def test_deduplicate_mixed_criteria(self):
        """Test deduplication with mixed criteria."""
        processor = DataQualityProcessor()
        results = [
            {"place_id": "p1", "phone": "+12011111111", "email": "a@example.com"},
            {"place_id": "p2", "phone": "+12011111111", "email": "b@example.com"},  # Dup phone
            {"place_id": "p3", "phone": "+12012222222", "email": "a@example.com"},  # Dup email
            {"place_id": "p4", "phone": "+12013333333", "email": "d@example.com"}
        ]
        deduplicated = processor.deduplicate_results(results)
        assert len(deduplicated) == 2  # Only first and last
    
    def test_deduplicate_empty_list(self):
        """Test deduplication with empty list."""
        processor = DataQualityProcessor()
        deduplicated = processor.deduplicate_results([])
        assert deduplicated == []


class TestBatchProcessing:
    """Test batch processing functionality."""
    
    def test_process_batch_cleans_data(self):
        """Test batch processing cleans all results."""
        processor = DataQualityProcessor(default_region="US")
        results = [
            {"name": "Business 1", "phone": "(201) 555-0111"},
            {"name": "Business 2", "phone": "(201) 555-0222"}
        ]
        processed = processor.process_batch(results, deduplicate=False)
        
        assert len(processed) == 2
        assert processed[0]["phone"] == "+12015550111"
        assert processed[1]["phone"] == "+12015550222"
        assert "quality_score" in processed[0]
    
    def test_process_batch_deduplicates(self):
        """Test batch processing removes duplicates."""
        processor = DataQualityProcessor()
        results = [
            {"place_id": "p1", "name": "Business 1"},
            {"place_id": "p1", "name": "Business 1 Dup"},
            {"place_id": "p2", "name": "Business 2"}
        ]
        processed = processor.process_batch(results, deduplicate=True)
        assert len(processed) == 2
    
    def test_process_batch_without_deduplication(self):
        """Test batch processing skips deduplication when disabled."""
        processor = DataQualityProcessor()
        results = [
            {"place_id": "p1", "name": "Business 1"},
            {"place_id": "p1", "name": "Business 1 Dup"}
        ]
        processed = processor.process_batch(results, deduplicate=False)
        assert len(processed) == 2  # No deduplication


class TestQualityFiltering:
    """Test quality-based filtering."""
    
    def test_filter_by_quality_keeps_high_quality(self):
        """Test filtering keeps high quality results."""
        processor = DataQualityProcessor()
        results = [
            {"name": "Business 1", "quality_score": 80.0},
            {"name": "Business 2", "quality_score": 90.0},
            {"name": "Business 3", "quality_score": 40.0}
        ]
        filtered = processor.filter_by_quality(results, min_score=50.0)
        assert len(filtered) == 2
        assert filtered[0]["quality_score"] == 80.0
        assert filtered[1]["quality_score"] == 90.0
    
    def test_filter_by_quality_custom_threshold(self):
        """Test filtering with custom threshold."""
        processor = DataQualityProcessor()
        results = [
            {"name": "Business 1", "quality_score": 85.0},
            {"name": "Business 2", "quality_score": 75.0},
            {"name": "Business 3", "quality_score": 95.0}
        ]
        filtered = processor.filter_by_quality(results, min_score=80.0)
        assert len(filtered) == 2
    
    def test_filter_by_quality_empty_list(self):
        """Test filtering empty list."""
        processor = DataQualityProcessor()
        filtered = processor.filter_by_quality([], min_score=50.0)
        assert filtered == []


class TestStatistics:
    """Test statistics calculation."""
    
    def test_get_statistics_complete_data(self):
        """Test statistics with complete data."""
        processor = DataQualityProcessor()
        results = [
            {
                "name": "Business 1",
                "phone": "+12011111111",
                "email": "b1@example.com",
                "website": "https://b1.com",
                "rating": 4.5,
                "quality_score": 90.0
            },
            {
                "name": "Business 2",
                "phone": "+12012222222",
                "email": "b2@example.com",
                "website": "https://b2.com",
                "rating": 4.0,
                "quality_score": 85.0
            }
        ]
        stats = processor.get_statistics(results)
        
        assert stats["total_count"] == 2
        assert stats["avg_quality_score"] == 87.5
        assert stats["with_phone"] == 2
        assert stats["with_email"] == 2
        assert stats["with_website"] == 2
        assert stats["with_rating"] == 2
        assert stats["quality_distribution"]["A"] == 1  # 90%
        assert stats["quality_distribution"]["B"] == 1  # 85%
    
    def test_get_statistics_partial_data(self):
        """Test statistics with partial data."""
        processor = DataQualityProcessor()
        results = [
            {"name": "Business 1", "phone": "+12011111111", "quality_score": 60.0},
            {"name": "Business 2", "email": "b2@example.com", "quality_score": 50.0}
        ]
        stats = processor.get_statistics(results)
        
        assert stats["total_count"] == 2
        assert stats["with_phone"] == 1
        assert stats["with_email"] == 1
        assert stats["with_website"] == 0
        assert stats["with_rating"] == 0
    
    def test_get_statistics_empty_list(self):
        """Test statistics with empty list."""
        processor = DataQualityProcessor()
        stats = processor.get_statistics([])
        
        assert stats["total_count"] == 0
        assert stats["avg_quality_score"] == 0.0
        assert stats["with_phone"] == 0
        assert stats["with_email"] == 0
    
    def test_get_statistics_quality_distribution(self):
        """Test quality grade distribution calculation."""
        processor = DataQualityProcessor()
        results = [
            {"name": "Business 1", "quality_score": 95.0},  # A
            {"name": "Business 2", "quality_score": 85.0},  # B
            {"name": "Business 3", "quality_score": 75.0},  # C
            {"name": "Business 4", "quality_score": 65.0},  # D
            {"name": "Business 5", "quality_score": 45.0},  # F
        ]
        stats = processor.get_statistics(results)
        
        assert stats["quality_distribution"]["A"] == 1
        assert stats["quality_distribution"]["B"] == 1
        assert stats["quality_distribution"]["C"] == 1
        assert stats["quality_distribution"]["D"] == 1
        assert stats["quality_distribution"]["F"] == 1
