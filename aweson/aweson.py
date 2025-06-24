from __future__ import annotations
from abc import ABC
from collections import namedtuple
import dataclasses as dc
from typing import Any

@dc.dataclass(frozen=True, kw_only=True)
class _Accessor(ABC):
    """
    Base class for building JSON Path-like expression.
    """
    parent: _Accessor | None
    container_type: type

    def _access(self, container: list | dict, singular_path: bool = False):
        """
        Yields one or more tuples of sub-item + a CTOR function to build a JSON Path-like representtion
        to access that sub-item.
        """
        pass

    def _representation(self) -> str:
        return ""

    def _check_container_type(self, container: list | dict):
        if not isinstance(container, self.container_type):
            raise ValueError(f"Expected {self.container_type}, got {type(container)} at {self}")

    def _accessors(self) -> list[_Accessor]:
        if self.parent is None:
            # Symmetry would suggest here to `return [self]`, however,
            # we cheat here: this instance shall be the root (=first accessor
            # to traverse by), not the parent
            return []
        return self.parent._accessors() + [self]

    def __str__(self):
        accessors = self._accessors()
        return "".join(a._representation() for a in accessors)

    def __getattr__(self, specification):
        return _DictKeyAccessor(parent=self, key=specification)

    def __getitem__(self, specification):
        if isinstance(specification, str):
            return _DictKeyAccessor(parent=self, key=specification)
        if isinstance(specification, int):
            return _ListIndexAccessor(parent=self, index=specification)
        if isinstance(specification, slice):
            return _ListSliceAccessor(parent=self, slice_=specification)
        raise ValueError(f"Unsupported indexing expression {specification}")

    def __call__(self, *paths, **named_paths):
        if len(paths) > 0 and len(named_paths) > 0:
            raise NotImplementedError("Either all sub-selections are to be named, or none of them.")
        elif len(paths) > 0:
            if any(not isinstance(path, _Accessor) for path in paths):  # TODO consider checking is_singular
                raise ValueError("Need path notation to dig out tuples from sub-hierarchies")
            return _SubHiearchyAccessor(parent=self, sub_accessors=paths, tuple_ctor=lambda values: tuple(values))
        elif len(named_paths) > 0:
            paths = list(named_paths.values())
            if any(not isinstance(path, _Accessor) for path in paths):  # TODO consider checking is_singular
                raise ValueError("Need path notation to dig out tuples from sub-hierarchies")
            named_tuple = namedtuple('SubSelect', list(named_paths.keys()))
            return _SubHiearchyAccessor(parent=self, sub_accessors=paths, tuple_ctor=lambda values: named_tuple(*values))
        raise NotImplementedError("Sub-selection cannot be empty")


@dc.dataclass(frozen=True, kw_only=True)
class _DictKeyAccessor(_Accessor):
    """Accesses a value of a dict container by a key"""
    key: str
    container_type: type = dict

    def _access(self, container: list | dict, singular_path: bool = False):
        self._check_container_type(container)
        if singular_path:
            yield container[self.key], (lambda parent: _DictKeyAccessor(parent=parent, key=self.key))
        else:
            yield container[self.key], None

    def _representation(self) -> str:
        return f".{self.key}"


@dc.dataclass(frozen=True, kw_only=True)
class _ListIndexAccessor(_Accessor):
    """Accesses an item of a list by an index"""
    index: int
    container_type: type = list

    def _access(self, container: list | dict, singular_path: bool = False):
        self._check_container_type(container)
        if singular_path:
            if self.index >= 0:
                yield container[self.index], (lambda parent: _ListIndexAccessor(parent=parent, index=self.index))
            else:
                yield container[self.index], (lambda parent: _ListIndexAccessor(parent=parent, index=len(container) + self.index))
        else:
            yield container[self.index], None

    def _representation(self) -> str:
        return f"[{self.index}]"


@dc.dataclass(frozen=True, kw_only=True)
class _ListSliceAccessor(_Accessor):
    """Accesses items of a list by a slice"""
    slice_: slice
    container_type: type = list

    def _access(self, container: list | dict, singular_path: bool = False):
        self._check_container_type(container)
        if singular_path:
            def create_accessor_ctor(index: int) -> _Accessor:
                return (lambda parent: _ListIndexAccessor(parent=parent, index=index))

            slice_indices = self.slice_.indices(len(container))

            for current_index, item in zip(range(slice_indices[0], slice_indices[1], slice_indices[2]), container[self.slice_]):
                yield item, create_accessor_ctor(current_index)
        else:
            yield from ((item, None) for item in container[self.slice_])

    def _representation(self) -> str:
        repr = (f"[{self.slice_.start}" if self.slice_.start is not None else "[") \
            + (f":{self.slice_.stop}" if self.slice_.stop is not None else ":") \
            + (f":{self.slice_.step}]" if self.slice_.step is not None else "]")
        return repr


@dc.dataclass(frozen=True, kw_only=True)
class _SubHiearchyAccessor(_Accessor):
    """
    Instead of returning an entire item (of a list), it constructs a tuple based on sub-JSON Path-like expressions.
    """
    sub_accessors: list[_Accessor]
    tuple_ctor: Any
    container_type: type = list

    def _access(self, container: list | dict, singular_path: bool = False):
        items = [next(find_all(container, sub_accessor)) for sub_accessor in self.sub_accessors]
        if singular_path:
            yield self.tuple_ctor(items), (lambda parent: _SubHiearchyAccessor(parent=parent, sub_accessors=self.sub_accessors, tuple_ctor=self.tuple_ctor))
        else:
            yield self.tuple_ctor(items), None

    def _representation(self):
        return f"({', '.join(str(sub_accessor) for sub_accessor in self.sub_accessors)})"


JP = _Accessor(parent=None, container_type=type(None))


def find_all(
        root_data: list | dict | str | int | float | bool,
        path: _Accessor,
        enumerate: bool = False):
    """
    Finds all matching items in a JSON-like data hierarchy (lists of / dicts of / values) based
    on a JSON Path-like specification.

    Technically, it iterates over the matching items.

    If `enumerate` is False (default), then it will yield the matching items only.

    If `enumerate` is True, then it will yield a tuple of JSON Path-like pointer to a matching item +
    the matching item itself. Just like `enumerate(your_list)` yields index + item tuples, where the
    index points to the item in `your_list`, similarly, `find_all(..., ..., enumerate=True)` yields
    a path + item tuples, where path points at the item itself.
    """
    all_accessors = list(path._accessors())
    stack = [(root_data, all_accessors, JP)]

    while len(stack) > 0:
        data, accessors, current_accessor = stack.pop()
        if len(accessors) == 0:  # leaf item
            if enumerate:
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
            for sub_data, accessor_ctor in accessor._access(data, singular_path=enumerate):
                stack.insert(stack_insert_position, (sub_data, accessors[1:], accessor_ctor(current_accessor) if accessor_ctor else None ))
