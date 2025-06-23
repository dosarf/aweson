`aweson`
========
Traversing and manipulating hierarchical data (JSON) using pythonic JSON Path-like expressions

Import the necessary stuff
--------------------------

.. code-block:: python
    >>> from aweson import JP, find_all

Iterating over hierarchical data
--------------------------------

.. code-block:: python
    >>> content = {"employees": [{"name": "Doe, John", "age": 32}, {"name": "Doe, Jane", "age": -23}, {"name": "Deer, Jude", "age": 42}, ]}
    >>> list(find_all(content, JP.employees[:].name))
    ['Doe, John', 'Doe, Jane', 'Deer, Jude']

Note that the JSON Path-like expression is _not_ a string, it's a Python expression, i.e. your
IDE will be of actual help.

Furthermore, to address all items in a list, Pythonic slice expression `[:]` is used. Naturally,
other indexing and slice expressions also work in the conventional Pythonic way:

.. code-block:: python
    >>> list(find_all(content, JP.employees[-1].name))
    ['Deer, Jude']

.. code-block:: python
    >>> list(find_all(content, JP.employees[:2].name))
    ['Doe, John', 'Doe, Jane']

You may be interested in the actual path of an item being returned, just like
you get an index alongside items when using `enumerate()`. For instance, you may want to verify
ages being non-negative, and report accurately the path of failure items:

.. code-block:: python
    >>> path, item = next(t for t in find_all(content, JP.employees[:].age, enumerate=True) if t[1] < 0)
    >>> item
    -23

Note, if argument `enumerate=True` is passed, `find_all()` returns tuples instead of single
items: the first items being JSON Path-like expression (a pointer to data, just
like an _index_ of `enumerate()`) and the second items the value itself.

The offending path, then, in human-readable format:

.. code-block:: python
    >>> str(path)
    '.employees[1].age'

The enclosing record, using `.parent` attribute of the path obtained for the offending age:

.. code-block:: python
    >>> next(find_all(content, path.parent))
    {'name': 'Doe, Jane', 'age': -23}
