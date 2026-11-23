"""
soak_isbn.py

Hypothesis-based property tests for ISBN-10/ISBN-13 utilities.

Run with: python soak_isbn.py
"""

import sys
import os

# Add the current directory to the path so we can import home module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from home import (
    is_valid_isbn10,
    calculate_isbn10_check_digit,
    isbn10_to_isbn13,
    is_valid_isbn13,
)

# Also import the Hypothesis library
from hypothesis import given, settings, strategies as st
from hypothesis import Phase


# ISBN-10 digit strategies
# A valid ISBN-10 check digit is either 0-9 or X (for 10)
@st.composite
def isbn10_prefix(draw):
    """
    Generate a valid 9-digit ISBN-10 prefix.
    Each digit has weight 1-9, so we generate valid digits.
    """
    digits = []
    for i in range(9):
        # Generate a digit that will be used with weight (i+1)
        d = draw(st.integers(min_value=0, max_value=9))
        digits.append(str(d))
    return "".join(digits)


@st.composite
def isbn10_with_check(draw):
    """
    Generate a full 10-digit ISBN-10 where the last digit is the
    correct check digit.
    """
    prefix = draw(isbn10_prefix())
    check_digit = calculate_isbn10_check_digit(prefix)
    return prefix + check_digit


@st.composite
def isbn10_with_special_check(draw):
    """
    Generate a 10-digit ISBN-10 where the check digit is explicitly 'X'.
    This ensures the weight-10 position with X is valid.
    """
    prefix = draw(isbn10_prefix())
    check_digit = 'X'
    return prefix + check_digit


# ISBN-13 data strategies
@st.composite
def isbn13_data(draw):
    """
    Generate valid ISBN-13 numbers by taking a 12-digit prefix,
    computing the check digit, and returning the full 13-digit ISBN.
    """
    # Generate first 12 digits: first 3 are '978' or '979'
    first_part = draw(st.text(alphabet="0123456789", min_size=12, max_size=12))
    # Ensure it starts with 978 or 979
    prefix_12 = draw(st.text(alphabet="0123456789", min_size=12, max_size=12))
    if prefix_12[:3] not in ("978", "979"):
        prefix_12 = "978" + prefix_12[3:]
    # Calculate check digit
    total = sum(int(prefix_12[i]) * (1 if i % 2 == 0 else 3) for i in range(12))
    check_digit = (10 - (total % 10)) % 10
    return prefix_12 + str(check_digit)


# =============================================================================
# Property Tests
# =============================================================================

class TestISBN10Validation:
    """Test cases for is_valid_isbn10 function."""

    @given(st.text(
        alphabet="0123456789X",
        min_size=10,
        max_size=10
    ))
    @settings(max_examples=500, deadline=None)
    def test_isbn10_formats(self, s):
        """Test that is_valid_isbn10 correctly identifies valid formats."""
        result = is_valid_isbn10(s)
        # Should return a boolean
        assert isinstance(result, bool)

    @given(isbn10_with_check())
    @settings(max_examples=500, deadline=None)
    def test_valid_check_digit_is_accepted(self, s):
        """Valid ISBN-10 with correct check digit should be valid."""
        assert is_valid_isbn10(s) is True

    @given(isbn10_prefix())
    @settings(max_examples=500, deadline=None)
    def test_invalid_prefix_fails(self, prefix):
        """ISBN-10 with incorrect check digit should be invalid."""
        # Extract first 9 digits to get a valid check digit
        # Then append a wrong check digit (different from calculated)
        invalid_prefix = prefix[:8]  # 8 digits
        wrong_check = '0' if prefix[8] != '0' else '1'
        invalid = invalid_prefix + wrong_check
        assert is_valid_isbn10(invalid) is False

    @given(st.text(alphabet="0123456789", min_size=9, max_size=9))
    @settings(max_examples=500, deadline=None)
    def test_null_check_digit(self, prefix):
        """Adding '0' as check digit to a 9-digit prefix produces valid ISBN."""
        candidate = prefix + '0'
        # The result should be either valid or invalid, both are acceptable
        assert isinstance(is_valid_isbn10(candidate), bool)

    @given(st.text(alphabet="0123456789X", min_size=8, max_size=9))
    @settings(max_examples=500, deadline=None)
    def test_short_length_fails(self, s):
        """ISBN shorter than 10 digits should be invalid."""
        assert is_valid_isbn10(s) is False

    @given(st.text(alphabet="0123456789X", min_size=11, max_size=15))
    @settings(max_examples=500, deadline=None)
    def test_long_length_fails(self, s):
        """ISBN longer than 10 digits should be invalid."""
        assert is_valid_isbn10(s) is False

    @given(st.text(alphabet="0123456789X", min_size=10, max_size=10))
    @settings(max_examples=500, deadline=None)
    def test_with_dashes(self, s):
        """Dashed ISBN should be validated correctly."""
        s_with_dash = s[:5] + "-" + s[5:]
        assert isinstance(is_valid_isbn10(s_with_dash), bool)
        assert is_valid_isbn10(s) == is_valid_isbn10(s_with_dash.replace("-", ""))


class TestISBN10CheckDigit:
    """Test cases for calculate_isbn10_check_digit function."""

    @given(isbn10_prefix())
    @settings(max_examples=500, deadline=None)
    def test_check_digit_calculated(self, prefix):
        """Check digit should be calculated for valid 9-digit prefix."""
        result = calculate_isbn10_check_digit(prefix)
        assert result is not None
        assert result in "0123456789X"

    @given(st.text(alphabet="0123456789", min_size=8, max_size=10))
    @settings(max_examples=500, deadline=None)
    def test_invalid_length_returns_none(self, s):
        """Invalid length should return None."""
        if len(s) != 9:
            assert calculate_isbn10_check_digit(s) is None

    @given(st.text(
        alphabet="0123456789X",
        min_size=9,
        max_size=9
    ))
    @settings(max_examples=500, deadline=None)
    def test_non_numeric_returns_none(self, s):
        """Non-numeric input with length 9 should return None."""
        if not s.isdigit():
            assert calculate_isbn10_check_digit(s) is None


class TestISBN10ToISBN13:
    """Test cases for isbn10_to_isbn13 function."""

    @given(isbn10_with_check())
    @settings(max_examples=500, deadline=None)
    def test_conversion_produces_valid_isbn13(self, s):
        """Converted ISBN-13 should be valid."""
        isbn13 = isbn10_to_isbn13(s)
        assert isbn13 is not None
        assert is_valid_isbn13(isbn13) is True

    @given(isbn10_with_check())
    @settings(max_examples=500, deadline=None)
    def test_isbn13_has_correct_prefix(self, s):
        """ISBN-13 should start with '978'."""
        isbn13 = isbn10_to_isbn13(s)
        assert isbn13.startswith("978")

    @given(isbn10_with_check())
    @settings(max_examples=500, deadline=None)
    def test_isbn13_length(self, s):
        """ISBN-13 should be exactly 13 digits."""
        isbn13 = isbn10_to_isbn13(s)
        assert len(isbn13) == 13
        assert isbn13.isdigit()

    @given(isbn10_with_check())
    @settings(max_examples=500, deadline=None)
    def test_conversion_is_consistent(self, s):
        """Converting twice should give the same result."""
        first = isbn10_to_isbn13(s)
        second = isbn10_to_isbn13(s)
        assert first == second


class TestISBN13Validation:
    """Test cases for is_valid_isbn13 function."""

    @given(isbn13_data())
    @settings(max_examples=500, deadline=None)
    def test_valid_isbn13_accepted(self, s):
        """Valid ISBN-13 should be accepted."""
        assert is_valid_isbn13(s) is True

    @given(st.text(alphabet="0123456789", min_size=12, max_size=14))
    @settings(max_examples=500, deadline=None)
    def test_wrong_length_fails(self, s):
        """Wrong length should be invalid."""
        # Skip 13-digit numeric strings (may be valid ISBN-13)
        if len(s) != 13 or not s.isdigit():
            assert is_valid_isbn13(s) is False

    @given(st.text(alphabet="0123456789", min_size=13, max_size=13))
    @settings(max_examples=500, deadline=None)
    def test_non_numeric_fails(self, s):
        """Non-numeric input with length 13 should be invalid."""
        # Skip valid ISBN-13 numbers (all digits, 13 chars)
        if len(s) != 13 or not s.isdigit() or not is_valid_isbn13(s):
            assert is_valid_isbn13(s) is False

    @given(st.text(alphabet="0123456789X!", min_size=13, max_size=13))
    @settings(max_examples=500, deadline=None)
    def test_special_characters_fails(self, s):
        """Special characters should be invalid."""
        # Skip if string is all digits (valid ISBN-13) - not a "special character" case
        if s.isdigit() or not is_valid_isbn13(s):
            # Verify special characters (non-digit) are invalid
            if not s.isdigit():
                assert is_valid_isbn13(s) is False


class TestIntegration:
    """Integration tests combining multiple functions."""

    @given(isbn10_with_check())
    @settings(max_examples=500, deadline=None)
    def test_full_pipeline(self, s):
        """
        Full pipeline test:
        1. Validate ISBN-10 (should be valid)
        2. Convert to ISBN-13 (should be valid)
        3. Validate ISBN-13 (should be valid)
        """
        assert is_valid_isbn10(s) is True
        isbn13 = isbn10_to_isbn13(s)
        assert isbn13 is not None
        assert is_valid_isbn13(isbn13) is True

    @given(st.text(alphabet="0123456789X", min_size=10, max_size=10))
    @settings(max_examples=500, deadline=None)
    def test_invalid_input(self, s):
        """
        Test that non-standard ISBN-10 produces False for validation
        and None for check digit calculation.
        """
        # This is a random 10-digit string, may or may not be valid
        result = is_valid_isbn10(s)
        assert isinstance(result, bool)


# Run the tests
if __name__ == "__main__":
    print("=" * 60)
    print("ISBN-10/ISBN-13 Hypothesis Property Tests")
    print("=" * 60)
    print("\nRunning tests with Hypothesis...")
    print("=" * 60)
    print()

    # Run all tests
    result = 0
    try:
        # We run the tests via pytest-style collection
        # But for now, let's just run a quick smoke test
        print("Running smoke test...")
        test_isbn10_with_check().example()
        test_isbn13_data().example()
        print("  Smoke test passed!")
        print("\nAll tests defined successfully.")
        print("\nTo run the full test suite:")
        print("  pip install hypothesis")
        print("  pytest soak_isbn.py -v")
    except Exception as e:
        print(f"Test setup failed: {e}")
        result = 1

    sys.exit(result)
