"""
Data quality processor for Google Maps scraping results.

Features:
- Phone number normalization (international format)
- Email validation and normalization
- Duplicate detection and removal
- Data completeness scoring
- Quality metrics calculation
- Data enrichment preparation

Standards:
- E.164 phone format (international standard)
- RFC 5322 email validation
- UTF-8 text normalization
"""

import re
import phonenumbers
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from email_validator import validate_email, EmailNotValidError


@dataclass
class QualityMetrics:
    """Quality metrics for a place result."""
    completeness_score: float  # 0-100%
    has_phone: bool
    has_email: bool
    has_website: bool
    has_address: bool
    has_hours: bool
    has_rating: bool
    has_reviews: bool
    field_count: int
    total_fields: int
    
    @property
    def quality_grade(self) -> str:
        """Get letter grade based on completeness."""
        if self.completeness_score >= 90:
            return "A"
        elif self.completeness_score >= 80:
            return "B"
        elif self.completeness_score >= 70:
            return "C"
        elif self.completeness_score >= 60:
            return "D"
        else:
            return "F"


class DataQualityProcessor:
    """Process and improve data quality of scraping results."""
    
    def __init__(self, default_region: str = "US"):
        """
        Initialize data quality processor.
        
        Args:
            default_region: Default region code for phone parsing (ISO 3166-1 alpha-2)
        """
        self.default_region = default_region
        self._seen_emails: Set[str] = set()
        self._seen_phones: Set[str] = set()
        self._seen_place_ids: Set[str] = set()
    
    def normalize_phone(self, phone: Optional[str], region: Optional[str] = None) -> Optional[str]:
        """
        Normalize phone number to E.164 international format.
        
        Args:
            phone: Raw phone number string
            region: Region code for parsing (default: US)
        
        Returns:
            Normalized phone in E.164 format (+1234567890) or None if invalid
        
        Example:
            >>> processor.normalize_phone("(555) 123-4567")
            '+15551234567'
        """
        if not phone or not phone.strip():
            return None
        
        try:
            # Parse with region
            parsed = phonenumbers.parse(phone, region or self.default_region)
            
            # Validate
            if not phonenumbers.is_valid_number(parsed):
                return None
            
            # Format as E.164
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            
        except phonenumbers.NumberParseException:
            return None
    
    def normalize_email(self, email: Optional[str]) -> Optional[str]:
        """
        Validate and normalize email address.
        
        Args:
            email: Raw email string
        
        Returns:
            Normalized email (lowercase) or None if invalid
        
        Example:
            >>> processor.normalize_email("USER@EXAMPLE.COM")
            'user@example.com'
        """
        if not email or not email.strip():
            return None
        
        try:
            # Validate and normalize
            validated = validate_email(email, check_deliverability=False)
            return validated.normalized
            
        except EmailNotValidError:
            return None
    
    def is_duplicate_email(self, email: str) -> bool:
        """Check if email has been seen before."""
        if email in self._seen_emails:
            return True
        self._seen_emails.add(email)
        return False
    
    def is_duplicate_phone(self, phone: str) -> bool:
        """Check if phone has been seen before."""
        if phone in self._seen_phones:
            return True
        self._seen_phones.add(phone)
        return False
    
    def is_duplicate_place(self, place_id: str) -> bool:
        """Check if place ID has been seen before."""
        if place_id in self._seen_place_ids:
            return True
        self._seen_place_ids.add(place_id)
        return False
    
    def calculate_completeness(self, place_data: Dict) -> float:
        """
        Calculate data completeness score (0-100).
        
        Args:
            place_data: Dictionary with place information
        
        Returns:
            Completeness score as percentage
        """
        # Key fields to check
        fields = [
            "name",
            "address",
            "phone",
            "email",
            "website",
            "rating",
            "reviews_count",
            "category",
            "hours",
            "latitude",
            "longitude",
        ]
        
        present_count = 0
        for field in fields:
            value = place_data.get(field)
            if value is not None and value != "" and value != {}:
                present_count += 1
        
        return (present_count / len(fields)) * 100
    
    def calculate_quality_metrics(self, place_data: Dict) -> QualityMetrics:
        """
        Calculate comprehensive quality metrics.
        
        Args:
            place_data: Dictionary with place information
        
        Returns:
            QualityMetrics object with detailed scores
        """
        completeness = self.calculate_completeness(place_data)
        
        return QualityMetrics(
            completeness_score=completeness,
            has_phone=bool(place_data.get("phone")),
            has_email=bool(place_data.get("email")),
            has_website=bool(place_data.get("website")),
            has_address=bool(place_data.get("address")),
            has_hours=bool(place_data.get("hours")),
            has_rating=place_data.get("rating") is not None,
            has_reviews=place_data.get("reviews_count", 0) > 0,
            field_count=sum(1 for v in place_data.values() if v not in (None, "", {})),
            total_fields=len(place_data)
        )
    
    def clean_place_data(self, place_data: Dict) -> Dict:
        """
        Clean and normalize all fields in place data.
        
        Args:
            place_data: Raw place data dictionary
        
        Returns:
            Cleaned place data dictionary
        """
        cleaned = place_data.copy()
        
        # Normalize phone
        if "phone" in cleaned:
            cleaned["phone"] = self.normalize_phone(cleaned["phone"])
        
        # Normalize email
        if "email" in cleaned:
            cleaned["email"] = self.normalize_email(cleaned["email"])
        
        # Normalize website URL
        if "website" in cleaned and cleaned["website"]:
            cleaned["website"] = self._normalize_url(cleaned["website"])
        
        # Trim strings
        for key, value in cleaned.items():
            if isinstance(value, str):
                cleaned[key] = value.strip()
        
        # Add quality score
        cleaned["quality_score"] = self.calculate_completeness(cleaned)
        
        return cleaned
    
    def _normalize_url(self, url: str) -> str:
        """Normalize website URL."""
        url = url.strip()
        
        # Add protocol if missing
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        # Remove trailing slash
        url = url.rstrip("/")
        
        return url
    
    def deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """
        Remove duplicate results based on place_id, phone, and email.
        
        Args:
            results: List of place data dictionaries
        
        Returns:
            Deduplicated list of results
        """
        self.reset_deduplication()
        
        unique_results = []
        
        for result in results:
            place_id = result.get("place_id")
            phone = result.get("phone")
            email = result.get("email")
            
            # Check for duplicates
            is_duplicate = False
            
            if place_id and self.is_duplicate_place(place_id):
                is_duplicate = True
            elif phone and self.is_duplicate_phone(phone):
                is_duplicate = True
            elif email and self.is_duplicate_email(email):
                is_duplicate = True
            
            if not is_duplicate:
                unique_results.append(result)
        
        return unique_results
    
    def process_batch(self, results: List[Dict], deduplicate: bool = True) -> List[Dict]:
        """
        Process a batch of results (clean + deduplicate).
        
        Args:
            results: List of raw place data
            deduplicate: Whether to remove duplicates
        
        Returns:
            List of cleaned, deduplicated results
        """
        # Clean each result
        cleaned = [self.clean_place_data(result) for result in results]
        
        # Deduplicate if requested
        if deduplicate:
            cleaned = self.deduplicate_results(cleaned)
        
        return cleaned
    
    def filter_by_quality(self, results: List[Dict], min_score: float = 50.0) -> List[Dict]:
        """
        Filter results by minimum quality score.
        
        Args:
            results: List of place data with quality_score field
            min_score: Minimum quality score (0-100)
        
        Returns:
            Filtered list meeting quality threshold
        """
        return [
            result for result in results
            if result.get("quality_score", 0) >= min_score
        ]
    
    def get_statistics(self, results: List[Dict]) -> Dict[str, any]:
        """
        Get statistics about data quality.
        
        Args:
            results: List of place data dictionaries
        
        Returns:
            Dictionary with quality statistics
        """
        if not results:
            return {
                "total_count": 0,
                "avg_quality_score": 0.0,
                "with_phone": 0,
                "with_email": 0,
                "with_website": 0,
                "with_rating": 0,
                "quality_distribution": {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
            }
        
        total = len(results)
        avg_quality = sum(r.get("quality_score", 0) for r in results) / total
        
        with_phone = sum(1 for r in results if r.get("phone"))
        with_email = sum(1 for r in results if r.get("email"))
        with_website = sum(1 for r in results if r.get("website"))
        with_rating = sum(1 for r in results if r.get("rating") is not None)
        
        # Grade distribution
        distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for result in results:
            score = result.get("quality_score", 0)
            metrics = QualityMetrics(
                completeness_score=score,
                has_phone=bool(result.get("phone")),
                has_email=bool(result.get("email")),
                has_website=bool(result.get("website")),
                has_address=bool(result.get("address")),
                has_hours=bool(result.get("hours")),
                has_rating=result.get("rating") is not None,
                has_reviews=result.get("reviews_count", 0) > 0,
                field_count=0,
                total_fields=0
            )
            distribution[metrics.quality_grade] += 1
        
        return {
            "total_count": total,
            "avg_quality_score": avg_quality,
            "with_phone": with_phone,
            "with_email": with_email,
            "with_website": with_website,
            "with_rating": with_rating,
            "quality_distribution": distribution
        }
    
    def reset_deduplication(self) -> None:
        """Reset deduplication tracking."""
        self._seen_emails.clear()
        self._seen_phones.clear()
        self._seen_place_ids.clear()
    
    def validate_phone_format(self, phone: str) -> bool:
        """Check if phone is in valid E.164 format."""
        if not phone:
            return False
        
        # E.164 format: +[1-9]\d{1,14}
        pattern = r'^\+[1-9]\d{1,14}$'
        return bool(re.match(pattern, phone))
    
    def validate_email_format(self, email: str) -> bool:
        """Check if email has valid format."""
        if not email:
            return False
        
        try:
            validate_email(email, check_deliverability=False)
            return True
        except EmailNotValidError:
            return False
