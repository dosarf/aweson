aweson
======

Traversing and manipulating hierarchical data (think JSON) using
pythonic `JSON Path`_ -like expressions. This library doesn't support
every JSON Path notation, but it has it's own tricks to offer, e.g.
``with_values()``.


Importing:

>>> from aweson import JP, find_all, find_all_duplicate, find_all_unique, find_next, with_values


Iterating over hierarchical data
--------------------------------

>>> content = {"employees": [
...     {"name": "Doe, John", "age": 32, "account": "johndoe"},
...     {"name": "Doe, Jane", "age": -23, "account": "janedoe"},
...     {"name": "Deer, Jude", "age": 42, "account": "judedeer"},
... ]}
>>> list(find_all(content, JP.employees[:].name))
['Doe, John', 'Doe, Jane', 'Deer, Jude']

    The JSON Path-like expression ``JP.employees[:].name`` is `not` a string.
    Most JSON Path supporting libraries, like `python-jsonpath`_, `jsonpath-rfc9535`_
    have the JSON Path as a string, which they parse.
    Using this library You build a `Python expression`, parsed and interpreted
    by Python itself. This way Your IDE will be of actual help.

To address all items in a list, Pythonic slice expression
``[:]`` is used. Naturally, other indexing and slice expressions also work:

>>> list(find_all(content, JP.employees[1].name))
['Doe, Jane']
>>> list(find_all(content, JP.employees[-1].name))
['Deer, Jude']
>>> list(find_all(content, JP.employees[:2].name))
['Doe, John', 'Doe, Jane']

    These indexing and slicing expressions are valid expressions for both `JSON Path`_
    and Python. The more conventional JSON Path notation for selecting all items of a list,
    ``$.some_array[*]``, is (sort of) supported, only as ``JP.some_array["*"]``.


Selecting list items by boolean expressions
-------------------------------------------

Dictionaries in lists can also be selected by simple boolean expressions evaluated within
the context of each such dictionary, for instance

>>> list(find_all(content, JP.employees[JP.age > 35]))
[{'name': 'Deer, Jude', 'age': 42, 'account': 'judedeer'}]

Only simple comparisons are supported, and only these operators: ``==``, ``!=``,
``<``, ``<=``, ``>``, ``>=``.

    Both operands can be dict keys in a list item, e.g. expressions like
    ``JP.years[JP.planned_budget < JP.realized_budget]`` are supported.

In addition to this, existence of a sub-item or path can also be used as
a list item selector, e.g. ``JP.years[JP.planned_budget]`` would select only
the years where the key ``planned_budget`` exists.


Field name by regular expressions
---------------------------------

Consider the following ``dict`` content

>>> content = {
...     "apple": [{"name": "red delicious"}, {"name": "punakaneli"}],
...     "pear": [{"name": "wilhelm"}, {"name": "conference"}]
... }

if You want to iterate over `all` fruit items, both apples and pears,
You can do so:

>>> list(find_all(content, JP["apple|pear"][:].name))
['red delicious', 'punakaneli', 'wilhelm', 'conference']

or even

>>> list(find_all(content, JP[".*"][:].name))
['red delicious', 'punakaneli', 'wilhelm', 'conference']

if You are interested in everything, not only apples and pears.


Paths to items iterated
-----------------------

You may be interested in the actual path of an item being returned.

    When You use ``enumerate()`` with a ``list``, You want to obtain the
    index of an item alongside with the item's value during iteration. For
    instance,

    >>> list(enumerate(["a", "b"]))
    [(0, 'a'), (1, 'b')]

    and You can use that index to refer to the item itself, even to retrieve
    it again from the list.

Similarly, when iterating within a hierarchical data structure, You
may want to obtain a `pointer` (i.e. path object) alongside the item's
value:

>>> content = {"employees": [
...     {"name": "Doe, John", "age": 32, "account": "johndoe"},
...     {"name": "Doe, Jane", "age": -23, "account": "janedoe"},
...     {"name": "Deer, Jude", "age": 42, "account": "judedeer"},
... ]}
>>> path, item = next(tup for tup in find_all(
...     content,
...     JP.employees[JP.age < 0],
...     with_path=True
... ))
>>> item
{'name': 'Doe, Jane', 'age': -23, 'account': 'janedoe'}

The path to the item found is:

>>> str(path)
'$.employees[1]'

The path object yielded along is a JSON Path-like object, just as if You
constructed it as ``JP.employee[1]``.

    With argument ``with_path=True`` passed, ``find_all()`` yields tuples
    instead of items only. The first item of a yielded tuple is the path object,
    and the second item is the item itself. This is consistent with ``enumerate()``
    behavior.

Also, the JSON Path-like objects have a field called ``.parent``, so that You can
access the parent data structure, consider a path object you've obtained. You
can dig out its respective value:

>>> path = JP.employees[1].name
>>> next(find_all(content, path))
'Doe, Jane'

But if you want to have access to the containing structure, use ``.parent``:

>>> next(find_all(content, path.parent))
{'name': 'Doe, Jane', 'age': -23, 'account': 'janedoe'}


.. _subitems:

Selecting sub-items
-------------------

You can select sub-items of iterated items, comes handy into turning one structure
into another, like a list of records into a ``dict``:

>>> {account: name for account, name in find_all(content, JP.employees[:](JP.account, JP.name))}
{'johndoe': 'Doe, John', 'janedoe': 'Doe, Jane', 'judedeer': 'Deer, Jude'}

    This is roughly equivalent to:

    >>> {item["account"]: item["name"] for item in find_all(content, JP.employees[:])}
    {'johndoe': 'Doe, John', 'janedoe': 'Doe, Jane', 'judedeer': 'Deer, Jude'}

    The sub-item selection, while slightly more verbose, is arguably more
    declarative.

You can also make a sub-items selection produce dictionaries by explicitly naming sub-paths:

>>> list(find_all(content, JP.employees[:](id=JP.account, username=JP.name)))
[{'id': 'johndoe', 'username': 'Doe, John'}, {'id': 'janedoe', 'username': 'Doe, Jane'}, {'id': 'judedeer', 'username': 'Deer, Jude'}]

In the code above, the key ``"account"`` is rendered as ``id``,
and ``"name"`` as ``username``.


Variable field name selection
-----------------------------

The forms ``JP["field_name"]`` and ``JP.field_name`` are equivalent:

>>> from functools import reduce
>>> def my_sum(content, field_name_to_sum, initial):
...     return reduce(
...         lambda x, y: x + y,
...         find_all(content, JP.employees[:][field_name_to_sum]),
...         initial
...     )
>>> my_sum(content, "age", 0)
51
>>> my_sum(content, "account", "")
'johndoejanedoejudedeer'

    At this point, some disambiguation is due:

    - ``JP["field"]`` is equivalent to ``JP.field``, both select a key/value pair
      of a dictionary,

    - ``JP[".*"]`` is a regular expression, select all key/value pairs of a dictionary.

    - ``JP["*"]`` selects all items in a list, equivalent to ``JP[:]``,


.. _withvalues:

Utility ``with_values()``
-------------------------

You can produce a copy of Your hierarchical data with some values overwritten (or
even added):

>>> content = [{"msg": "hallo"}, {"msg": "hello"}, {"msg": "bye"}]
>>> with_values(content, JP[1].msg, "moi")
[{'msg': 'hallo'}, {'msg': 'moi'}, {'msg': 'bye'}]

    Note that the original ``content`` is not mutated:

    >>> content
    [{'msg': 'hallo'}, {'msg': 'hello'}, {'msg': 'bye'}]

You can also overwrite values at multiple places:

>>> with_values(content, JP[:].msg, "moi")
[{'msg': 'moi'}, {'msg': 'moi'}, {'msg': 'moi'}]

or even insert new key / value pairs into ``dict`` s:

>>> with_values(content, JP[:].id, -1)
[{'msg': 'hallo', 'id': -1}, {'msg': 'hello', 'id': -1}, {'msg': 'bye', 'id': -1}]

Writing or added the same value in multiple places is perhaps not that
useful. However, You _can_ use an iterator to supply the values to use for
overwriting or adding:

>>> with_values(content, JP[:].id, iter(range(100)))
[{'msg': 'hallo', 'id': 0}, {'msg': 'hello', 'id': 1}, {'msg': 'bye', 'id': 2}]

    or, more elegantly, if range ``stop=100`` irks You, using ``itertools.count()``:

    >>> from itertools import count
    >>> with_values(content, JP[:].id, count(0, 1))
    [{'msg': 'hallo', 'id': 0}, {'msg': 'hello', 'id': 1}, {'msg': 'bye', 'id': 2}]

You can also provide a (unary) function, taking the current value as an argument,
calculating the new value to be inserted:

>>> with_values(content, JP[:].msg, lambda msg: msg.upper())
[{'msg': 'HALLO'}, {'msg': 'HELLO'}, {'msg': 'BYE'}]

In the example above, the value for dictionary key `"msg"` is given
as argument to the function, and this form is good for re-calculating
an existing value. If You want to add a new key/value pair to a dictionary,
You can achieve that in one of two ways:

- Iterate over dictionaries of the list, receiving each dictionary as argument to Your
  function, and re-calculate entire dictionaries:

>>> with_values(
...     content,
...     JP[:],
...     lambda d: d | {"msg_startswith_h": d["msg"].startswith("h")}
... )
[{'msg': 'hallo', 'msg_startswith_h': True}, {'msg': 'hello', 'msg_startswith_h': True}, {'msg': 'bye', 'msg_startswith_h': False}]

- Iterate over dictionaries of the list, receiving each dictionary as argument to
  Your function just as above, but use the
  `sub-item expression`, to compose dictionary content
  for You, e.g. adding even two keys ( ``"id"`` and ``"verdict"`` ) now, to each
  dictionary item:

>>> counter = count(0, 1)
>>> with_values(
...     content,
...     JP[:](JP.id, JP.msg_startswith_h),
...     lambda d: (next(counter), d["msg"].startswith("h"))
... )
[{'msg': 'hallo', 'id': 0, 'msg_startswith_h': True}, {'msg': 'hello', 'id': 1, 'msg_startswith_h': True}, {'msg': 'bye', 'id': 2, 'msg_startswith_h': False}]

    Above, You declare what keys You are interested in overwriting or adding
    (``"id"`` and ``"msg_startswith_h"``), and Your function returns a tuple of
    just those values, based on the parent dictionary given as argument to it.


    The function ``with_values()`` has a similar idea to `JSON Patch`_, except there
    is no point of a full-fledged patching facility, after all, Python list
    and dictionary comprehensions go a long way in manipulating content hierarchy.


Utility ``find_next()``
-----------------------

Often, You just need a first value, roughly equivalent to a ``next(find_all(...))``
invocation. You can use ``find_next()`` for this, for instance

>>> find_next([{"hello": 5}, {"hello": 42}], JP[:].hello)
5
>>> find_next([{"hello": 5}, {"hello": 42}], JP[1].hello)
42

You can also ask for the path of the value returned, in the style of ``with_path=True``
above

>>> path, value = find_next([{"hello": 5}, {"hello": 42}], JP[-1].hello, with_path=True)
>>> str(path)
'$[1].hello'
>>> value
42

You can also supply a default value for ``find_next()``, just like for ``next()``:

>>> find_next([{"hello": 5}, {"hello": 42}], JP[3].hello, default=17)
17

>>> find_next([{"hello": 5}, {"hello": 42}], JP[3].hello, default=17)
17


Utilities ``find_all_unique()``, ``find_all_duplicate()``
---------------------------------------------------------

A common task is to find only unique items in data, e.g.

>>> content = [{"hi": 1}, {"hi": 2}, {"hi": 1}, {"hi": 3}, {"hi": -22}, {"hi": 3}]
>>> list(find_all_unique(content, JP[:].hi))
[1, 2, 3, -22]

and of course You can ask for the paths, too

>>> content = [{"hi": 1}, {"hi": 2}, {"hi": 1}, {"hi": 3}, {"hi": -22}, {"hi": 3}]
>>> [(str(path), item) for path, item in find_all_unique(content, JP[:].hi, with_path=True)]
[('$[0].hi', 1), ('$[1].hi', 2), ('$[3].hi', 3), ('$[4].hi', -22)]

A related common task is to find duplicates, e.g.

>>> content = {
...     "apple": [{"name": "red delicious", "id": 123}, {"name": "punakaneli", "id": 234}],
...     "pear": [{"name": "wilhelm", "id": 345}, {"name": "conference", "id": 123}]
... }
>>> [f"Duplicate ID: {item} at {path.parent}" for path, item in find_all_duplicate(content, JP["apple|pear"][:].id, with_path=True)]
['Duplicate ID: 123 at $.pear[1]']


Suppressing indexing and key errors, safe navigation operator
-------------------------------------------------------------

By default, path expressions are strict, e.g. for non-existent ``list`` indexes
You get an ``IndexError``:

>>> list(find_all([0, 1], JP[2]))
Traceback (most recent call last):
    ...
IndexError: list index out of range

which is consistent with how a ``list`` behaves. Similarly, for
non-existent ``dict`` keys You get a ``KeyError``:

>>> list(find_all({"hello": 42}, JP.hi))
Traceback (most recent call last):
    ...
KeyError: 'hi'

You can suppress these errors and simply have nothing yielded, for ``list`` indexes:

>>> list(find_all([0, 1], JP[2], lenient=True))
[]

and for ``dict`` keys:

>>> list(find_all({"hello": 42}, JP.hi, lenient=True))
[]

In fact, ``find_next()`` which, in turn, invokes ``find_all()``,
delegates its call to ``find_all()`` with ``lenient=True`` whenever a default
value is defined for ``find_next()`` itself. Thus, supplying a ``None`` as a default
value to ``find_next()``:

>>> empty_content = []
>>> type( find_next(empty_content, JP[3].hello[:].hi[:3], default=None) )
<class 'NoneType'>

is as close to a `safe navigation operator` implementation as You can get
given that `PEP 505`_ has deferred status.


Use Case: JSON content validator and tests
------------------------------------------

The utilities above may benefit You in writing production code, but also unit tests
can be made for more readable and self-explanatory.

Imagine You have a JSON content like this in a request body:

>>> fruits = {
...    "apple": [{"name": "red delicious"}, {"name": "punakaneli"}],
...    "pear": [{"name": "conference"}, {"name": "wilhelm"}],
... }

with the type of a fruit (apple, pear) encoded in the hierarchy itself.

    This is often the case, since processing items of a certain type is easy,
    e.g. in Python:

    >>> [apple["name"] for apple in fruits["apple"]]
    ['red delicious', 'punakaneli']

Let's say Your business analyst says the name of fruit is unique on document scope,
i.e. no two fruits can have the same name regardless whether they are of the same
type or not, and You must validate this unique constraint for all requests.

You wish the JSON format would be flat, something like
``[{"name": "red delicious", "type": "apple"}, ...]``, encoding the type in
a key, because then You could use JSON Schema facility
`uniqueKeys <https://docs.json-everything.net/schema/vocabs/uniquekeys/#schema-uniquekeys-keyword>`__,
but You are not in control of the JSON format: You need a custom validator.
With this library, it's easy enough to fashion something like below:

>>> def verify_unique_fruit_names(content: dict) -> None | str:
...    """
...    Return the (path, name) tuple of the first fruit name
...    duplicate within the entire document if any, None otherwise.
...    """
...    return next(
...       find_all_duplicate(content, JP[".*"][:].name, with_path=True),
...       None
...    )

First off, You want to test that Your implementation will regard the valid document
``fruits`` valid:

>>> assert verify_unique_fruit_names(fruits) is None

Then, You want to verify that the some document with name duplicates will not
pass verification, with the expected error info tuple returned. At this point
test suites normally choose between two alternatives, the bad and the ugly:

- The bad: the input document is small and simple. The test is easy to read
  and maintain as It's easy to spot where the input is broken, but one is left
  with the nagging feeling, whether will ``verify_unique_fruit_names()`` work
  for more complex inputs, too?

- The ugly: the input document is big and complex. Now You know for sure
  that ``verify_unique_fruit_names()`` works for bigger input, except now the
  test is not readable / maintainable, as it's not clear at all, at first glance,
  where the input is broken. You now have a so called `MD5 test`: no one knows
  why it breaks when it does.

Can we have the good? Can we have complex input `and` make sure it's clear
where it's broken? Yes we can, we can use ``with_values()``, e.g. consider this:

>>> an_apple_name = find_next(fruits, JP.apple[0].name)

that is, we have a known apple name.

>>> an_apple_name
'red delicious'

Let's use that name to introduce a duplicate:

>>> broken_path = JP.pear[0].name
>>> fruits_with_duplicate_names = with_values(fruits, broken_path, an_apple_name)

Now our fixture explains where and how it's broken! Let's check,
just to satisfy our curiosity, what the broken input looks like:

>>> fruits_with_duplicate_names
{'apple': [{'name': 'red delicious'}, {'name': 'punakaneli'}], 'pear': [{'name': 'red delicious'}, {'name': 'wilhelm'}]}

After this, the expectations in our tests will be self-explanatory:

>>> error_path, error_value = verify_unique_fruit_names(fruits_with_duplicate_names)
>>> assert error_path == broken_path
>>> assert error_value == an_apple_name

Best of all, you can make a parametrized test, with small and big input both,
so you can have a full coverage which is readable and maintainable.

.. _JSON Path: https://www.rfc-editor.org/rfc/rfc9535
.. _python-jsonpath: https://pypi.org/project/python-jsonpath
.. _jsonpath-rfc9535: https://pypi.org/project/jsonpath-rfc9535
.. _JSON Patch: https://jsonpatch.com/
.. _PEP 505: https://peps.python.org/pep-0505/