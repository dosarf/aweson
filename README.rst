``aweson``
==========
Traversing and manipulating hierarchical data (JSON) using pythonic JSON Path-like expressions


Importing
---------

>>> from aweson import JP, find_all, find_all_duplicate, find_all_unique, find_next


Iterating over hierarchical data
--------------------------------

>>> content = {"employees": [
...     {"name": "Doe, John", "age": 32, "account": "johndoe"},
...     {"name": "Doe, Jane", "age": -23, "account": "janedoe"},
...     {"name": "Deer, Jude", "age": 42, "account": "judedeer"},
... ]}
>>> list(find_all(content, JP.employees[:].name))
['Doe, John', 'Doe, Jane', 'Deer, Jude']

Note that the JSON Path-like expression ``JP.employees[:].name`` is `not` a string,
it's a Python expression, i.e. your IDE will be of actual help.

Furthermore, to address all items in a list, Pythonic slice expression ``[:]`` is used. Naturally,
other indexing and slice expressions also work in the conventional Pythonic way:

>>> list(find_all(content, JP.employees[-1].name))
['Deer, Jude']

>>> list(find_all(content, JP.employees[:2].name))
['Doe, John', 'Doe, Jane']


Paths to items iterated
-----------------------

You may be interested in the actual path of an item being returned, just like
you get an index alongside items when using ``enumerate()``. For instance, you may want to verify
ages being non-negative, and report accurately the path of failure items:

>>> path, item = next(tup for tup in find_all(content, JP.employees[:].age, with_path=True) if tup[1] < 0)
>>> item
-23

The offending path, then, in human-readable format:

>>> str(path)
'$.employees[1].age'

The enclosing record, using ``.parent`` attribute of the path obtained for the offending age:

>>> next(find_all(content, path.parent))
{'name': 'Doe, Jane', 'age': -23, 'account': 'janedoe'}

Note, with argument ``with_path=True`` passed, ``find_all()`` yields tuples instead of single
items.


Selecting sub-items
-------------------

You can select sub-items of iterated items, comes handy into turning one structure
into another, like a list of records into a ``dict``:

>>> {tup[0]: tup[1] for tup in find_all(content, JP.employees[:](JP.account, JP.name))}
{'johndoe': 'Doe, John', 'janedoe': 'Doe, Jane', 'judedeer': 'Deer, Jude'}

or, to make your processing logic within the same comprehension expression more readable:

>>> {account: name for account, name in find_all(content, JP.employees[:](JP.account, JP.name))}
{'johndoe': 'Doe, John', 'janedoe': 'Doe, Jane', 'judedeer': 'Deer, Jude'}

You can also make a sub-items selection produce `named tuples` by explicitly naming sub-paths:

>>> list(find_all(content, JP.employees[:](account=JP.account, name=JP.name)))
[SubSelect(account='johndoe', name='Doe, John'), SubSelect(account='janedoe', name='Doe, Jane'), SubSelect(account='judedeer', name='Deer, Jude')]

Now, the processing code could be elsewhere than the `find_all()` invocation, as named tuples will carry
the field names with them. The produced named tuples will all be called ``SubSelect`` but they will be
different named tuples for each invocation.


Variable field name selection
-----------------------------

The forms ``JP["field_name"]`` and ``JP.field_name`` are equivalent:

>>> from functools import reduce
>>> def my_sum(content, field_name, initial):
...     return reduce(
...         lambda x, y: x + y,
...         find_all(content, JP.employees[:][field_name]),
...         initial
...     )
>>> my_sum(content, "age", 0)
51
>>> my_sum(content, "account", "")
'johndoejanedoejudedeer'


Field name by regular expressions
---------------------------------

Sometimes you have a JSON format where types are represented by JSON objects, e.g.

>>> content = {
...     "apple": [{"name": "red delicious"}, {"name": "punakaneli"}],
...     "pear": [{"name": "wilhelm"}, {"name": "conference"}]
... }

i.e. it's not a union list of records with a type discriminator ``[{"type": "apple", "name": ...}, ...]``.
Iterating over all the fruits, regardless of their type, in our example ``content`` above can
be achieved by:

>>> list(find_all(content, JP["apple|pear"][:].name))
['red delicious', 'punakaneli', 'wilhelm', 'conference']

if you are only interested in apples and pears, or

>>> list(find_all(content, JP[".*"][:].name))
['red delicious', 'punakaneli', 'wilhelm', 'conference']

if you are interested in fruits other than apples and pears.

Note, that the expression ``JP["*"]`` is also supported, but that's `not` a regular expression,
merely a conventional JSON Path notation, and equivalent to ``JP[:]``:

>>> list(find_all([5, 42, 137], JP["*"]))
[5, 42, 137]


Suppressing indexing errors and key errors
------------------------------------------

By default, path expressions are strict, e.g. for ``list`` indexes:

>>> list(find_all([0, 1], JP[2]))
Traceback (most recent call last):
    ...
IndexError: list index out of range

and for ``dict`` keys:

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


Utility ``find_next()``
-----------------------

Often, you just need a first value, roughly equivalent to a ``next(find_all(...))``
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


Utilities: finding unique and duplicate items
---------------------------------------------

A common task is to find only unique items in data, e.g.

>>> content = [{"hi": 1}, {"hi": 2}, {"hi": 1}, {"hi": 3}, {"hi": -22}, {"hi": 3}]
>>> list(find_all_unique(content, JP[:].hi))
[1, 2, 3, -22]

and of course you can ask for the paths, too

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
