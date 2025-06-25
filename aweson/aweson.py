"""
Infra for JSON Path-like expressions and finding items in data hiearchy.
"""

# pylint: disable=protected-access
from __future__ import annotations

import dataclasses as dc
import re
from abc import ABC
from collections import namedtuple
from typing import Any, Callable, Iterator


@dc.dataclass(frozen=True, kw_only=True)
class _Accessor(ABC):
    """
    Base class for building JSON Path-like expression.
    """

    parent: _Accessor | None
    container_type: type

    def _access(
        self, container: list | dict, *, yield_path: bool = False, lenient: bool = False
    ) -> Iterator[tuple[Any, Callable[[_Accessor], _Accessor] | None]]:
        """
        Args:
            container: the data structure to access into
            yield_path: whether to yield a singular path to the item (or items) that are being accessed
            lenient: whether to allow out-of-bounds indexing or missing dict key references to raise
                IndexError or KeyError, respectively
        Returns:
            An iterator to tuples, where there the first field of the tuple is the item being accessed
            at this point, and the second field of the tuple is either ``None``, or a function taking
            a single ``parent`` argument, to create paths leading to those items being accessed.
        """
        raise NotImplementedError("Root accessor should not be invoked")

    def _is_singular(self) -> bool:
        """
        Returns: if this accessor (excluding any parent from consideration) can only
            ever return a single item.
        """
        return True

    def is_singular(self) -> bool:
        """
        Returns: if this path (this accessor and its parents, transitively) can only
            ever return a single item. E.g. a slice expression in a path makes it non-singular,
            even if the start/stop combination otherwise would say it's singular, like ``[1:2]``.
        """
        return self._is_singular() and (
            self.parent is None or self.parent.is_singular()
        )

    def _representation(self) -> str:
        """
        Represention for this accessor (excluding any parent)
        """
        raise NotImplementedError("Root accessor should not be invoked")

    def _check_container_type(self, container: list | dict):
        """
        Performs a check that a container to access is of the type mandated by
        the declared container_type of an accessor instance.
        """
        if not isinstance(  # pylint: disable=isinstance-second-argument-not-valid-type
            container, self.container_type
        ):
            raise ValueError(
                f"Expected {self.container_type}, got {type(container)} at {self}"
            )

    def _accessors(self) -> list[_Accessor]:
        """
        List of accessors, from root to this, recursively collected.
        """
        if self.parent is None:
            # Symmetry would suggest here to `return [self]`, however,
            # we cheat here: this instance shall be the root (=first accessor
            # to traverse by), not the parent
            return []
        return self.parent._accessors() + [self]

    def __str__(self):
        accessors = self._accessors()
        return "$" + "".join(a._representation() for a in accessors)

    def __getattr__(self, specification):
        """
        JSON Path-like expression builder infra.

        Overloaded for dict key access.
        """
        return _DictKeyAccessor(parent=self, key=specification)

    def __getitem__(self, specification):
        """
        JSON Path-like expression builder infra.

        Overloaded for list (index, slice) and various dict key access.
        """
        if isinstance(specification, str):
            if specification == "*":
                return _ListSliceAccessor(parent=self, slice_=slice(None, None, None))
            if specification.isidentifier():
                return _DictKeyAccessor(parent=self, key=specification)
            key_regex = re.compile(specification)
            return _DictKeyRegexAccessor(parent=self, key_regex=key_regex)
        if isinstance(specification, int):
            return _ListIndexAccessor(parent=self, index=specification)
        if isinstance(specification, slice):
            return _ListSliceAccessor(parent=self, slice_=specification)
        raise ValueError(f"Unsupported indexing expression {specification}")

    def __call__(self, *paths, **named_paths):
        """
        JSON Path-like expression builder infra.

        Overloaded for sub-item selection (vanilla or named tuple).
        """
        if len(paths) > 0 and len(named_paths) > 0:
            raise NotImplementedError(
                "Either all sub-selections are to be named, or none of them."
            )

        def verify_paths(paths):
            not_accessors = [path for path in paths if not isinstance(path, _Accessor)]
            if len(not_accessors) > 0:
                raise ValueError(f"Not paths: {not_accessors}")
            not_singulars = [path for path in paths if not path.is_singular()]
            if len(not_singulars) > 0:
                raise ValueError(
                    f"Not singular paths (could point to multiple items): {not_singulars}"
                )

        if len(paths) > 0:
            verify_paths(paths)
            return _SubHiearchyAccessor(
                parent=self, sub_accessors=paths, tuple_ctor=tuple
            )
        if len(named_paths) > 0:
            paths = list(named_paths.values())
            verify_paths(paths)
            named_tuple = namedtuple("SubSelect", list(named_paths.keys()))
            return _SubHiearchyAccessor(
                parent=self,
                sub_accessors=paths,
                tuple_ctor=lambda values: named_tuple(*values),
            )
        raise NotImplementedError("Sub-selection cannot be empty")


@dc.dataclass(frozen=True, kw_only=True)
class _DictKeyAccessor(_Accessor):
    """Accesses a value of a dict container by a key"""

    key: str
    container_type: type = dict

    def _access(
        self, container: list | dict, *, yield_path: bool = False, lenient: bool = False
    ) -> Iterator[tuple[Any, Callable[[_Accessor], _Accessor] | None]]:
        self._check_container_type(container)
        if lenient and self.key not in container:
            yield from iter([])
        elif yield_path:
            yield container[self.key], (lambda parent: _DictKeyAccessor(parent=parent, key=self.key))  # type: ignore
        else:
            yield container[self.key], None  # type: ignore

    def _representation(self) -> str:
        return f".{self.key}"


@dc.dataclass(frozen=True, kw_only=True)
class _DictKeyRegexAccessor(_Accessor):
    """Accesses a value or values of a dict container by a regex matching keys"""

    key_regex: re.Pattern
    container_type: type = dict

    def _is_singular(self) -> bool:
        return False

    def _access(
        self, container: list | dict, *, yield_path: bool = False, lenient: bool = False
    ) -> Iterator[tuple[Any, Callable[[_Accessor], _Accessor] | None]]:
        self._check_container_type(container)
        for key, value in container.items():  # type: ignore
            if self.key_regex.findall(key):  # pylint: disable=no-member
                if yield_path:
                    yield value, lambda parent: _DictKeyAccessor(
                        parent=parent, key=key  # pylint: disable=cell-var-from-loop
                    )
                else:
                    yield value, None

    def _representation(self) -> str:
        return f"[{self.key_regex.pattern}]"  # pylint: disable=no-member


@dc.dataclass(frozen=True, kw_only=True)
class _ListIndexAccessor(_Accessor):
    """Accesses an item of a list by an index"""

    index: int
    container_type: type = list

    def _access(
        self, container: list | dict, *, yield_path: bool = False, lenient: bool = False
    ) -> Iterator[tuple[Any, Callable[[_Accessor], _Accessor] | None]]:
        self._check_container_type(container)
        if lenient and (self.index >= len(container) or self.index < -len(container)):
            yield from iter([])
        elif yield_path:
            if self.index >= 0:
                yield container[self.index], lambda parent: _ListIndexAccessor(
                    parent=parent, index=self.index
                )
            else:
                yield container[self.index], lambda parent: _ListIndexAccessor(
                    parent=parent, index=len(container) + self.index
                )
        else:
            yield container[self.index], None

    def _representation(self) -> str:
        return f"[{self.index}]"


@dc.dataclass(frozen=True, kw_only=True)
class _ListSliceAccessor(_Accessor):
    """Accesses items of a list by a slice"""

    slice_: slice
    container_type: type = list

    def _is_singular(self) -> bool:
        return False

    def _access(
        self, container: list | dict, *, yield_path: bool = False, lenient: bool = False
    ) -> Iterator[tuple[Any, Callable[[_Accessor], _Accessor] | None]]:
        _ = lenient  # unused
        self._check_container_type(container)
        if yield_path:

            def create_accessor_ctor(index: int) -> _Accessor:
                return lambda parent: _ListIndexAccessor(parent=parent, index=index)  # type: ignore

            slice_indices = self.slice_.indices(len(container))

            yield from (
                (item, create_accessor_ctor(current_index))
                for current_index, item in zip(
                    range(slice_indices[0], slice_indices[1], slice_indices[2]),
                    container[self.slice_],
                )
            )
        else:
            yield from ((item, None) for item in container[self.slice_])

    def _representation(self) -> str:
        repr_ = (
            (f"[{self.slice_.start}" if self.slice_.start is not None else "[")
            + (f":{self.slice_.stop}" if self.slice_.stop is not None else ":")
            + (f":{self.slice_.step}]" if self.slice_.step is not None else "]")
        )
        return repr_


@dc.dataclass(frozen=True, kw_only=True)
class _SubHiearchyAccessor(_Accessor):
    """
    Instead of returning an entire item (of a list), it constructs a tuple based on sub-JSON Path-like expressions.
    """

    sub_accessors: list[_Accessor]
    tuple_ctor: Any
    container_type: type = dict

    def _access(
        self, container: list | dict, *, yield_path: bool = False, lenient: bool = False
    ) -> Iterator[tuple[Any, Callable[[_Accessor], _Accessor] | None]]:
        _ = lenient  # unused
        self._check_container_type(container)
        items = [
            find_next(container, sub_accessor, default=None)
            for sub_accessor in self.sub_accessors
        ]
        if yield_path:
            yield self.tuple_ctor(items), lambda parent: _SubHiearchyAccessor(
                parent=parent,
                sub_accessors=self.sub_accessors,
                tuple_ctor=self.tuple_ctor,
            )
        else:
            yield self.tuple_ctor(items), None

    def _representation(self):
        return (
            f"({', '.join(str(sub_accessor) for sub_accessor in self.sub_accessors)})"
        )


JP = _Accessor(parent=None, container_type=type(None))


def find_all(
    root_data: list | dict | str | int | float | bool,
    path: _Accessor,
    *,
    with_path: bool = False,
    lenient: bool = False,
):
    """
    Finds all matching items in a JSON-like data hierarchy (lists of / dicts of / values) based
    on a JSON Path-like specification. Technically, it iterates over the matching items.

    Args:
        path: JSON Path-like expression, specifying what item (or items) to match & iterate over
        with_path: whether to yield accurate, JSON Path-like pointer objects to items found
        lenient: whether to allow out of bound indices or missing keys, or raise ``IndexError`` and
            ``KeyError`` exceptions, respectivately.
    """
    all_accessors = list(path._accessors())
    stack = [(root_data, all_accessors, JP if with_path else None)]

    while len(stack) > 0:
        data, accessors, current_accessor = stack.pop()
        if len(accessors) == 0:  # leaf item
            if with_path:
                yield current_accessor, data
            else:
                yield data
        else:
            accessor = accessors[0]

            # With a stack content [...] and items A, B, C iterated by accessor._access(...)
            # we want the following stack content: [..., C*, B*, A*]
            # - where A*, B*, C* are tuples created for A, B, C respectively
            # the point is that we want to process, in the next loop, in the order A*. B*, C*.
            #
            # We don't want to do an equivalent `for ... in reversed(list(accessor._access(...))):`,
            # as reversal requires constructing a full list first in order to reverse the order.
            #
            # Inserting into the Nth position (N is current length of stack) achieves the same.
            stack_insert_position = len(stack)
            sub_tuples = accessor._access(data, yield_path=with_path, lenient=lenient)  # type: ignore
            for sub_data, accessor_ctor in sub_tuples:
                new_accessor = accessor_ctor(current_accessor) if accessor_ctor is not None else None  # type: ignore
                stack.insert(
                    stack_insert_position, (sub_data, accessors[1:], new_accessor)
                )


def find_next(
    root_data: list | dict | str | int | float | bool,
    path: _Accessor,
    *,
    with_path: bool = False,
    **kwargs,
):
    """
    Shorthand for ``next(find_all(...))``. Also takes a keyword argument, ``default``,
    to delegate it to the ``next(..., default=...)`` call, if defined.
    """
    if "default" in kwargs:
        default = kwargs["default"]
        try:
            # we don't want to pass the default value as `next(..., default)` ...
            return next(find_all(root_data, path, with_path=with_path, lenient=True))
        except StopIteration:
            # ... because we need to return None for path, if with_path=True
            return (None, default) if with_path else default
    else:
        return next(find_all(root_data, path, with_path=with_path))


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
