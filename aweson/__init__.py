"""
Iterate or find items in a hierarchical data structure (e.g. loaded from JSON content) based
on JSON Path-like Pythonic expressions.
"""

from .core import JP, find_all, find_next, parse
from .utilities import find_all_duplicate, find_all_unique, with_values
