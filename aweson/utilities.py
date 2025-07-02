"""
Utility functions built on top of JSON-Path like expressions
and find_all() / find_next().
"""

# pylint: disable=unnecessary-lambda-assignment,protected-access

from copy import deepcopy
from typing import Any, Callable, Iterator

from aweson.core import _Accessor, find_all


def _find_all_with_multiplicity(
    root_data: list | dict | str | int | float | bool,
    path: _Accessor,
    *,
    with_path: bool = False,
    lenient: bool = False,
):
    """
    Workhorse utility function for finding both unique and duplicate items.
    """
    item_func = (lambda i: i[1]) if with_path else (lambda i: i)

    known_items: dict = {}

    for tup in find_all(root_data, path, with_path=with_path, lenient=lenient):
        item = item_func(tup)
        if item in known_items:
            known_items[item] += 1
        else:
            known_items[item] = 0
        yield tup, known_items[item]


def find_all_unique(
    root_data: list | dict | str | int | float | bool,
    path: _Accessor,
    *,
    with_path: bool = False,
    lenient: bool = False,
):
    """
    Yields unique elemnents, with or without paths.
    """
    yield from (
        item
        for item, multiplicity in _find_all_with_multiplicity(
            root_data, path, with_path=with_path, lenient=lenient
        )
        if multiplicity == 0
    )


def find_all_duplicate(
    root_data: list | dict | str | int | float | bool,
    path: _Accessor,
    *,
    with_path: bool = False,
    lenient: bool = False,
):
    """
    Yields duplicate elemnents, with or without paths.
    """
    yield from (
        item
        for item, multiplicity in _find_all_with_multiplicity(
            root_data, path, with_path=with_path, lenient=lenient
        )
        if multiplicity > 0
    )


def with_values(
    content: list | dict,
    path: _Accessor,
    values: Any | Iterator[Any] | Callable[[_Accessor, Any], Any] = None,
    /,
):
    """
    Returns a content (list or dictionary) with values specified by the call.

    The place(s) where values of the returned content differ to the original one
    is specified by ``path``. New values can come from an iterator, or they can
    be calculated, or they can be defined as values.

    The original argument ``content`` is treated immutable, i.e. the returned
    data will be a different object.

    For dictionaries, existing keys can have new values, and entirely new
    key/value pairs can be added.

    For lists, existing indexes can have new values defined, and only a single
    new item can be appended to a list.
    """
    content = deepcopy(content)

    all_accessors = list(path._accessors())
    stack = [(content, all_accessors)]

    while len(stack) > 0:
        data, accessors = stack.pop()
        if len(accessors) == 0:
            continue
        accessor = accessors[0]
        if len(accessors) == 1:
            if hasattr(values, "__iter__") and hasattr(values, "__next__"):
                iterator = values

                def insert_fun(_):
                    try:
                        return next(iterator)
                    except StopIteration as exc:
                        raise ValueError(
                            "Iterator size falls short of expectations"
                        ) from exc

            elif hasattr(values, "__call__"):
                insert_fun = values  # type: ignore
            else:
                single_value = values
                insert_fun = lambda x: single_value
            is_penultimate = True
        else:
            insert_fun = lambda x: accessors[1].container_type()
            is_penultimate = False

        stack_insert_position = len(stack)
        sub_tuples = accessor._access_or_insert(data, is_penultimate, insert_fun)
        for sub_data in sub_tuples:
            stack.insert(stack_insert_position, (sub_data, accessors[1:]))

    return content
