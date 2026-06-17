"""
tests/test_harness_demo.py

Concrete assertions for the harness_demo.py worker-generated module.
The worker must create scripts/harness_demo.py with three functions:
  - add(a, b) -> sum
  - is_even(n) -> bool
  - slugify(s) -> str
"""

import pytest

# Import the module the worker will generate.
# Before the worker runs, this import will fail (expected — captured as baseline).
from scripts.harness_demo import add, is_even, slugify


class TestAdd:
    def test_positive(self):
        assert add(2, 3) == 5

    def test_zero_sum(self):
        assert add(-1, 1) == 0

    def test_negative(self):
        assert add(-3, -4) == -7

    def test_large(self):
        assert add(100, 200) == 300


class TestIsEven:
    def test_even(self):
        assert is_even(4) is True

    def test_odd(self):
        assert is_even(7) is False

    def test_zero(self):
        assert is_even(0) is True

    def test_negative_even(self):
        assert is_even(-2) is True

    def test_negative_odd(self):
        assert is_even(-3) is False


class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello-world"

    def test_strip_and_collapse(self):
        assert slugify("  A  B  ") == "a-b"

    def test_single_word(self):
        assert slugify("Python") == "python"

    def test_already_lower(self):
        assert slugify("foo bar") == "foo-bar"

    def test_multiple_spaces(self):
        assert slugify("one   two   three") == "one-two-three"
