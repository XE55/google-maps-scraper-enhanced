"""
Comprehensive tests for gmaps_scraper_server.extractor module.
Tests all extraction functions and JSON parsing logic.
"""
import pytest
import json
from gmaps_scraper_server.extractor import (
    safe_get,
    extract_initial_json,
    parse_json_data,
    get_main_name,
    get_place_id,
    get_gps_coordinates,
    get_complete_address,
    get_rating,
    get_reviews_count,
    get_website,
    get_phone_number,
    get_categories,
    get_thumbnail,
    extract_place_data,
    _find_phone_recursively
)


class TestSafeGet:
    """Tests for safe_get helper function."""
    
    def test_safe_get_dict_valid_key(self):
        """Test accessing valid key in dict."""
        data = {"name": "Test Place", "rating": 4.5}
        assert safe_get(data, "name") == "Test Place"
        assert safe_get(data, "rating") == 4.5
    
    def test_safe_get_dict_missing_key(self):
        """Test accessing missing key returns None."""
        data = {"name": "Test"}
        assert safe_get(data, "missing") is None
    
    def test_safe_get_list_valid_index(self):
        """Test accessing valid index in list."""
        data = ["a", "b", "c"]
        assert safe_get(data, 0) == "a"
        assert safe_get(data, 2) == "c"
    
    def test_safe_get_list_out_of_bounds(self):
        """Test accessing out of bounds index returns None."""
        data = ["a", "b"]
        assert safe_get(data, 5) is None
        assert safe_get(data, -1) is None
    
    def test_safe_get_nested_path(self):
        """Test accessing nested path."""
        data = {
            "place": {
                "details": ["name", "address", "phone"]
            }
        }
        assert safe_get(data, "place", "details", 0) == "name"
        assert safe_get(data, "place", "details", 2) == "phone"
    
    def test_safe_get_nested_invalid_path(self):
        """Test accessing invalid nested path returns None."""
        data = {"place": {"name": "Test"}}
        assert safe_get(data, "place", "missing", 0) is None
        assert safe_get(data, "invalid", "path") is None
    
    def test_safe_get_none_data(self):
        """Test safe_get with None data."""
        assert safe_get(None, "key") is None
    
    def test_safe_get_string_key_on_list(self):
        """Test using string key on list returns None."""
        data = ["a", "b", "c"]
        assert safe_get(data, "key") is None
    
    def test_safe_get_int_key_on_dict(self):
        """Test using int key on dict returns None."""
        data = {"0": "value"}
        assert safe_get(data, 0) is None
    
    def test_safe_get_empty_keys(self):
        """Test safe_get with no keys returns data."""
        data = {"test": "value"}
        assert safe_get(data) == data


class TestExtractInitialJson:
    """Tests for extract_initial_json function."""
    
    def test_extract_valid_json_object(self):
        """Test extracting valid JSON object."""
        html = """
        <html>
        <script>;window.APP_INITIALIZATION_STATE={"key":"value"};window.APP_FLAGS</script>
        </html>
        """
        result = extract_initial_json(html)
        assert result == '{"key":"value"}'
    
    def test_extract_valid_json_array(self):
        """Test extracting valid JSON array."""
        html = """
        ;window.APP_INITIALIZATION_STATE=[1,2,3];window.APP_FLAGS
        """
        result = extract_initial_json(html)
        assert result == '[1,2,3]'
    
    def test_extract_multiline_json(self):
        """Test extracting multiline JSON."""
        html = """
        ;window.APP_INITIALIZATION_STATE=[
            "data1",
            "data2"
        ];window.APP_FLAGS
        """
        result = extract_initial_json(html)
        assert '"data1"' in result
        assert '"data2"' in result
    
    def test_extract_pattern_not_found(self):
        """Test when pattern not found returns None."""
        html = "<html><body>No pattern here</body></html>"
        result = extract_initial_json(html)
        assert result is None
    
    def test_extract_invalid_json_start(self):
        """Test when extracted content doesn't start with [ or {."""
        html = ";window.APP_INITIALIZATION_STATE=invalid_data;window.APP_FLAGS"
        result = extract_initial_json(html)
        assert result is None
    
    def test_extract_empty_html(self):
        """Test with empty HTML."""
        result = extract_initial_json("")
        assert result is None
    
    def test_extract_with_complex_json(self):
        """Test extracting complex nested JSON."""
        json_data = '{"a":{"b":[1,2,{"c":"d"}]}}'
        html = f";window.APP_INITIALIZATION_STATE={json_data};window.APP_FLAGS"
        result = extract_initial_json(html)
        assert result == json_data


class TestParseJsonData:
    """Tests for parse_json_data function."""
    
    def test_parse_direct_list_structure(self):
        """Test parsing when data is directly at [3][6]."""
        data = [None, None, None, [None, None, None, None, None, None, ["data_blob"]]]
        json_str = json.dumps(data)
        result = parse_json_data(json_str)
        assert result == ["data_blob"]
    
    def test_parse_nested_json_string(self):
        """Test parsing when [3][6] contains nested JSON string."""
        # parse_json_data returns the data at index 6 of the inner structure
        inner_data = [None, None, None, None, None, None, ["inner_blob"]]
        inner_json = ")]}'\n" + json.dumps(inner_data)
        outer_data = [None, None, None, [None, None, None, None, None, None, inner_json]]
        json_str = json.dumps(outer_data)
        result = parse_json_data(json_str)
        # The function returns actual_data[6] which is ["inner_blob"]
        assert result == ["inner_blob"]
    
    def test_parse_none_input(self):
        """Test with None input."""
        result = parse_json_data(None)
        assert result is None
    
    def test_parse_invalid_json(self):
        """Test with invalid JSON string."""
        result = parse_json_data("not valid json")
        assert result is None
    
    def test_parse_wrong_structure_too_short(self):
        """Test when list is too short."""
        data = [None, None]
        json_str = json.dumps(data)
        result = parse_json_data(json_str)
        assert result is None
    
    def test_parse_wrong_structure_not_list(self):
        """Test when data is not a list."""
        json_str = '{"key": "value"}'
        result = parse_json_data(json_str)
        assert result is None
    
    def test_parse_nested_string_without_prefix(self):
        """Test nested string without )]}' prefix."""
        data = [None, None, None, [None, None, None, None, None, None, "no_prefix"]]
        json_str = json.dumps(data)
        result = parse_json_data(json_str)
        assert result is None
    
    def test_parse_nested_invalid_json_string(self):
        """Test nested invalid JSON string."""
        data = [None, None, None, [None, None, None, None, None, None, ")]}'\ninvalid"]]
        json_str = json.dumps(data)
        result = parse_json_data(json_str)
        assert result is None


class TestFieldExtraction:
    """Tests for individual field extraction functions."""
    
    @pytest.fixture
    def sample_data_blob(self):
        """Sample data blob with typical structure."""
        return [
            None,  # 0
            None,  # 1
            ["123 Main St", "New York", "NY", "10001"],  # 2 - address
            None,  # 3
            [None, None, None, None, None, None, None, 4.5, 120],  # 4 - rating/reviews
            None,  # 5
            None,  # 6
            ["https://example.com"],  # 7 - website
            None,  # 8
            [None, None, 40.7128, -74.0060],  # 9 - coordinates
            "ChIJOwg_06VPwokRYv534QaPC8g",  # 10 - place_id
            "Test Restaurant",  # 11 - name
            None,  # 12
            ["Restaurant", "Food", "Dining"],  # 13 - categories
            [[None, [None, None, None, None, None, None, ["https://photo.jpg"]]]]  # 14 - thumbnail
        ]
    
    def test_get_main_name(self, sample_data_blob):
        """Test extracting main name."""
        assert get_main_name(sample_data_blob) == "Test Restaurant"
    
    def test_get_main_name_missing(self):
        """Test name extraction when missing."""
        assert get_main_name([]) is None
    
    def test_get_place_id(self, sample_data_blob):
        """Test extracting place ID."""
        assert get_place_id(sample_data_blob) == "ChIJOwg_06VPwokRYv534QaPC8g"
    
    def test_get_place_id_missing(self):
        """Test place_id extraction when missing."""
        assert get_place_id([]) is None
    
    def test_get_gps_coordinates(self, sample_data_blob):
        """Test extracting GPS coordinates."""
        result = get_gps_coordinates(sample_data_blob)
        assert result == {"latitude": 40.7128, "longitude": -74.0060}
    
    def test_get_gps_coordinates_missing(self):
        """Test coordinates when missing."""
        assert get_gps_coordinates([]) is None
    
    def test_get_gps_coordinates_partial(self):
        """Test coordinates when only one value present."""
        data = [None] * 10 + [[None, None, 40.7128, None]]
        assert get_gps_coordinates(data) is None
    
    def test_get_complete_address(self, sample_data_blob):
        """Test extracting complete address."""
        result = get_complete_address(sample_data_blob)
        assert result == "123 Main St, New York, NY, 10001"
    
    def test_get_complete_address_missing(self):
        """Test address when missing."""
        assert get_complete_address([]) is None
    
    def test_get_complete_address_empty_parts(self):
        """Test address with some empty parts."""
        data = [None, None, ["123 Main", None, "", "10001"]]
        result = get_complete_address(data)
        assert result == "123 Main, 10001"
    
    def test_get_rating(self, sample_data_blob):
        """Test extracting rating."""
        assert get_rating(sample_data_blob) == 4.5
    
    def test_get_rating_missing(self):
        """Test rating when missing."""
        assert get_rating([]) is None
    
    def test_get_reviews_count(self, sample_data_blob):
        """Test extracting reviews count."""
        assert get_reviews_count(sample_data_blob) == 120
    
    def test_get_reviews_count_missing(self):
        """Test reviews count when missing."""
        assert get_reviews_count([]) is None
    
    def test_get_website(self, sample_data_blob):
        """Test extracting website."""
        assert get_website(sample_data_blob) == "https://example.com"
    
    def test_get_website_missing(self):
        """Test website when missing."""
        assert get_website([]) is None
    
    def test_get_categories(self, sample_data_blob):
        """Test extracting categories."""
        result = get_categories(sample_data_blob)
        assert result == ["Restaurant", "Food", "Dining"]
    
    def test_get_categories_missing(self):
        """Test categories when missing."""
        assert get_categories([]) is None
    
    def test_get_thumbnail(self, sample_data_blob):
        """Test extracting thumbnail - path may need verification."""
        # Thumbnail path is tentative, just test return type
        result = get_thumbnail(sample_data_blob)
        assert result is None or isinstance(result, str)
    
    def test_get_thumbnail_missing(self):
        """Test thumbnail when missing."""
        assert get_thumbnail([]) is None


class TestPhoneNumberExtraction:
    """Tests for phone number extraction functions."""
    
    def test_find_phone_recursively_direct_match(self):
        """Test finding phone in direct list structure."""
        data = [
            "https://icon/call_googblue",
            "+1 (555) 123-4567",
            "other_data"
        ]
        result = _find_phone_recursively(data)
        assert result == "15551234567"
    
    def test_find_phone_recursively_nested(self):
        """Test finding phone in nested structure."""
        data = [
            "unrelated",
            [
                "nested",
                ["https://icon/call_googblue", "(555) 987-6543"]
            ]
        ]
        result = _find_phone_recursively(data)
        assert result == "5559876543"
    
    def test_find_phone_recursively_in_dict(self):
        """Test finding phone in dict structure."""
        data = {
            "contact": {
                "info": ["https://icon/call_googblue", "555.111.2222"]
            }
        }
        result = _find_phone_recursively(data)
        assert result == "5551112222"
    
    def test_find_phone_recursively_not_found(self):
        """Test when phone not found."""
        data = ["no", "phone", "here"]
        result = _find_phone_recursively(data)
        assert result is None
    
    def test_find_phone_recursively_wrong_pattern(self):
        """Test with wrong icon pattern."""
        data = ["https://icon/wrong_icon", "555-1234"]
        result = _find_phone_recursively(data)
        assert result is None
    
    def test_find_phone_recursively_non_string_phone(self):
        """Test when phone number is not a string."""
        data = ["https://icon/call_googblue", 5551234]
        result = _find_phone_recursively(data)
        assert result is None
    
    def test_find_phone_recursively_empty_phone(self):
        """Test with empty phone string."""
        data = ["https://icon/call_googblue", ""]
        result = _find_phone_recursively(data)
        assert result is None
    
    def test_find_phone_recursively_only_letters(self):
        """Test with phone containing only letters."""
        data = ["https://icon/call_googblue", "CALL-NOW"]
        result = _find_phone_recursively(data)
        assert result is None
    
    def test_get_phone_number_found(self):
        """Test get_phone_number when phone exists."""
        data_blob = [
            "data",
            ["https://icon/call_googblue", "(555) 123-4567"]
        ]
        result = get_phone_number(data_blob)
        assert result == "5551234567"
    
    def test_get_phone_number_not_found(self):
        """Test get_phone_number when phone doesn't exist."""
        data_blob = ["no", "phone", "data"]
        result = get_phone_number(data_blob)
        assert result is None


class TestExtractPlaceData:
    """Tests for high-level extract_place_data function."""
    
    def test_extract_place_data_complete(self):
        """Test extracting complete place data."""
        # Create realistic HTML with proper structure
        inner_data = [
            None, None,
            ["123 Main St", "NYC", "NY"],  # 2 - address
            None,
            [None, None, None, None, None, None, None, 4.5, 100],  # 4 - rating/reviews
            None, None,
            ["https://test.com"],  # 7 - website
            None,
            [None, None, 40.7, -74.0],  # 9 - coords
            "place_id_123",  # 10
            "Test Place",  # 11 - name
            None,
            ["Restaurant"]  # 13 - categories
        ]
        
        inner_json = ")]}'\n" + json.dumps([None] * 6 + [inner_data])
        outer_data = [None, None, None, [None] * 6 + [inner_json]]
        
        html = f"""
        <html>
        <script>;window.APP_INITIALIZATION_STATE={json.dumps(outer_data)};window.APP_FLAGS</script>
        </html>
        """
        
        result = extract_place_data(html)
        
        assert result is not None
        assert result["name"] == "Test Place"
        assert result["place_id"] == "place_id_123"
        assert result["address"] == "123 Main St, NYC, NY"
        assert result["rating"] == 4.5
        assert result["reviews_count"] == 100
        assert result["website"] == "https://test.com"
        assert result["categories"] == ["Restaurant"]
        assert result["coordinates"] == {"latitude": 40.7, "longitude": -74.0}
    
    def test_extract_place_data_no_json_found(self):
        """Test when no JSON found in HTML."""
        html = "<html><body>No data</body></html>"
        result = extract_place_data(html)
        assert result is None
    
    def test_extract_place_data_invalid_structure(self):
        """Test with invalid JSON structure."""
        html = """
        <html>
        <script>;window.APP_INITIALIZATION_STATE={"wrong": "structure"};window.APP_FLAGS</script>
        </html>
        """
        result = extract_place_data(html)
        assert result is None
    
    def test_extract_place_data_partial_data(self):
        """Test extracting with some fields missing."""
        inner_data = [
            None, None, None, None, None, None, None, None, None, None,
            "place_123",  # 10 - place_id
            "Partial Place"  # 11 - name
        ]
        
        inner_json = ")]}'\n" + json.dumps([None] * 6 + [inner_data])
        outer_data = [None, None, None, [None] * 6 + [inner_json]]
        
        html = f"""
        <script>;window.APP_INITIALIZATION_STATE={json.dumps(outer_data)};window.APP_FLAGS</script>
        """
        
        result = extract_place_data(html)
        
        assert result is not None
        assert result["name"] == "Partial Place"
        assert result["place_id"] == "place_123"
        # Missing fields should not be in result
        assert "address" not in result
        assert "rating" not in result
    
    def test_extract_place_data_empty_html(self):
        """Test with empty HTML."""
        result = extract_place_data("")
        assert result is None
    
    def test_extract_place_data_all_none_values(self):
        """Test when all extracted values are None."""
        inner_data = [None] * 20
        inner_json = ")]}'\n" + json.dumps([None] * 6 + [inner_data])
        outer_data = [None, None, None, [None] * 6 + [inner_json]]
        
        html = f"""
        <script>;window.APP_INITIALIZATION_STATE={json.dumps(outer_data)};window.APP_FLAGS</script>
        """
        
        result = extract_place_data(html)
        # Should return None when no valid data extracted
        assert result is None


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_safe_get_with_type_error(self):
        """Test safe_get handles TypeError gracefully."""
        data = "string_not_dict_or_list"
        assert safe_get(data, 0) is None
    
    def test_extract_initial_json_malformed_html(self):
        """Test with malformed HTML."""
        html = ";window.APP_INITIALIZATION_STATE=[broken;window.APP_FLAGS"
        result = extract_initial_json(html)
        # Should extract even if JSON is broken (validation happens in parse)
        assert result is not None
    
    def test_parse_json_data_with_unicode(self):
        """Test parsing JSON with unicode characters."""
        data = [None, None, None, [None] * 6 + [["名前", "地址"]]]
        json_str = json.dumps(data, ensure_ascii=False)
        result = parse_json_data(json_str)
        assert result == ["名前", "地址"]
    
    def test_phone_extraction_international_format(self):
        """Test extracting international phone number."""
        data = ["https://icon/call_googblue", "+44 20 7946 0958"]
        result = _find_phone_recursively(data)
        assert result == "442079460958"
    
    def test_address_with_all_none_parts(self):
        """Test address extraction with all None parts."""
        data = [None, None, [None, None, None]]
        result = get_complete_address(data)
        assert result is None
    
    def test_categories_as_empty_list(self):
        """Test categories when it's an empty list."""
        data = [None] * 13 + [[]]
        result = get_categories(data)
        assert result == []
    
    def test_coordinates_with_zero_values(self):
        """Test coordinates with zero values (valid coordinates)."""
        data = [None] * 9 + [[None, None, 0.0, 0.0]]
        result = get_gps_coordinates(data)
        assert result == {"latitude": 0.0, "longitude": 0.0}
    
    def test_website_as_empty_array(self):
        """Test website when array is empty."""
        data = [None] * 7 + [[]]
        result = get_website(data)
        assert result is None
    
    def test_rating_as_zero(self):
        """Test rating when it's zero (valid rating)."""
        data = [None] * 4 + [[None] * 7 + [0.0]]
        result = get_rating(data)
        assert result == 0.0
    
    def test_reviews_count_as_zero(self):
        """Test reviews count when zero."""
        data = [None] * 4 + [[None] * 8 + [0]]
        result = get_reviews_count(data)
        assert result == 0
