import pytest

from aweson import JP, find_all, find_all_duplicate, find_all_unique, find_next


def test_x():
    assert str(JP[JP.id == 0]) == "$[?@.id == 0]"
