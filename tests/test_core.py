import pytest

from aweson import JP, find_all, find_next
from aweson.core import _Predicate

###############################################################
#
# infra
#


@pytest.mark.parametrize(
    "jp_bool",
    [
        JP == 0,
        JP != 0,
        JP < 0,
        JP <= 0,
        JP > 0,
        JP >= 0,
        JP.price == 0,
        JP.price != 0,
        JP.price < 0,
        JP.price <= 0,
        JP.price > 0,
        JP.price >= 0,
        JP.price[0] == 0,
        JP.price[0] != 0,
        JP.price[0] < 0,
        JP.price[0] <= 0,
        JP.price[0] > 0,
        JP.price[0] >= 0,
        JP.price == 0,
        JP.price != 0,
        JP.price < 0,
        JP.price <= 0,
        JP.price > 0,
        JP.price >= 0,
        JP.price.unit == 0,
        JP.price.unit != 0,
        JP.price.unit < 0,
        JP.price.unit <= 0,
        JP.price.unit > 0,
        JP.price.unit >= 0,
    ],
)
def test_overloaded_bool_operators(jp_bool):
    assert isinstance(jp_bool, _Predicate)


@pytest.mark.parametrize(
    "jp,stringfied",
    [
        (JP, "$"),
        (JP.hello, "$.hello"),
        (JP.hello.world, "$.hello.world"),
        (JP["hello"], "$.hello"),
        (JP["hello"]["world"], "$.hello.world"),
        (JP[0], "$[0]"),
        (JP[42], "$[42]"),
        (JP[-1], "$[-1]"),
        (JP[5][42], "$[5][42]"),
        (JP[:], "$[:]"),
        (JP["*"], "$[:]"),
        (JP[JP == 0], "$[?@ == 0]"),
        (JP[JP != 0], "$[?@ != 0]"),
        (JP[JP > 0], "$[?@ > 0]"),
        (JP[JP >= 0], "$[?@ >= 0]"),
        (JP[JP < 0], "$[?@ < 0]"),
        (JP[JP <= 0], "$[?@ <= 0]"),
        (JP[JP.id], "$[?@.id]"),
        (JP[JP.id == 0], "$[?@.id == 0]"),
        (JP.products[JP == 0], "$.products[?@ == 0]"),
        (JP.products[JP.id], "$.products[?@.id]"),
        (JP.products[JP.price > 120], "$.products[?@.price > 120]"),
        (JP.products[JP.price > JP.avg_price], "$.products[?@.price > @.avg_price]"),
        (JP[::], "$[:]"),
        (JP[1:], "$[1:]"),
        (JP[1::], "$[1:]"),
        (JP[:2], "$[:2]"),
        (JP[:2:], "$[:2]"),
        (JP[::-1], "$[::-1]"),
        (JP[1:12:-1], "$[1:12:-1]"),
        (JP[5].hello, "$[5].hello"),
        (JP.hello[5], "$.hello[5]"),
        (JP["hello|hi"].id, "$[hello|hi].id"),
        (JP[5].hello[42].world, "$[5].hello[42].world"),
        (JP.hello[5].world[42], "$.hello[5].world[42]"),
        (JP["hello"][5]["world"][42], "$.hello[5].world[42]"),
        (JP.hello(JP.world, JP.hi[0]), "$.hello(@.world, @.hi[0])"),
    ],
)
def test_jp_stringification(jp, stringfied):
    assert str(jp) == stringfied


@pytest.mark.parametrize(
    "jp, is_singular",
    [
        (JP, True),
        (JP.hello, True),
        (JP.hello[0], True),
        (JP.hello[-1], True),
        (JP["hello"], True),
        (JP[:], False),
        (JP["*"], False),
        (JP[1:2], False),
        (JP.hello[:], False),
        (JP[1:2].hello, False),
    ],
)
def test_path_is_singular(jp, is_singular):
    assert jp.is_singular() == is_singular


def test_sub_selection_either_all_unnamed_or_all_named_fields():
    with pytest.raises(NotImplementedError):
        JP.hello(JP.some_field, named=JP.other_field)


def test_sub_selection_must_not_be_empty():
    with pytest.raises(NotImplementedError):
        JP.hello()


def test_sub_selection_must_be_path():
    with pytest.raises(ValueError):
        JP[:](JP.id, "somestring")

    with pytest.raises(ValueError):
        JP[:](id_=JP.id, detail="somestring")


def test_sub_selection_must_be_singular():
    with pytest.raises(ValueError):
        JP[:](JP.id, JP.detail[:])

    with pytest.raises(ValueError):
        JP[:](id_=JP.id, detail=JP.detail[:])


###############################################################
#
# find_all()
#


@pytest.mark.parametrize(
    "content,jp,expected_items",
    [
        ("string", JP, ["string"]),
        (5, JP, [5]),
        (5.13, JP, [5.13]),
        (True, JP, [True]),
        ({"hello": 42}, JP, [{"hello": 42}]),
        ([5, 42], JP, [[5, 42]]),
    ],
)
def test_find_all_for_root_path(content, jp, expected_items):
    items = list(find_all(content, jp))
    assert items == expected_items


@pytest.mark.parametrize(
    "content,jp,expected_items",
    [
        ({"hello": 42, "hi": "irrelevant"}, JP.hello, [42]),
        ({"hello": {"world": 42}, "hi": "irrelevant"}, JP.hello.world, [42]),
        ({"hello": 42, "hi": "irrelevant"}, JP["hello"], [42]),
        ({"hello": {"world": 42}, "hi": "irrelevant"}, JP["hello"]["world"], [42]),
    ],
)
def test_find_all_simple_key_based_dict_access(content, jp, expected_items):
    items = list(find_all(content, jp))
    assert items == expected_items


@pytest.mark.parametrize(
    "content,jp,expected_items",
    [
        ([5, 42], JP[0], [5]),
        ([5, 42], JP[-1], [42]),
        ([5, 42, 137], JP[:], [5, 42, 137]),
        ([5, 42, 137], JP["*"], [5, 42, 137]),
        ([5, 42, 137], JP[1:], [42, 137]),
        ([5, 42, 137], JP[:1], [5]),
        ([5, 42, 137], JP[::-1], [137, 42, 5]),
    ],
)
def test_find_all_list_access_by_index_and_slice(content, jp, expected_items):
    items = list(find_all(content, jp))
    assert items == expected_items


@pytest.mark.parametrize(
    "content,jp,expected_items",
    [
        (
            {
                "apple": [{"name": "red delicious"}, {"name": "punakaneli"}],
                "pear": [{"name": "wilhelm"}, {"name": "conference"}],
            },
            JP[".*"][:].name,
            ["red delicious", "punakaneli", "wilhelm", "conference"],
        ),
        (
            {
                "apple": [{"name": "red delicious"}, {"name": "punakaneli"}],
                "pear": [{"name": "wilhelm"}, {"name": "conference"}],
            },
            JP["apple|pear"][:].name,
            ["red delicious", "punakaneli", "wilhelm", "conference"],
        ),
    ],
)
def test_find_all_access_by_key_regex(content, jp, expected_items):
    items = list(find_all(content, jp))
    assert items == expected_items


@pytest.mark.parametrize(
    "content,jp,expected_items",
    [
        (
            {
                "apple": [{"name": "red delicious"}, {"name": "punakaneli"}],
                "pear": [{"name": "wilhelm"}, {"name": "conference"}],
            },
            JP[".*"][:].name,
            [
                (JP.apple[0].name, "red delicious"),
                (JP.apple[1].name, "punakaneli"),
                (JP.pear[0].name, "wilhelm"),
                (JP.pear[1].name, "conference"),
            ],
        ),
    ],
)
def test_find_all_access_by_key_regex_with_path(content, jp, expected_items):
    items = list(find_all(content, jp, with_path=True))
    assert items == expected_items


@pytest.mark.parametrize(
    "content,jp,expected_items",
    [
        ({"hello": [5, 42]}, JP.hello[1], [42]),
        ([{"hello": 42}, {"hello": 5}], JP[1].hello, [5]),
        ([{"hello": 42}, {"hello": 5}], JP[1]["hello"], [5]),
        (
            {"l1": [{"detail": {"data": 5}}, {"detail": {"data": 42}}]},
            JP.l1[:].detail.data,
            [5, 42],
        ),
    ],
)
def test_find_all_mixed_hierarchy(content, jp, expected_items):
    items = list(find_all(content, jp))
    assert items == expected_items


@pytest.mark.parametrize(
    "content,jp,expected_items",
    [
        (
            [
                {"hello": "world", "hi": [5, 42, 137]},
                {"hello": "mundo", "hi": [-5, -42, -137]},
            ],
            JP[:](JP.hello, JP.hi[1]),
            [("world", 42), ("mundo", -42)],
        ),
        (
            {
                "employees": [
                    {"name": "Doe, John", "age": 32, "account": "johndoe"},
                    {"name": "Doe, Jane", "age": -23, "account": "janedoe"},
                    {"name": "Deer, Jude", "age": 42, "account": "judedeer"},
                ]
            },
            JP.employees[:2](JP.account, JP.name),
            [("johndoe", "Doe, John"), ("janedoe", "Doe, Jane")],
        ),
    ],
)
def test_find_all_sub_selection_tuple(content, jp, expected_items):
    items = list(find_all(content, jp))
    assert items == expected_items


@pytest.mark.parametrize(
    "content,jp,expected_items",
    [
        (
            [
                {"hello": "world", "hi": [5, 42, 137]},
                {"hello": "mundo", "hi": [-5, -42, -137]},
            ],
            JP[:](id=JP.hello, detail=JP.hi[1]),
            [{"id": "world", "detail": 42}, {"id": "mundo", "detail": -42}],
        ),
        (
            {
                "employees": [
                    {"name": "Doe, John", "age": 32, "account": "johndoe"},
                    {"name": "Doe, Jane", "age": -23, "account": "janedoe"},
                    {"name": "Deer, Jude", "age": 42, "account": "judedeer"},
                ]
            },
            JP.employees[:2](id=JP.account, detail=JP.name),
            [
                {"id": "johndoe", "detail": "Doe, John"},
                {"id": "janedoe", "detail": "Doe, Jane"},
            ],
        ),
    ],
)
def test_find_all_sub_selection(content, jp, expected_items):
    items = list(find_all(content, jp))
    assert items == expected_items


def test_find_all_demo_transformation():
    list_of_entities = [
        {"id": 5, "value": "five"},
        {"id": 42, "value": "life, universe and everything"},
        {"id": 137, "value": "137"},
    ]

    id_to_value_map = {
        id_: value for id_, value in find_all(list_of_entities, JP[:](JP.id, JP.value))
    }
    assert id_to_value_map == {
        5: "five",
        42: "life, universe and everything",
        137: "137",
    }


def test_find_all_demo_transformation_named_tuples():
    list_of_entities = [
        {"id": 5, "value": "five"},
        {"id": 42, "value": "life, universe and everything"},
        {"id": 137, "value": "137"},
    ]

    id_to_value_map = {
        tup["id"]: tup["value"]
        for tup in find_all(list_of_entities, JP[:](id=JP.id, value=JP.value))
    }
    assert id_to_value_map == {
        5: "five",
        42: "life, universe and everything",
        137: "137",
    }


@pytest.mark.parametrize(
    "content,jp,expected_paths_and_items",
    [
        ("string", JP, [(JP, "string")]),
        (
            {"hello": {"world": 42}, "hi": "irrelevant"},
            JP.hello.world,
            [(JP.hello.world, 42)],
        ),
        ([5, 42], JP[-1], [(JP[1], 42)]),
        ([5, 42, 137], JP[1:], [(JP[1], 42), (JP[2], 137)]),
        ([5, 42, 137], JP[::-1], [(JP[2], 137), (JP[1], 42), (JP[0], 5)]),
        ([{"hello": 42}, {"hello": 5}], JP[1:]["hello"], [(JP[1].hello, 5)]),
        (
            [{"hello": 42}, {"hello": 5}],
            JP[-1::-1]["hello"],
            [(JP[1].hello, 5), (JP[0].hello, 42)],
        ),
        (
            [
                {"hello": "world", "hi": [5, 42, 137]},
                {"hello": "mundo", "hi": [-5, -42, -137]},
            ],
            JP[:](JP.hello, JP.hi[1]),
            [
                (JP[0](JP.hello, JP.hi[1]), ("world", 42)),
                (JP[1](JP.hello, JP.hi[1]), ("mundo", -42)),
            ],
        ),
        (
            [
                {"hello": "world", "hi": [5, 42, 137]},
                {"hello": "mundo", "hi": [-5, -42, -137]},
            ],
            JP[1:0:-1](JP.hello, JP.hi[1]),
            [(JP[1](JP.hello, JP.hi[1]), ("mundo", -42))],
        ),
    ],
)
def test_find_all_with_paths(content, jp, expected_paths_and_items):
    paths_and_items = list(find_all(content, jp, with_path=True))
    assert len(paths_and_items) == len(expected_paths_and_items)
    for path_and_item, expected_path_and_item in zip(
        paths_and_items, expected_paths_and_items
    ):

        path, item = path_and_item

        # The path yielded alongside the item points to the item itself ...
        assert item == next(find_all(content, path))

        # ... but let's check it against explicit expectations, too.
        expected_path, expected_item = expected_path_and_item
        assert item == expected_item
        assert str(path) == str(expected_path)


@pytest.mark.parametrize(
    "content, jp",
    [
        ([], JP[0]),
        ([5, 42], JP[2]),
        ({"hello": [5, 42]}, JP.hello[2]),
        ({"hello": [5, 42]}, JP["hello"][2]),
    ],
)
def test_find_all_index_error(content, jp):
    with pytest.raises(IndexError):
        list(find_all(content, jp))


@pytest.mark.parametrize(
    "content, jp",
    [
        ([], JP[0]),
        ([5, 42], JP[2]),
        ([5, 42], JP[-3]),
        ({"hello": [5, 42]}, JP.hello[2]),
        ({"hello": [5, 42]}, JP["hello"][2]),
    ],
)
def test_lenient_find_all_yields_nothing_on_nonexistent_indexes(content, jp):
    assert list(find_all(content, jp, lenient=True)) == []


@pytest.mark.parametrize(
    "content, jp",
    [
        ({}, JP.hello),
        ({"hello": {"world": 42}}, JP.hello.hi),
        ({"hello": {"world": 42}}, JP["hello"]["hi"]),
    ],
)
def test_find_all_key_error(content, jp):
    with pytest.raises(KeyError):
        list(find_all(content, jp))


@pytest.mark.parametrize(
    "content, jp",
    [
        ({}, JP.hello),
        ({"hello": {"world": 42}}, JP.hello.hi),
        ({"hello": {"world": 42}}, JP["hello"]["hi"]),
    ],
)
def test_lenient_find_all_yields_nothing_on_nonexistent_keys(content, jp):
    assert list(find_all(content, jp, lenient=True)) == []


@pytest.mark.parametrize(
    "content, jp",
    [
        ([], JP[:].hello[13].hi),
        ({}, JP.hello[13].hi[:]),
    ],
)
def test_lenient_find_all_yields_nothing_mixed_case(content, jp):
    assert list(find_all(content, jp, lenient=True)) == []


@pytest.mark.parametrize(
    "content,jp,with_path,expected_items",
    [
        # cases: if attribute / path exists
        ([{"hello": 5, "id": 1}, {"hi": 42, "id": 2}], JP[JP.hi].id, False, [2]),
        (
            [{"hello": 5, "id": 1}, {"hi": 42, "id": 2}],
            JP[JP.hi].id,
            True,
            [(JP[1].id, 2)],
        ),
        # cases: comparing to constant literal
        (
            {
                "product": [
                    {"current_price": 12.3, "avg_price": 10.5, "name": "kerfufle"},
                    {"current_price": 1.3, "avg_price": 9.5, "name": "acme"},
                ]
            },
            JP.product[JP.current_price < 10.1].name,
            False,
            ["acme"],
        ),
        (
            {
                "product": [
                    {"current_price": 12.3, "avg_price": 10.5, "name": "kerfufle"},
                    {"current_price": 1.3, "avg_price": 9.5, "name": "acme"},
                ]
            },
            JP.product[JP.current_price < 10.1].name,
            True,
            [(JP.product[1].name, "acme")],
        ),
        # cases: comparing two sub-items
        (
            {
                "product": [
                    {"current_price": 12.3, "avg_price": 10.5, "name": "kerfufle"},
                    {"current_price": 1.3, "avg_price": 9.5, "name": "acme"},
                ]
            },
            JP.product[JP.current_price > JP.avg_price].name,
            False,
            ["kerfufle"],
        ),
        (
            {
                "product": [
                    {"current_price": 12.3, "avg_price": 10.5, "name": "kerfufle"},
                    {"current_price": 1.3, "avg_price": 9.5, "name": "acme"},
                ]
            },
            JP.product[JP.current_price > JP.avg_price].name,
            True,
            [(JP.product[0].name, "kerfufle")],
        ),
    ],
)
def test_find_all_with_attribute_expressions(content, jp, with_path, expected_items):
    items = list(find_all(content, jp, with_path=with_path))
    assert items == expected_items


@pytest.mark.parametrize(
    "content,jp,with_path,expected_items",
    [
        ([0, 5, -5, 42], JP[JP == 0], True, [(JP[0], 0)]),
        ({"hello": [0, 5, -5, 42]}, JP.hello[JP == 0], True, [(JP.hello[0], 0)]),
        (
            [{"hi": 0}, {"hi": 5}, {"hi": -5}, {"hi": 42}],
            JP[JP.hi == 0],
            True,
            [(JP[0], {"hi": 0})],
        ),
        (
            {"hello": [{"hi": 0}, {"hi": 5}, {"hi": -5}, {"hi": 42}]},
            JP.hello[JP.hi == 0],
            True,
            [(JP.hello[0], {"hi": 0})],
        ),
        ([0, 5, -5, 42], JP[JP != 0], True, [(JP[1], 5), (JP[2], -5), (JP[3], 42)]),
        ([0, 5, -5, 42], JP[JP > 0], True, [(JP[1], 5), (JP[3], 42)]),
        ([0, 5, -5, 42], JP[JP >= 0], True, [(JP[0], 0), (JP[1], 5), (JP[3], 42)]),
        ([0, 5, -5, 42], JP[JP < 0], True, [(JP[2], -5)]),
        ([0, 5, -5, 42], JP[JP <= 0], True, [(JP[0], 0), (JP[2], -5)]),
    ],
)
def test_find_all_with_attribute_expressions_all_operators(
    content, jp, with_path, expected_items
):
    items = list(find_all(content, jp, with_path=with_path))
    assert items == expected_items


@pytest.mark.parametrize(
    "content,jp,expected_items",
    [
        ([{"id2": 0}], JP[JP.id == 0], []),
        ([{"id": None}], JP[JP.id == 0], []),
        ([{"id": "not a number"}], JP[JP.id == 0], []),
    ],
)
def test_find_all_with_attribute_expressions_are_robust(content, jp, expected_items):
    items = list(find_all(content, jp))
    assert items == expected_items


###############################################################
#
# find_next()
#


@pytest.mark.parametrize(
    "content,jp,with_path,expected_value",
    [
        (
            [{"hello": 5}, {"hello": 42}],
            JP[:].hello,
            False,
            5,
        ),
        (
            [{"hello": 5}, {"hello": 42}],
            JP[1].hello,
            False,
            42,
        ),
        (
            [{"hello": 5}, {"hello": 42}],
            JP[:].hello,
            True,
            (JP[0].hello, 5),
        ),
        (
            [{"hello": 5}, {"hello": 42}],
            JP[1].hello,
            True,
            (JP[1].hello, 42),
        ),
    ],
)
def test_find_next(content, jp, with_path, expected_value):
    assert find_next(content, jp, with_path=with_path) == expected_value


@pytest.mark.parametrize(
    "content,jp,with_path,default",
    [
        # cases: slice with empty list
        ([], JP[:].hello, False, 17),
        ([], JP[:].hello, True, (None, 17)),
        # cases: ignoring index error
        (
            [{"hello": 5}, {"hello": 42}],
            JP[2].hello,
            False,
            5,
        ),
        (
            [{"hello": 5}, {"hello": 42}],
            JP[2].hello,
            True,
            (None, 5),
        ),
        # cases: ignoring key error
        (
            [{"hello": 5}, {"hello": 42}],
            JP[2].hi,
            False,
            5,
        ),
        (
            [{"hello": 5}, {"hello": 42}],
            JP[2].hi,
            True,
            (None, 5),
        ),
        # cases: mixed, long paths
        ([], JP[:].hello[13].hi, False, 5),
        ([], JP[:].hello[13].hi, True, (None, 5)),
        ({}, JP.hello[13].hi[:], False, 5),
        ([], JP[:].hello[13].hi, True, (None, 5)),
    ],
)
def test_find_next_with_default(content, jp, with_path, default):
    assert find_next(content, jp, with_path=with_path, default=default)
