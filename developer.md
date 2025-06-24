Everything is manual, for now.

# Installing

Have a python environment for `awesone` (e.g. conda).

```
pip install -e ".[testing,develop]
```

With this, you get
- `pytest`
- `build` and  `twine`

# Running tests

```
python -m doctest README.rst
pytest tests
isort aweson
black aweson
mypy aweson
pylint aweson
```

# Releasing

Based on [these instructions](https://packaging.python.org/en/latest/tutorials/packaging-projects/).

## Prerequisite: PyPI registration and API Token

(One time setup)

In your `~/.pypirc` file:

```
[pypi]
  username = __token__
  password = <API_TOKEN>
```

With this, `twine` should be able to upload locally built packages.

## Create a git tag

```
git tag -m "Releasing N.N.N" -a "N.N.N"
```

verify by `git tag`.

## Build packages

```
rm -rf dist
python -m build
```

Check the contents of `./dist/` folder:
- should have source `aweson-N.N.N.tar.gz` and wheel `aweson-N.N.N-py3-none-any.whl` package files
- where `N.N.N` matches the version you've created with `git tag`
- verify source package content `tar -ztf dist/aweson-N.N.N.tar.gz`
- verify wheel package content `unzip -l dist/aweson-N.N.N-py3-none-any.whl`

## Upload to PyPI

```
python -m twine upload dist/*
```

## Git push

```
git push N.N.N
```

## Verify uploaded version

In a pristine python environment:

```
pip install aweson=N.N.N
python
>>> from aweson import JP, find_all
>>> content = {"hello": "world"}
>>> next(find_all(content, JP.hello))
'world'
```
