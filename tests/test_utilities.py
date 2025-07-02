from itertools import count

import pytest

from aweson import JP, find_all_duplicate, find_all_unique, with_values

###############################################################
#
# find_all_unique()
#


@pytest.mark.parametrize(
    "content,jp,with_path,expected_items",
    [
        ([1, 2, 1, 3, -22, 3], JP[:], False, [1, 2, 3, -22]),
        (
            [1, 2, 1, 3, -22, 3],
            JP[:],
            True,
            [(JP[0], 1), (JP[1], 2), (JP[3], 3), (JP[4], -22)],
        ),
        (
            [
                {"hello": 1},
                {"hello": 2},
                {"hello": 1},
                {"hello": 3},
                {"hello": -22},
                {"hello": 3},
            ],
            JP[:].hello,
            False,
            [1, 2, 3, -22],
        ),
        (
            [
                {"hello": 1},
                {"hello": 2},
                {"hello": 1},
                {"hello": 3},
                {"hello": -22},
                {"hello": 3},
            ],
            JP[:].hello,
            True,
            [(JP[0].hello, 1), (JP[1].hello, 2), (JP[3].hello, 3), (JP[4].hello, -22)],
        ),
        (
            [
                {"hello": 1},
                {"hello": 2},
                {"hello": 1},
                {"hello": 3},
                {"hello": -22},
                {"hello": 3},
            ],
            JP[:4].hello,
            False,
            [1, 2, 3],
        ),
        (
            [
                {"hello": 1},
                {"hello": 2},
                {"hello": 1},
                {"hello": 3},
                {"hello": -22},
                {"hello": 3},
            ],
            JP[:4].hello,
            True,
            [(JP[0].hello, 1), (JP[1].hello, 2), (JP[3].hello, 3)],
        ),
    ],
)
def test_find_all_unique(content, jp, with_path, expected_items):
    items = list(find_all_unique(content, jp, with_path=with_path))
    assert items == expected_items


###############################################################
#
# find_all_duplicate()
#


@pytest.mark.parametrize(
    "content,jp,with_path,expected_items",
    [
        ([1, 2, 1, 3, -22, 3], JP[:], False, [1, 3]),
        ([1, 2, 1, 3, -22, 3], JP[:], True, [(JP[2], 1), (JP[5], 3)]),
        (
            [
                {"hello": 1},
                {"hello": 2},
                {"hello": 1},
                {"hello": 3},
                {"hello": -22},
                {"hello": 3},
            ],
            JP[:].hello,
            False,
            [1, 3],
        ),
        (
            [
                {"hello": 1},
                {"hello": 2},
                {"hello": 1},
                {"hello": 3},
                {"hello": -22},
                {"hello": 3},
            ],
            JP[:].hello,
            True,
            [(JP[2].hello, 1), (JP[5].hello, 3)],
        ),
        (
            [
                {"hello": 1},
                {"hello": 2},
                {"hello": 1},
                {"hello": 3},
                {"hello": -22},
                {"hello": 3},
            ],
            JP[:3].hello,
            False,
            [1],
        ),
        (
            [
                {"hello": 1},
                {"hello": 2},
                {"hello": 1},
                {"hello": 3},
                {"hello": -22},
                {"hello": 3},
            ],
            JP[:3].hello,
            True,
            [(JP[2].hello, 1)],
        ),
    ],
)
def test_find_all_duplicates(content, jp, with_path, expected_items):
    items = list(find_all_duplicate(content, jp, with_path=with_path))
    assert items == expected_items


###############################################################
#
# with_values()
#


# mix case: several iterations on different level .foo[:]["h(ello|i)"][.bar == 0] ...
# TODO sub-hierarchy ???


def my_negator(n: int | None):
    """
    Silly negation for tests
    """
    if n is None:
        return -1 / 12
    if isinstance(n, int):
        return -n
    assert False


@pytest.mark.parametrize(
    "content, jp, values, expected_content",
    [
        # VALUES
        # - simple list
        ([11, 12, 13], JP[1], 137, [11, 137, 13]),
        (
            [11, 12, 13],
            JP[1],
            {"hi": 137},
            [11, {"hi": 137}, 13],
        ),
        # - list in the middle of path
        (
            {"hello": [{"hi": 11}, {"hi": 12}, {"hi": 13}]},
            JP.hello[1].hi,
            137,
            {"hello": [{"hi": 11}, {"hi": 137}, {"hi": 13}]},
        ),
        # - list is parent of leaf data
        ({"hello": [11, 12, 13]}, JP.hello[1], 137, {"hello": [11, 137, 13]}),
        # ITERATOR
        # - simple list
        ([11, 12, 13], JP[1], count(37, 1), [11, 37, 13]),
        (
            [11, 12, 13],
            JP[1],
            ({"hi": idx} for idx in count(37, 1)),
            [11, {"hi": 37}, 13],
        ),
        # - list in the middle of path
        (
            {"hello": [{"hi": 11}, {"hi": 12}, {"hi": 13}]},
            JP.hello[1].hi,
            count(37, 1),
            {"hello": [{"hi": 11}, {"hi": 37}, {"hi": 13}]},
        ),
        # - list is parent of leaf data
        ({"hello": [11, 12, 13]}, JP.hello[1], count(37, 1), {"hello": [11, 37, 13]}),
        # FUNCTION
        # - simple list
        ([11, 12, 13], JP[1], my_negator, [11, -12, 13]),
        # - list in the middle of path
        (
            {"hello": [{"hi": 11}, {"hi": 12}, {"hi": 13}]},
            JP.hello[1].hi,
            my_negator,
            {"hello": [{"hi": 11}, {"hi": -12}, {"hi": 13}]},
        ),
        # - list is parent of leaf data
        ({"hello": [11, 12, 13]}, JP.hello[1], my_negator, {"hello": [11, -12, 13]}),
    ],
)
def test_with_values_list_index(content, jp, values, expected_content):
    new_content = with_values(content, jp, values)
    assert new_content == expected_content


@pytest.mark.parametrize(
    "content, jp, values, expected_content",
    [
        # VALUES
        # - simple list
        ([11, 12, 13], JP[:2], 137, [137, 137, 13]),
        ([11, 12, 13], JP[:2], {"hi": 137}, [{"hi": 137}, {"hi": 137}, 13]),
        # - list in the middle of path
        (
            {"hello": [{"hi": 11}, {"hi": 12}, {"hi": 13}]},
            JP.hello[:2].hi,
            137,
            {"hello": [{"hi": 137}, {"hi": 137}, {"hi": 13}]},
        ),
        # - list is parent of leaf data
        ({"hello": [11, 12, 13]}, JP.hello[:2], 137, {"hello": [137, 137, 13]}),
        # ITERATOR
        # - simple list
        ([11, 12, 13], JP[:2], count(37, 1), [37, 38, 13]),
        (
            [11, 12, 13],
            JP[:2],
            ({"hi": idx} for idx in count(37, 1)),
            [{"hi": 37}, {"hi": 38}, 13],
        ),
        # - list in the middle of path
        (
            {"hello": [{"hi": 11}, {"hi": 12}, {"hi": 13}]},
            JP.hello[:2].hi,
            count(37, 1),
            {"hello": [{"hi": 37}, {"hi": 38}, {"hi": 13}]},
        ),
        # - list is parent of leaf data
        ({"hello": [11, 12, 13]}, JP.hello[:2], count(37, 1), {"hello": [37, 38, 13]}),
        # FUNCTION
        # - simple list
        ([11, 12, 13], JP[:2], my_negator, [-11, -12, 13]),
        # - list in the middle of path
        (
            {"hello": [{"hi": 11}, {"hi": 12}, {"hi": 13}]},
            JP.hello[:2].hi,
            my_negator,
            {"hello": [{"hi": -11}, {"hi": -12}, {"hi": 13}]},
        ),
        # - list is parent of leaf data
        ({"hello": [11, 12, 13]}, JP.hello[:2], my_negator, {"hello": [-11, -12, 13]}),
    ],
)
def test_with_values_list_slices(content, jp, values, expected_content):
    new_content = with_values(content, jp, values)
    assert new_content == expected_content


@pytest.mark.parametrize(
    "content, jp, values, expected_content",
    [
        # VALUES
        # - simple list
        #   - field existence
        (
            [
                {"foo": 10, "hola": 5},
                {"foo": 1, "hola": -42},
                {"foo": 2},
                {"foo": 3, "hola": None},
            ],
            JP[JP.hola].foo,
            137,
            [
                {"foo": 137, "hola": 5},
                {"foo": 137, "hola": -42},
                {"foo": 2},
                {"foo": 137, "hola": None},
            ],
        ),
        (
            [
                {"foo": 10, "hola": 5},
                {"foo": 1, "hola": -42},
                {"foo": 2},
                {"foo": 3, "hola": None},
            ],
            JP[JP.hola].foo,
            {"hi": 137},
            [
                {"foo": {"hi": 137}, "hola": 5},
                {"foo": {"hi": 137}, "hola": -42},
                {"foo": 2},
                {"foo": {"hi": 137}, "hola": None},
            ],
        ),
        #   - simple relational operator
        (
            [{"foo": 10, "hola": 5}, {"foo": 1, "hola": -42}, {"foo": 2}],
            JP[JP.hola < 0].foo,
            137,
            [{"foo": 10, "hola": 5}, {"foo": 137, "hola": -42}, {"foo": 2}],
        ),
        (
            [{"foo": 10, "hola": 5}, {"foo": 1, "hola": -42}, {"foo": 2}],
            JP[JP.hola < 0].foo,
            {"hi": 137},
            [{"foo": 10, "hola": 5}, {"foo": {"hi": 137}, "hola": -42}, {"foo": 2}],
        ),
        # - list in the middle of path
        #   - field existence
        (
            {
                "hello": [
                    {"foo": 10, "hola": 5},
                    {"foo": 1, "hola": -42},
                    {"foo": 2},
                    {"foo": 3, "hola": None},
                ]
            },
            JP.hello[JP.hola].foo,
            137,
            {
                "hello": [
                    {"foo": 137, "hola": 5},
                    {"foo": 137, "hola": -42},
                    {"foo": 2},
                    {"foo": 137, "hola": None},
                ]
            },
        ),
        #   - simple relational operator
        (
            {"hello": [{"foo": 10, "hola": 5}, {"foo": 1, "hola": -42}, {"foo": 2}]},
            JP.hello[JP.hola < 0].foo,
            137,
            {"hello": [{"foo": 10, "hola": 5}, {"foo": 137, "hola": -42}, {"foo": 2}]},
        ),
        # ITERATOR
        # - simple list: (a) field existence, (b) simple relational operator
        #   - field existence
        (
            [
                {"foo": 10, "hola": 5},
                {"foo": 1, "hola": -42},
                {"foo": 2},
                {"foo": 3, "hola": None},
            ],
            JP[JP.hola].foo,
            count(37, 1),
            [
                {"foo": 37, "hola": 5},
                {"foo": 38, "hola": -42},
                {"foo": 2},
                {"foo": 39, "hola": None},
            ],
        ),
        #   - simple relational operator
        (
            [{"foo": 10, "hola": 5}, {"foo": 1, "hola": -42}, {"foo": 2}],
            JP[JP.hola < 0].foo,
            count(37, 1),
            [{"foo": 10, "hola": 5}, {"foo": 37, "hola": -42}, {"foo": 2}],
        ),
        # - list in the middle of path
        #   - field existence
        (
            {
                "hello": [
                    {"foo": 10, "hola": 5},
                    {"foo": 1, "hola": -42},
                    {"foo": 2},
                    {"foo": 3, "hola": None},
                ]
            },
            JP.hello[JP.hola].foo,
            count(37, 1),
            {
                "hello": [
                    {"foo": 37, "hola": 5},
                    {"foo": 38, "hola": -42},
                    {"foo": 2},
                    {"foo": 39, "hola": None},
                ]
            },
        ),
        #   - simple relational operator
        (
            {"hello": [{"foo": 10, "hola": 5}, {"foo": 1, "hola": -42}, {"foo": 2}]},
            JP.hello[JP.hola < 0].foo,
            count(37, 1),
            {"hello": [{"foo": 10, "hola": 5}, {"foo": 37, "hola": -42}, {"foo": 2}]},
        ),
        # FUNCTION
        # - simple list
        #   - field existence
        (
            [
                {"foo": 10, "hola": 5},
                {"foo": 1, "hola": -42},
                {"foo": 2},
                {"foo": 3, "hola": None},
            ],
            JP[JP.hola].foo,
            my_negator,
            [
                {"foo": -10, "hola": 5},
                {"foo": -1, "hola": -42},
                {"foo": 2},
                {"foo": -3, "hola": None},
            ],
        ),
        #   - simple relational operator
        (
            [{"foo": 10, "hola": 5}, {"foo": 1, "hola": -42}, {"foo": 2}],
            JP[JP.hola < 0].foo,
            my_negator,
            [{"foo": 10, "hola": 5}, {"foo": -1, "hola": -42}, {"foo": 2}],
        ),
        # - list in the middle of path
        #   - field existence
        (
            {
                "hello": [
                    {"foo": 10, "hola": 5},
                    {"foo": 1, "hola": -42},
                    {"foo": 2},
                    {"foo": 3, "hola": None},
                ]
            },
            JP.hello[JP.hola].foo,
            my_negator,
            {
                "hello": [
                    {"foo": -10, "hola": 5},
                    {"foo": -1, "hola": -42},
                    {"foo": 2},
                    {"foo": -3, "hola": None},
                ]
            },
        ),
        #   - simple relational operator
        (
            {"hello": [{"foo": 10, "hola": 5}, {"foo": 1, "hola": -42}, {"foo": 2}]},
            JP.hello[JP.hola < 0].foo,
            my_negator,
            {"hello": [{"foo": 10, "hola": 5}, {"foo": -1, "hola": -42}, {"foo": 2}]},
        ),
    ],
)
def test_with_values_attribute_predicates(content, jp, values, expected_content):
    new_content = with_values(content, jp, values)
    assert new_content == expected_content


@pytest.mark.parametrize(
    "content, jp, values, expected_content",
    [
        # VALUES
        # - simple dict
        (
            {"hello": 5, "hi": 42},
            JP.hello,
            137,
            {"hello": 137, "hi": 42},
        ),
        # - dict in middle of the path
        (
            [{"hello": 5, "hi": 42}, {"hello": 29, "hi": 144}],
            JP[:].hello,
            137,
            [{"hello": 137, "hi": 42}, {"hello": 137, "hi": 144}],
        ),
        # - dict is parent of leaf data
        (
            {"foo": [{"hello": 5, "hi": 42}, {"hello": 29, "hi": 144}]},
            JP.foo[:].hello,
            137,
            {"foo": [{"hello": 137, "hi": 42}, {"hello": 137, "hi": 144}]},
        ),
        # ITERATOR
        # - simple dict
        (
            {"hello": 5, "hi": 42},
            JP.hello,
            count(37, 1),
            {"hello": 37, "hi": 42},
        ),
        # - dict in middle of the path
        (
            [{"hello": 5, "hi": 42}, {"hello": 29, "hi": 144}],
            JP[:].hello,
            count(37, 1),
            [{"hello": 37, "hi": 42}, {"hello": 38, "hi": 144}],
        ),
        # - dict is parent of leaf data
        (
            {"foo": [{"hello": 5, "hi": 42}, {"hello": 29, "hi": 144}]},
            JP.foo[:].hello,
            count(37, 1),
            {"foo": [{"hello": 37, "hi": 42}, {"hello": 38, "hi": 144}]},
        ),
        # FUNCTION
        # - simple dict
        (
            {"hello": 5, "hi": 42},
            JP.hello,
            my_negator,
            {"hello": -5, "hi": 42},
        ),
        # - dict in middle of the path
        (
            [{"hello": 5, "hi": 42}, {"hello": 29, "hi": 144}],
            JP[:].hello,
            my_negator,
            [{"hello": -5, "hi": 42}, {"hello": -29, "hi": 144}],
        ),
        # - dict is parent of leaf data
        (
            {"foo": [{"hello": 5, "hi": 42}, {"hello": 29, "hi": 144}]},
            JP.foo[:].hello,
            my_negator,
            {"foo": [{"hello": -5, "hi": 42}, {"hello": -29, "hi": 144}]},
        ),
    ],
)
def test_with_values_dict_key(content, jp, values, expected_content):
    new_content = with_values(content, jp, values)
    assert new_content == expected_content


@pytest.mark.parametrize(
    "content, jp, values, expected_content",
    [
        # VALUES
        # - simple dict
        (
            {"hello": 5, "helsinki": 13, "hi": 42},
            JP["hel.*"],
            137,
            {"hello": 137, "helsinki": 137, "hi": 42},
        ),
        # - dict in middle of the path
        (
            [
                {"hello": 5, "helsinki": 13, "hi": 42},
                {"hello": 29, "helsinki": 19, "hi": 144},
            ],
            JP[:]["hel.*"],
            137,
            [
                {"hello": 137, "helsinki": 137, "hi": 42},
                {"hello": 137, "helsinki": 137, "hi": 144},
            ],
        ),
        # - dict is parent of leaf data
        (
            {
                "foo": [
                    {"hello": 5, "helsinki": 13, "hi": 42},
                    {"hello": 29, "helsinki": 19, "hi": 144},
                ]
            },
            JP.foo[:]["hel.*"],
            137,
            {
                "foo": [
                    {"hello": 137, "helsinki": 137, "hi": 42},
                    {"hello": 137, "helsinki": 137, "hi": 144},
                ]
            },
        ),
        # ITERATOR
        # - simple dict
        (
            {"hello": 5, "helsinki": 13, "hi": 42},
            JP["hel.*"],
            count(37, 1),
            {"hello": 37, "helsinki": 38, "hi": 42},
        ),
        # - dict in middle of the path
        (
            [
                {"hello": 5, "helsinki": 13, "hi": 42},
                {"hello": 29, "helsinki": 19, "hi": 144},
            ],
            JP[:]["hel.*"],
            count(37, 1),
            [
                {"hello": 37, "helsinki": 38, "hi": 42},
                {"hello": 39, "helsinki": 40, "hi": 144},
            ],
        ),
        # - dict is parent of leaf data
        (
            {
                "foo": [
                    {"hello": 5, "helsinki": 13, "hi": 42},
                    {"hello": 29, "helsinki": 19, "hi": 144},
                ]
            },
            JP.foo[:]["hel.*"],
            count(37, 1),
            {
                "foo": [
                    {"hello": 37, "helsinki": 38, "hi": 42},
                    {"hello": 39, "helsinki": 40, "hi": 144},
                ]
            },
        ),
        # FUNCTION
        # - simple dict
        (
            {"hello": 5, "helsinki": 13, "hi": 42},
            JP["hel.*"],
            my_negator,
            {"hello": -5, "helsinki": -13, "hi": 42},
        ),
        # - dict in middle of the path
        (
            [
                {"hello": 5, "helsinki": 13, "hi": 42},
                {"hello": 29, "helsinki": 19, "hi": 144},
            ],
            JP[:]["hel.*"],
            my_negator,
            [
                {"hello": -5, "helsinki": -13, "hi": 42},
                {"hello": -29, "helsinki": -19, "hi": 144},
            ],
        ),
        # - dict is parent of leaf data
        (
            {
                "foo": [
                    {"hello": 5, "helsinki": 13, "hi": 42},
                    {"hello": 29, "helsinki": 19, "hi": 144},
                ]
            },
            JP.foo[:]["hel.*"],
            my_negator,
            {
                "foo": [
                    {"hello": -5, "helsinki": -13, "hi": 42},
                    {"hello": -29, "helsinki": -19, "hi": 144},
                ]
            },
        ),
    ],
)
def test_with_values_dict_regex(content, jp, values, expected_content):
    new_content = with_values(content, jp, values)
    assert new_content == expected_content


@pytest.mark.parametrize(
    "content, jp, values, expected_content",
    [
        # VALUES
        ([], JP[0], 137, [137]),
        ([5], JP[1], 137, [5, 137]),
        ({"hello": [5]}, JP.hello[1], 137, {"hello": [5, 137]}),
        # ITERATOR
        ([], JP[0], count(37, 1), [37]),
        ([5], JP[1], count(37, 1), [5, 37]),
        ({"hello": [5]}, JP.hello[1], count(37, 1), {"hello": [5, 37]}),
        # FUNCTION
        ([], JP[0], my_negator, [-1 / 12]),
        ([5], JP[1], my_negator, [5, -1 / 12]),
        ({"hello": [5]}, JP.hello[1], my_negator, {"hello": [5, -1 / 12]}),
    ],
)
def test_with_values_expanding_list(content, jp, values, expected_content):
    new_content = with_values(content, jp, values)
    assert new_content == expected_content


@pytest.mark.parametrize(
    "content, jp, values, expected_content",
    [
        # VALUES
        ({}, JP.hello, 137, {"hello": 137}),
        ({"hi": 5}, JP.hello, 137, {"hi": 5, "hello": 137}),
        (
            [{"hi": 5}, {"hi": 5}],
            JP[:].hello,
            137,
            [{"hi": 5, "hello": 137}, {"hi": 5, "hello": 137}],
        ),
        # ITERATOR
        ({}, JP.hello, count(37, 1), {"hello": 37}),
        ({"hi": 5}, JP.hello, count(37, 1), {"hi": 5, "hello": 37}),
        (
            [{"hi": 5}, {"hi": 5}],
            JP[:].hello,
            count(37, 1),
            [{"hi": 5, "hello": 37}, {"hi": 5, "hello": 38}],
        ),
        # FUNCTION
        ({}, JP.hello, my_negator, {"hello": -1 / 12}),
        ({"hi": 5}, JP.hello, my_negator, {"hi": 5, "hello": -1 / 12}),
        (
            [{"hi": 5}, {"hi": 5}],
            JP[:].hello,
            my_negator,
            [{"hi": 5, "hello": -1 / 12}, {"hi": 5, "hello": -1 / 12}],
        ),
    ],
)
def test_with_values_adding_to_dicts(content, jp, values, expected_content):
    new_content = with_values(content, jp, values)
    assert new_content == expected_content


@pytest.mark.parametrize(
    "content, jp, values, expected_content",
    [
        ({}, JP.hi, [137], {"hi": [137]}),
        ({}, JP.hi, {"hello": 137}, {"hi": {"hello": 137}}),
    ],
)
def test_with_values_non_primitive_values(content, jp, values, expected_content):
    new_content = with_values(content, jp, values)
    assert new_content == expected_content


@pytest.mark.parametrize(
    "content,jp",
    [
        ([0, 1], JP[3]),
        ({"hello": [0, 1]}, JP.hello[3]),
    ],
)
def test_with_values_rejects_gaps_in_lists(content, jp):
    with pytest.raises(ValueError, match="Cannot append at"):
        _ = with_values(content, jp, 0)


@pytest.mark.parametrize(
    "content,jp,values",
    [
        ([0, 1, 2], JP[:], iter([1, 2])),
        ([{"hello": 5}, {"hello": 42}, {"hello": 137}], JP[:].id, iter([1, 2])),
        ([{"hello": 5}, {"hello": 42}, {"hello": 137}], JP[JP.hello].id, iter([1, 2])),
    ],
)
def test_with_values_insufficient_iterated_input_rejected(content, jp, values):
    with pytest.raises(ValueError, match="Iterator size falls short of expectations"):
        _ = with_values(content, jp, values)


def test_with_values_demo_id_generation():
    content = [
        {"hello": 5},
        {"hello": 42},
        {"hello": 137},
    ]
    content_with_ids = with_values(content, JP[:].id, count(0, 1))
    assert content_with_ids == [
        {"hello": 5, "id": 0},
        {"hello": 42, "id": 1},
        {"hello": 137, "id": 2},
    ]


@pytest.mark.parametrize(
    "content,jp,values,expected_content",
    [
        # specific path
        (
            {
                "hello": [
                    {"hi": "world", "details": [5, 10]},
                    {"hi": "maailma", "details": [7, 20]},
                    {"hi": "mundo", "details": [5, 30]},
                ],
                "irrelevant": 3.14,
            },
            JP.hello[1].details[1],
            137,
            {
                "hello": [
                    {"hi": "world", "details": [5, 10]},
                    {"hi": "maailma", "details": [7, 137]},
                    {"hi": "mundo", "details": [5, 30]},
                ],
                "irrelevant": 3.14,
            },
        ),
        # over multiple slices
        (
            {
                "hello": [
                    {"hi": "world", "details": [5, 10]},
                    {"hi": "maailma", "details": [7, 20]},
                    {"hi": "mundo", "details": [5, 30]},
                ],
                "irrelevant": 3.14,
            },
            JP.hello[:].details[:],
            my_negator,
            {
                "hello": [
                    {"hi": "world", "details": [-5, -10]},
                    {"hi": "maailma", "details": [-7, -20]},
                    {"hi": "mundo", "details": [-5, -30]},
                ],
                "irrelevant": 3.14,
            },
        ),
        # over multiple slices (actual slices)
        (
            {
                "hello": [
                    {"hi": "world", "details": [5, 10]},
                    {"hi": "maailma", "details": [7, 20]},
                    {"hi": "mundo", "details": [5, 30]},
                ],
                "irrelevant": 3.14,
            },
            JP.hello[1:].details[1:],
            my_negator,
            {
                "hello": [
                    {"hi": "world", "details": [5, 10]},
                    {"hi": "maailma", "details": [7, -20]},
                    {"hi": "mundo", "details": [5, -30]},
                ],
                "irrelevant": 3.14,
            },
        ),
        # mkdir -p
        ({}, JP.hello.hi.moi, 137, {"hello": {"hi": {"moi": 137}}}),
        # mkdir -p #2
        ({}, JP["hello"].hi["moi"], 137, {"hello": {"hi": {"moi": 137}}}),
        # mkdir -p with lists
        (
            [],
            JP[0][0][0],
            137,
            [
                [
                    [
                        137,
                    ],
                ],
            ],
        ),
    ],
)
def test_with_values_misc_cases(content, jp, values, expected_content):
    new_content = with_values(content, jp, values)
    assert new_content == expected_content


# TODO test case: overwrite entire dictionaries (with a function)

counter = count(137, 1)


@pytest.mark.parametrize(
    "content, jp, values, expected_content",
    [
        (
            [
                {"product": "apple", "price": -3},
                {"product": "pear", "price": 3},
                {"product": "peach", "price": 0},
            ],
            JP[:],
            (
                lambda r: (
                    r
                    if r["price"] > 0
                    else (
                        r | {"zero": True}
                        if r["price"] == 0
                        else r | {"error": "Negative price"}
                    )
                )
            ),
            [
                {"product": "apple", "price": -3, "error": "Negative price"},
                {"product": "pear", "price": 3},
                {"product": "peach", "price": 0, "zero": True},
            ],
        ),
        (
            [
                {"product": "apple", "price": -3},
                {"product": "pear", "price": 3},
                {"product": "peach", "price": 0},
            ],
            JP[:](JP.error),
            (
                lambda r: (
                    (None,)
                    if r["price"] > 0
                    else ("Zero price",) if r["price"] == 0 else ("Negative price",)
                )
            ),
            [
                {"product": "apple", "price": -3, "error": "Negative price"},
                {"product": "pear", "price": 3, "error": None},
                {"product": "peach", "price": 0, "error": "Zero price"},
            ],
        ),
        (
            [
                {"product": "apple", "price": -3},
                {"product": "pear", "price": 3},
                {"product": "peach", "price": 0},
            ],
            JP[JP.price <= 0](JP.error),
            (
                lambda r: (
                    (None,)
                    if r["price"] > 0
                    else ("Zero price",) if r["price"] == 0 else ("Negative price",)
                )
            ),
            [
                {"product": "apple", "price": -3, "error": "Negative price"},
                {"product": "pear", "price": 3},
                {"product": "peach", "price": 0, "error": "Zero price"},
            ],
        ),
        (
            [{}, {}, {}],
            JP[:](JP.product, JP.price, JP.id),
            zip(iter(["apple", "pear", "peach"]), iter([1.2, 2.3, 3.4]), count(0, 1)),
            [
                {"product": "apple", "price": 1.2, "id": 0},
                {"product": "pear", "price": 2.3, "id": 1},
                {"product": "peach", "price": 3.4, "id": 2},
            ],
        ),
        (
            [{"price": 1.2}, {"price": 2.3}, {"price": 123.4}],
            JP[:](JP.id, JP.verdict),
            lambda d: (
                (next(counter), "expensive")
                if d["price"] > 100
                else (next(counter), "OK")
            ),
            [
                {"price": 1.2, "id": 137, "verdict": "OK"},
                {"price": 2.3, "id": 138, "verdict": "OK"},
                {"price": 123.4, "id": 139, "verdict": "expensive"},
            ],
        ),
    ],
)
def test_with_values_composite(content, jp, values, expected_content):
    new_content = with_values(content, jp, values)
    assert new_content == expected_content


@pytest.mark.parametrize("jp_sub_item", [JP.too.long.path, JP[".*"], JP[0], JP[:]])
def test_with_values_composite_complex_sub_items_rejected(jp_sub_item):
    with pytest.raises(ValueError):
        _ = with_values([{}], JP[:](jp_sub_item), 5)
