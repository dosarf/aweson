# CHANGELOG

## 2.1.0 (2025-06-26)

- Utilities: finding duplicates, unique items

## 2.0.0 (2025-06-24)

- Support lenient iteration
  - no KeyError, IndexError raised in lenient mode
- Argument `enumerate` renamed to `with_path`, and a keyword-only argument now
- Support `["*"]` resembling JSON Path `[*]` syntax
- Support `dict` key matching by regexp
- Make string representation of paths resemble more RFC 9535

## 1.1.0 (2025-06-24)

- Support named tuples in sub-select expressions

## 1.0.1 (2025-06-23)

- fixed and evolved documentation
- doctests

## 1.0.0 (2025-06-23)

- first release
  - `find_all()`
  - with JSON Path-like expression builder
