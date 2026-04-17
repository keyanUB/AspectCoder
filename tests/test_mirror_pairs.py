import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mirror_pairs import Solution


@pytest.fixture
def solution():
    return Solution()


class TestMinAbsoluteDistance:

    def test_basic_mirror_pair(self, solution):
        """Simple case: 12 and 21 are mirror pairs at distance 1."""
        assert solution.minAbsoluteDistance([12, 21]) == 1

    def test_no_mirror_pair_returns_minus_one(self, solution):
        """No mirror pairs exist -> return -1."""
        assert solution.minAbsoluteDistance([12, 34, 56]) == -1

    def test_multiple_pairs_return_minimum(self, solution):
        """Multiple mirror pairs; the minimum distance should be returned."""
        assert solution.minAbsoluteDistance([12, 34, 21]) == 2

    def test_palindrome_number_self_pair(self, solution):
        """A palindrome number repeated forms a mirror pair with itself."""
        assert solution.minAbsoluteDistance([121, 121]) == 1

    def test_single_element_no_pair(self, solution):
        """A single element cannot form a pair."""
        assert solution.minAbsoluteDistance([123]) == -1

    def test_leading_zero_dropped(self, solution):
        """10 reversed is 01 = 1; so 10 and 1 are a mirror pair."""
        assert solution.minAbsoluteDistance([10, 1]) == 1

    def test_mirror_pair_not_adjacent(self, solution):
        """Mirror pair separated by several elements; distance should be correct."""
        assert solution.minAbsoluteDistance([123, 5, 6, 7, 321]) == 4

    def test_closest_pair_chosen_among_many(self, solution):
        """When multiple mirror pairs exist, the one with smallest index gap wins."""
        assert solution.minAbsoluteDistance([12, 34, 43, 21]) == 1

    def test_all_same_palindrome(self, solution):
        """All elements are the same palindrome number -> minimum distance is 1."""
        assert solution.minAbsoluteDistance([11, 11, 11]) == 1

    def test_large_numbers_leading_zero(self, solution):
        """1000 reversed is 0001 = 1; so 1000 and 1 are a mirror pair."""
        assert solution.minAbsoluteDistance([1000, 1]) == 1
