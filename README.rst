``aweson``
==========
Traversing and manipulating hierarchical data (JSON) using pythonic JSON Path-like expressions


Importing
---------

    >>> from aweson import JP, find_all


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

    >>> path, item = next(tup for tup in find_all(content, JP.employees[:].age, enumerate=True) if tup[1] < 0)
    >>> item
    -23

The offending path, then, in human-readable format:

    >>> str(path)
    '.employees[1].age'

The enclosing record, using ``.parent`` attribute of the path obtained for the offending age:

    >>> next(find_all(content, path.parent))
    {'name': 'Doe, Jane', 'age': -23, 'account': 'janedoe'}

Note, with argument ``enumerate=True`` passed, ``find_all()`` yields tuples instead of single
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
