import re


def add(a, b):
    """Return the arithmetic sum of a and b."""
    return a + b


def is_even(n):
    """Return True if n is even, False otherwise."""
    return n % 2 == 0


def slugify(s):
    """Lowercase, strip, and collapse internal whitespace runs to a single hyphen."""
    return re.sub(r"\s+", "-", s.strip().lower())
