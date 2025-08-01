"""
Infra for JSON Path-like expressions and finding items in data hiearchy.
"""

# pylint: disable=protected-access
from __future__ import annotations

import dataclasses as dc
import json
import re
from abc import ABC, abstractmethod
from json import JSONDecodeError
from typing import Any, Callable, Iterator


@dc.dataclass(frozen=True, kw_only=True)
class _Predicate(ABC):
    """
    Abstract base class for predicate based list-item selection.
    """

    @abstractmethod
    def _evaluate(self, content) -> bool:
        """
        Evaluates this predicate within the context of the given content.
        """


@dc.dataclass(frozen=True, kw_only=True, eq=True)
class _BinaryPredicate(_Predicate):
    """
    Binary predicate for predicate based list-item selection.
    """

    operand1: _Accessor
    operand2: Any
    func: Callable[[Any, Any], bool] = dc.field(compare=False)
    repr_template: str  # format string referring to '{op1}' and '{op2}' variables

    def _evaluate(self, content) -> bool:
        non_existent = (1,)
        operand1 = find_next(content, self.operand1, default=non_existent)
        operand2 = (
            find_next(content, self.operand2, default=non_existent)
            if isinstance(self.operand2, _Accessor)
            else self.operand2
        )
        if (operand1 is non_existent) or (operand2 is non_existent):
            return False
        if operand1 is None and operand2 is None:
            return True
        if operand1 is None or operand2 is None:
            return False
        return self.func(operand1, operand2)

    def __bool__(self):
        """
        BinaryPredicate is primarily to serve as an infra for expressions like
        ``JP[JP.field1 == JP.field2]``. But what if someone just wants to test for
        path equivalence, like ``JP.field1 == JP.field2`` or ``JP.field1 != JP.field2``?
        Then this converter dunder method kicks in.
        """
        if "==" in self.repr_template:
            return str(self.operand1) == str(self.operand2)
        if "!=" in self.repr_template:
            return str(self.operand1) != str(self.operand2)
        raise NotImplementedError("Unsupported comparison of paths")

    def __str__(self) -> str:
        op1 = f"?{self.operand1._json_path_like(child_context=True)}"
        if isinstance(self.operand2, _Accessor):
            op2 = f"?{self.operand2._json_path_like(child_context=True)}"
        else:
            op2 = json.dumps(self.operand2)
        return self.repr_template.format(op1=op1, op2=op2)


_BINARY_PREDICATE_ARGS = {
    "==": {
        "func": (lambda x, y: x == y),
        "repr_template": "{op1} == {op2}",
    },
    "!=": {
        "func": (lambda x, y: x != y),
        "repr_template": "{op1} != {op2}",
    },
    "<": {
        "func": (lambda x, y: x < y),
        "repr_template": "{op1} < {op2}",
    },
    "<=": {
        "func": (lambda x, y: x <= y),
        "repr_template": "{op1} <= {op2}",
    },
    ">": {
        "func": (lambda x, y: x > y),
        "repr_template": "{op1} > {op2}",
    },
    ">=": {
        "func": (lambda x, y: x >= y),
        "repr_template": "{op1} >= {op2}",
    },
}


@dc.dataclass(frozen=True, kw_only=True)
class _PathExistsPredicate(_Predicate):
    """
    A unary predicate telling if a sub-path exists, for predicate based list-item selection.
    """

    path: _Accessor

    def _evaluate(self, content) -> bool:
        non_existent = (1,)

        found = find_next(content, self.path, default=non_existent)
        return found is not non_existent

    def __str__(self):
        return f"?{self.path._json_path_like(child_context=True)}"


@dc.dataclass(frozen=True, kw_only=True)
class _Accessor:
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
        raise NotImplementedError("Should not be invoked")

    def _access_or_insert(
        self, container: list | dict, is_penultimate: bool, insert_fun: Callable
    ):
        """
        Similar to ``_access()``, except this one is used for in-place modification of
        data.

        Args:
            container: the structure (list or dict) being accessed (or inserted into)
            is_penultimate: whether this structure (list or dict) is the last-but-one
            segment in the JSON Path-like expression, i.e. the immediate parent of
            a leaf data being inserted into.
            insert_fun: a unary function providing the new value to insert, the argument
                is the current value if exists, or ``None`` otherwise

        Returns:
            An iterator of child structures to further descend into with the JSON Path
            if is_penultimate=False, or the (newly) inserted leaf values if
            is_penultimate=True.
        """
        raise NotImplementedError("Should not be invoked")

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
        return self._json_path_like()

    def _json_path_like(self, child_context: bool = False):
        """
        A (best effort attempt) to render the path, made up
        by this accessor and its parents, transitively, as a JSON Path.

        Args:
            child_context: JSON Path uses marker "$" for paths starting
            from document root, and "@" for paths starting from a child
            node. This flag controls which context to build the string for.
        """
        accessors = self._accessors()
        marker = "@" if child_context else "$"
        return marker + "".join(a._representation() for a in accessors)

    def __getattr__(self, specification):
        """
        JSON Path-like expression builder infra.

        Overloaded for dict key access.
        """
        return _DictKeyAccessor(parent=self, key=specification)

    def __getitem__(self, specification):  # pylint: disable=too-many-return-statements
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
        if isinstance(specification, _Accessor):
            return _ListPredicateAccessor(
                parent=self, predicate=_PathExistsPredicate(path=specification)
            )
        if isinstance(specification, _Predicate):
            return _ListPredicateAccessor(parent=self, predicate=specification)
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
                parent=self,
                sub_accessors=paths,
                sub_hierarchy_ctor=tuple,
                field_name_mapping=tuple(),
            )
        if len(named_paths) > 0:
            paths = list(named_paths.values())
            verify_paths(paths)
            return _SubHiearchyAccessor(
                parent=self,
                sub_accessors=paths,
                sub_hierarchy_ctor=lambda values: dict(zip(named_paths.keys(), values)),
                field_name_mapping=tuple(named_paths.keys()),
            )
        raise NotImplementedError("Sub-selection cannot be empty")

    def __eq__(self, other):
        return _BinaryPredicate(
            operand1=self,
            operand2=other,
            **_BINARY_PREDICATE_ARGS["=="],
        )

    def __ne__(self, other):
        return _BinaryPredicate(
            operand1=self,
            operand2=other,
            **_BINARY_PREDICATE_ARGS["!="],
        )

    def __gt__(self, other):
        return _BinaryPredicate(
            operand1=self,
            operand2=other,
            **_BINARY_PREDICATE_ARGS[">"],
        )

    def __ge__(self, other):
        return _BinaryPredicate(
            operand1=self,
            operand2=other,
            **_BINARY_PREDICATE_ARGS[">="],
        )

    def __lt__(self, other):
        return _BinaryPredicate(
            operand1=self,
            operand2=other,
            **_BINARY_PREDICATE_ARGS["<"],
        )

    def __le__(self, other):
        return _BinaryPredicate(
            operand1=self,
            operand2=other,
            **_BINARY_PREDICATE_ARGS["<="],
        )


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

    def _access_or_insert(
        self, container: list | dict, is_penultimate: bool, insert_fun: Callable
    ):
        self._check_container_type(container)
        if self.key not in container or is_penultimate:
            container[self.key] = insert_fun(container.get(self.key, None))  # type: ignore

        yield container[self.key]  # type: ignore

    def _representation(self) -> str:
        return f".{self.key}"

    def __eq__(self, other):
        """
        Overloaded == operator in the superclass does not work in sub-classes.
        Other operators don't seem to have any trouble.
        """
        return _BinaryPredicate(
            operand1=self,
            operand2=other,
            **_BINARY_PREDICATE_ARGS["=="],
        )


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

    def _access_or_insert(
        self, container: list | dict, is_penultimate: bool, insert_fun: Callable
    ):
        self._check_container_type(container)
        for key in container.keys():  # type: ignore
            if self.key_regex.findall(key):  # pylint: disable=no-member
                if is_penultimate:
                    container[key] = insert_fun(container[key])
                yield container[key]

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

    def _access_or_insert(
        self, container: list | dict, is_penultimate: bool, insert_fun: Callable
    ):
        self._check_container_type(container)
        if self.index == len(container):
            container.append(insert_fun(None))  # type: ignore
        elif self.index < len(container):
            if is_penultimate:
                container[self.index] = insert_fun(container[self.index])
            else:
                pass
        else:
            raise ValueError(
                f"Cannot append at {self.index} to a list with length {len(container)}"
            )
        yield container[self.index]

    def _representation(self) -> str:
        return f"[{self.index}]"

    def __eq__(self, other):
        """
        Overloaded == operator in the superclass does not work in sub-classes.
        Other operators don't seem to have any trouble.
        """
        return _BinaryPredicate(
            operand1=self,
            operand2=other,
            **_BINARY_PREDICATE_ARGS["=="],
        )


def _create_list_idx_accessor_ctor(index: int) -> _Accessor:
    return lambda parent: _ListIndexAccessor(parent=parent, index=index)  # type: ignore


@dc.dataclass(frozen=True, kw_only=True)
class _ListPredicateAccessor(_Accessor):
    """Accesses items of a list by a predicate"""

    predicate: _Predicate
    container_type: type = list

    def _is_singular(self) -> bool:
        return False

    def _access(
        self, container: list | dict, *, yield_path: bool = False, lenient: bool = False
    ) -> Iterator[tuple[Any, Callable[[_Accessor], _Accessor] | None]]:
        _ = lenient  # unused
        self._check_container_type(container)
        if yield_path:

            yield from (
                (item, _create_list_idx_accessor_ctor(current_index))
                for current_index, item in enumerate(container)
                if self.predicate._evaluate(item)
            )
        else:
            yield from (
                (item, None) for item in container if self.predicate._evaluate(item)
            )

    def _access_or_insert(
        self, container: list | dict, is_penultimate: bool, insert_fun: Callable
    ):
        self._check_container_type(container)
        if is_penultimate:
            for index, item in enumerate(container):
                if self.predicate._evaluate(item):
                    container[index] = insert_fun(container[index])
                    yield container[index]
        else:
            yield from (item for item in container if self.predicate._evaluate(item))

    def _representation(self) -> str:
        return f"[{self.predicate}]"

    def __eq__(self, other):
        """
        Overloaded == operator in the superclass does not work in sub-classes.
        Other operators don't seem to have any trouble.
        """
        return _BinaryPredicate(
            operand1=self,
            operand2=other,
            **_BINARY_PREDICATE_ARGS["=="],
        )


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
            slice_indices = self.slice_.indices(len(container))

            yield from (
                (item, _create_list_idx_accessor_ctor(current_index))
                for current_index, item in zip(
                    range(slice_indices[0], slice_indices[1], slice_indices[2]),
                    container[self.slice_],
                )
            )
        else:
            yield from ((item, None) for item in container[self.slice_])

    def _access_or_insert(
        self, container: list | dict, is_penultimate: bool, insert_fun: Callable
    ):
        self._check_container_type(container)
        if is_penultimate:
            slice_indices = self.slice_.indices(len(container))
            for index in range(slice_indices[0], slice_indices[1], slice_indices[2]):
                container[index] = insert_fun(container[index])
                yield container[index]
        else:
            yield from container[self.slice_]

    def _representation(self) -> str:
        repr_ = (
            (f"[{self.slice_.start}" if self.slice_.start is not None else "[")
            + (f":{self.slice_.stop}" if self.slice_.stop is not None else ":")
            + (f":{self.slice_.step}]" if self.slice_.step is not None else "]")
        )
        return repr_

    def __eq__(self, other):
        """
        Overloaded == operator in the superclass does not work in sub-classes.
        Other operators don't seem to have any trouble.
        """
        return _BinaryPredicate(
            operand1=self,
            operand2=other,
            **_BINARY_PREDICATE_ARGS["=="],
        )


@dc.dataclass(frozen=True, kw_only=True)
class _SubHiearchyAccessor(_Accessor):
    """
    Instead of returning an entire item (of a list), it constructs a tuple based on sub-JSON Path-like expressions.
    """

    sub_accessors: list[_Accessor]
    sub_hierarchy_ctor: Callable
    container_type: type = dict
    field_name_mapping: tuple[str, ...]

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
            yield self.sub_hierarchy_ctor(items), lambda parent: _SubHiearchyAccessor(
                parent=parent,
                sub_accessors=self.sub_accessors,
                sub_hierarchy_ctor=self.sub_hierarchy_ctor,
                field_name_mapping=self.field_name_mapping,
            )
        else:
            yield self.sub_hierarchy_ctor(items), None

    def _access_or_insert(
        self, container: list | dict, is_penultimate: bool, insert_fun: Callable
    ):
        self._check_container_type(container)
        for accessor in self.sub_accessors:
            if (
                not isinstance(accessor, _DictKeyAccessor)
                or len(accessor._accessors()) > 2
            ):
                raise ValueError(f"Unsupported mutator in sub-hierarchy: {accessor}")

        values = insert_fun(container)
        if len(values) != len(self.sub_accessors):
            raise ValueError(
                f"Value count ({len(values)}) != specs count ({len(self.sub_accessors)})"
            )

        for sub_accessor, value in zip(self.sub_accessors, values):
            if sub_accessor.key not in container or is_penultimate:
                container[sub_accessor.key] = value

        yield values

    def _representation(self):
        sub_paths = [
            sub_acc._json_path_like(child_context=True)
            for sub_acc in self.sub_accessors
        ]
        if self.field_name_mapping:
            assert len(self.field_name_mapping) == len(self.sub_accessors)
            expression = ", ".join(
                (
                    f"{name}={sub_path}"
                    for name, sub_path in zip(self.field_name_mapping, sub_paths)
                )
            )
        else:
            expression = ", ".join(sub_paths)
        # return f"({', '.join(sub_paths)})"
        return f"({expression})"

    def __eq__(self, other):
        """
        Overloaded == operator in the superclass does not work in sub-classes.
        Other operators don't seem to have any trouble.
        """
        return _BinaryPredicate(
            operand1=self,
            operand2=other,
            **_BINARY_PREDICATE_ARGS["=="],
        )


JP = _Accessor(parent=None, container_type=type(None))


def _parse_operand(operand: str) -> None | str | int | float | bool | _Accessor:
    if operand.startswith("?@"):
        path_maybe = operand.replace("?@", "$", 1)
        return parse(path_maybe)

    try:
        value = json.loads(operand)
        return value
    except JSONDecodeError as err:
        raise ValueError(f"{operand} is not a JSON value") from err


PATTERN_SEGMENT = re.compile(
    """
        \\[(?P<slice1_stop>-?\\d+)]
        | \\[(?P<slice2>(?P<slice2_start>-?\\d+)?:(?P<slice2_stop>-?\\d+)?)]
        | \\[(?P<star>\\*)]
        | \\[(?P<slice3>(?P<slice3_start>-?\\d+)?:(?P<slice3_stop>-?\\d+)?:(?P<slice3_step>-?\\d+)?)]
        | \\[(?P<tested_path>\\?@[^ ]+)]
        | \\[(?P<operand1>[^ ]+)\\ *(?P<operator><=|>=|==|!=|<|>)\\ *(?P<operand2>.+)]
        | \\.(?P<field>[^.[(]+)
        | \\[(?P<regex>.*)]
        | \\((?P<subitems>[^=]+)\\)
        | \\((?P<named_subitems>(.*=.*)+)\\)
    """,
    re.VERBOSE,
)


def parse(  # pylint: disable=too-many-locals,too-many-branches
    json_path: str,
) -> _Accessor:
    """
    Parses a stringified form of a JSON Path-like object. There is an overlap with
    standard JSON Path expressions, but there are JSON Path expressions not supported by
    this library and features of this library which are not standard JSON Path expressions.
    """
    if not json_path.startswith(("$", "@")):
        raise ValueError("TODO")

    accessor = JP

    path = json_path[1:]

    for segment_match in PATTERN_SEGMENT.finditer(path):
        if field := segment_match.group("field"):
            accessor = accessor[field]
        elif slice1_stop := segment_match.group("slice1_stop"):
            accessor = accessor[int(slice1_stop)]
        elif segment_match.group("slice2"):
            start = segment_match.group("slice2_start")
            stop = segment_match.group("slice2_stop")
            s = slice(int(start) if start else None, int(stop) if stop else None)
            accessor = accessor[s]
        elif segment_match.group("slice3"):
            start = segment_match.group("slice3_start")
            stop = segment_match.group("slice3_stop")
            step = segment_match.group("slice3_step")
            s = slice(
                int(start) if start else None,
                int(stop) if stop else None,
                int(step) if step else None,
            )
            accessor = accessor[s]
        elif tested_path := segment_match.group("tested_path"):
            path = _parse_operand(tested_path)  # type: ignore
            predicate = _PathExistsPredicate(path=path)  # type: ignore
            accessor = accessor[predicate]
        elif operator := segment_match.group("operator"):
            operand1 = _parse_operand(segment_match.group("operand1"))
            operand2 = _parse_operand(segment_match.group("operand2"))
            predicate = _BinaryPredicate(
                operand1=operand1, operand2=operand2, **_BINARY_PREDICATE_ARGS[operator]  # type: ignore
            )
            accessor = accessor[predicate]
        elif segment_match.group("star"):
            accessor = accessor[:]
        elif regex := segment_match.group("regex"):
            _ = re.compile(regex)
            accessor = accessor[regex]
        elif subitems := segment_match.group("subitems"):
            subitem_list = [parse(subitem.strip()) for subitem in subitems.split(",")]
            accessor = accessor(*subitem_list)
        elif named_subitems := segment_match.group("named_subitems"):
            key_value_pattern = re.compile("(?P<key>\\w+)\\s*=\\s*(?P<value>\\S+)")
            named_subitem_list = {
                match["key"]: parse(match["value"])
                for named_subitem in named_subitems.split(",")
                if (match := key_value_pattern.match(named_subitem.strip()))
            }
            accessor = accessor(**named_subitem_list)
        else:
            raise ValueError("TODO")

    return accessor


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
