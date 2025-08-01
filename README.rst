aweson
======

Traversing and manipulating hierarchical data (think JSON) using
pythonic `JSON Path`_ -like expressions.


Import
------

>>> from aweson import JP, find_all, find_all_duplicate, find_all_unique, find_next, parse, with_values


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
    have the JSON Path as a string, parsed.
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


Obtaining a single value
------------------------

If You need only a first value, use ``find_next()``, roughly equivalent to ``next(find_all(...))``:

>>> find_next([{"hello": 5}, {"hello": 42}], JP[:].hello)
5
>>> find_next([{"hello": 5}, {"hello": 42}], JP[1].hello)
42

You can also supply a default value for ``find_next()``, just like for ``next()``:

>>> find_next([{"hello": 5}, {"hello": 42}], JP[3].hello, default=17)
17

Supplying a ``None`` as a default value to ``find_next()``, like:

>>> empty_content = []
>>> type( find_next(empty_content, JP[3].hello[:].hi[:3], default=None) )
<class 'NoneType'>

is as close to a `safe navigation operator` implementation as You can get
given that `PEP 505`_ has deferred status.


Paths to iterated items
-----------------------

You may be interested in the path of an item being yielded.

    When You use ``enumerate()`` with a ``list``, You want to obtain the
    index of an item alongside with the item's value during iteration. For
    instance,

    >>> list(enumerate(["a", "b"]))
    [(0, 'a'), (1, 'b')]

    You can use that index to refer to the item, e.g. in a log message
    or for retrieving the item at a later point.

Similarly, when iterating within a hierarchical data structure, You
may want to obtain the path object along the item's value:

>>> path, item = find_next(
...     content,
...     JP.employees[1],
...     with_path=True
... )
>>> item
{'name': 'Doe, Jane', 'age': -23, 'account': 'janedoe'}

The path to the item found is:

>>> str(path)
'$.employees[1]'

You can use this ``path`` object in a log message or for retrieval:

>>> path = JP.employees[1].name
>>> find_next(content, path)
'Doe, Jane'

You may want to use ``.parent`` to have access to the containing structure:

>>> find_next(content, path.parent)
{'name': 'Doe, Jane', 'age': -23, 'account': 'janedoe'}

Naturally, ``find_all()`` also supports ``with_path``:

>>> for path, _ in find_all(content, JP.employees[1:], with_path=True):
...     print(path)
$.employees[1]
$.employees[2]


Suppressing indexing and key errors
-----------------------------------

By default, path expressions are strict, e.g. for non-existent ``list`` indexes
``find_all()`` raises an ``IndexError``, and for non-existend ``dict`` keys a ``KeyError``:

>>> list(find_all([0, 1], JP[2]))
Traceback (most recent call last):
    ...
IndexError: list index out of range
>>> list(find_all({"hello": 42}, JP.hi))
Traceback (most recent call last):
    ...
KeyError: 'hi'

This is consistent with how a ``list`` and ``dict`` behave.

You can suppress these errors:

>>> list(find_all([0, 1], JP[2], lenient=True))
[]
>>> list(find_all({"hello": 42}, JP.hi, lenient=True))
[]

    When invoking ``find_next()``, just pass a default value.


Selecting list items by boolean expressions
-------------------------------------------

Dictionary items in lists can be selected by boolean expressions evaluated within
the context of each ``dict`` item, for instance

>>> list(find_all(content, JP.employees[JP.age > 35]))
[{'name': 'Deer, Jude', 'age': 42, 'account': 'judedeer'}]

Only simple comparisons are supported with these operators: ``==``, ``!=``,
``<``, ``<=``, ``>``, ``>=``.

    The first operand must always be a key expression, never a constant,
    e.g. a ``JP.employees[35 < JP.age]`` will `not` work.
    However, both operands can be key expressions, e.g.
    ``JP.years[JP.planned_budget < JP.realized_budget]`` is supported.

In addition to this, existence of a sub-item or path can also be used as
a list item selector, e.g. ``JP.years[JP.planned_budget]`` would select only
the years where the key ``planned_budget`` exists.


Field name by regular expressions
---------------------------------

Consider the following ``dict`` content

>>> content = {
...     "apple": [{"name": "red delicious"}, {"name": "punakaneli"}],
...     "pineapple": [{"name": "ripley"}, {"name": "mordilona"}],
...     "banana": [{"name": "cavendish"}, {"name": "lantundan"}]
... }

if You want to iterate both apples and pineapples, You can do so:

>>> list(find_all(content, JP[".*apple"][:].name))
['red delicious', 'punakaneli', 'ripley', 'mordilona']

and, if You are interested in everything including bananas:

>>> list(find_all(content, JP[".*"][:].name))
['red delicious', 'punakaneli', 'ripley', 'mordilona', 'cavendish', 'lantundan']


.. _subitems:

Selecting sub-items
-------------------

You can select multiple sub-items of iterated items, they are yielded as ``tuple`` instances:

>>> content = {"employees": [
...     {"name": "Doe, John", "age": 32, "account": "johndoe"},
...     {"name": "Doe, Jane", "age": -23, "account": "janedoe"},
...     {"name": "Deer, Jude", "age": 42, "account": "judedeer"},
... ]}
>>> list(find_all(content, JP.employees[:](JP.account, JP.name)))
[('johndoe', 'Doe, John'), ('janedoe', 'Doe, Jane'), ('judedeer', 'Deer, Jude')]

You can also make a sub-items selection produce dictionaries by explicitly
defining ``dict`` keys:

>>> list(find_all(content, JP.employees[:](id=JP.account, username=JP.name)))
[{'id': 'johndoe', 'username': 'Doe, John'}, {'id': 'janedoe', 'username': 'Doe, Jane'}, {'id': 'judedeer', 'username': 'Deer, Jude'}]

In the code above, the key ``"account"`` is rendered as ``id``,
and ``"name"`` as ``username``.


Variable field name selection
-----------------------------

The forms ``JP.field_name`` and ``JP["field_name"]`` are equivalent. Thus, if you don't know
``field_name`` in advance, you can still construct a path object:

>>> from functools import reduce
>>> def my_sum(content, field_name, initial_value):
...     return reduce(
...         lambda x, y: x + y,
...         find_all(content, JP.employees[:][field_name]),
...         initial_value
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

You can produce a copy of Your hierarchical with some changes in data:

>>> content = [{"msg": "hallo"}, {"msg": "hello"}, {"msg": "bye"}]
>>> with_values(content, JP[1].msg, "moi")
[{'msg': 'hallo'}, {'msg': 'moi'}, {'msg': 'bye'}]

    Note that the original ``content`` is not mutated:

    >>> content
    [{'msg': 'hallo'}, {'msg': 'hello'}, {'msg': 'bye'}]

You can also overwrite values at multiple places:

>>> with_values(content, JP[1:].msg, "moi")
[{'msg': 'hallo'}, {'msg': 'moi'}, {'msg': 'moi'}]

or even insert entirely new keys into ``dict`` items:

>>> with_values(content, JP[:].id, -1)
[{'msg': 'hallo', 'id': -1}, {'msg': 'hello', 'id': -1}, {'msg': 'bye', 'id': -1}]

Adding the exact same ID value (-1) is perhaps not that useful. However, You `can` use
an iterator to supply the values:

>>> with_values(content, JP[:].id, iter(range(100)))
[{'msg': 'hallo', 'id': 0}, {'msg': 'hello', 'id': 1}, {'msg': 'bye', 'id': 2}]

    or, more elegantly, if range's ``stop=100`` irks You, as it should, You may
    use ``itertools.count()``:

    >>> from itertools import count
    >>> with_values(content, JP[:].id, count(0, 1))
    [{'msg': 'hallo', 'id': 0}, {'msg': 'hello', 'id': 1}, {'msg': 'bye', 'id': 2}]

You can also provide a (unary) function, taking the current value as an argument,
calculating the new value to be inserted:

>>> with_values(content, JP[:].msg, lambda msg: msg.upper())
[{'msg': 'HALLO'}, {'msg': 'HELLO'}, {'msg': 'BYE'}]

In the example above, the value for dictionary key `"msg"` is given
as argument to the function, and this form is good for calculating
a new value for the same key. But what if you want to calculate a new
key/value pair, e.g. you want to calculate the base-64 encoded form
of each message?

>>> import base64
>>> with_values(
...     content,
...     JP[:](JP.b64,),
...     lambda d: (str(base64.b64encode(bytes(d["msg"], "utf-8")), "utf-8"),)
... )
[{'msg': 'hallo', 'b64': 'aGFsbG8='}, {'msg': 'hello', 'b64': 'aGVsbG8='}, {'msg': 'bye', 'b64': 'Ynll'}]

Above, you are iterating over each ``dict`` item, and telling, with a
`sub-item expression` (the tuple with the  single ``JP.hash``), the name
of the key(s) to be inserted: ``hash``. Then the function,
taking an entire ``dict`` item as an argument, returns a tuple with a value for each
key to be inserted. You can insert multiple keys, too:

>>> counter = count(0, 1)
>>> with_values(
...     content,
...     JP[:](JP.id, JP.b64),
...     lambda d: (next(counter), str(base64.b64encode(bytes(d["msg"], "utf-8")), "utf-8"))
... )
[{'msg': 'hallo', 'id': 0, 'b64': 'aGFsbG8='}, {'msg': 'hello', 'id': 1, 'b64': 'aGVsbG8='}, {'msg': 'bye', 'id': 2, 'b64': 'Ynll'}]

You don't have to use sub-item expressions, you may construct the dictionary
on your own, too:

>>> counter = count(0, 1)
>>> with_values(
...     content,
...     JP[:],
...     lambda d: d | { "id": next(counter), "b64": str(base64.b64encode(bytes(d["msg"], "utf-8")), "utf-8")}
... )
[{'msg': 'hallo', 'id': 0, 'b64': 'aGFsbG8='}, {'msg': 'hello', 'id': 1, 'b64': 'aGVsbG8='}, {'msg': 'bye', 'id': 2, 'b64': 'Ynll'}]

    The function ``with_values()`` has a similar idea to `JSON Patch`_, except there
    is no point of a full-fledged patching facility, after all, Python list
    and dictionary comprehensions go a long way in manipulating content hierarchy.


Utilities ``find_all_unique()``, ``find_all_duplicate()``
---------------------------------------------------------

A common task is to find only unique items in data, e.g.

>>> content = [{"hi": 1}, {"hi": 2}, {"hi": 1}, {"hi": 3}, {"hi": -22}, {"hi": 3}]
>>> list(find_all_unique(content, JP[:].hi))
[1, 2, 3, -22]

and You can ask for the paths, too

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


``parse()``
-----------

You may want to be able parse back the stringified value of a path object, e.g. using content

>>> content = {
...     "apple": [{"name": "red delicious", "id": 123}, {"name": "punakaneli", "id": 234}],
...     "pear": [{"name": "wilhelm", "id": 345}, {"name": "conference", "id": 123}]
... }

and You have some the stringified path, e.g. in persistence,

>>> path_str = str(JP.apple[0].name)
>>> path_str
'$.apple[0].name'

which now you wish to turn into a path object and use it

>>> path = parse(path_str)
>>> assert path == JP.apple[0].name
>>> find_next(content, path)
'red delicious'

Since there is a an overlap between `JSON Path`_ and this libary's features,
``parse()`` provides a measure of `JSON Path`_ support:

>>> list(find_all(content, parse('$.apple[*].name')))
['red delicious', 'punakaneli']

but only for simpler `JSON Path`_ expressions.


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
i.e. no two fruits can have the same name regardless of their types,
and this unique constraint is to be validated.

Now You wish the JSON format would be flat, something like
``[{"name": "red delicious", "type": "apple"}, ...]``, encoding the type in
a key, because then You could use
`uniqueKeys <https://docs.json-everything.net/schema/vocabs/uniquekeys/#schema-uniquekeys-keyword>`__
for validation, but You are not in control of the JSON format, You need a custom validator:

>>> def find_fruit_name_duplicate(content: dict) -> None | str:
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

>>> assert find_fruit_name_duplicate(fruits) is None

Then, You want to verify that the some document with name duplicates will not
pass verification, with the expected error info tuple returned. At this point
test suites normally choose between two alternatives, the bad and the ugly:

- The bad: the input document is small and simple. The test is easy to read
  and maintain as It's easy to spot where the input is broken, but one is left
  with the nagging feeling, whether will ``find_fruit_name_duplicate()`` work
  for more complex inputs, too?

- The ugly: the input document is big and complex. Now You know for sure
  that ``find_fruit_name_duplicate()`` works for bigger input, except now the
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

>>> error_path, error_value = find_fruit_name_duplicate(fruits_with_duplicate_names)
>>> assert error_path == broken_path
>>> assert error_value == an_apple_name

Best of all, you can make a parametrized test, with small and big input both,
so you can have a full coverage which is readable and maintainable.

.. _JSON Path: https://www.rfc-editor.org/rfc/rfc9535
.. _python-jsonpath: https://pypi.org/project/python-jsonpath
.. _jsonpath-rfc9535: https://pypi.org/project/jsonpath-rfc9535
.. _JSON Patch: https://jsonpatch.com/
.. _PEP 505: https://peps.python.org/pep-0505/