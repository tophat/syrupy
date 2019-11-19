# 🥞 syrupy

[![Maturity badge - level 1](https://img.shields.io/badge/Maturity-Level%201%20--%20New%20Project-yellow.svg)](https://github.com/tophat/getting-started/blob/master/scorecard.md)

> _/ˈsirəpē/_

## Overview

Syrupy is a pytest snapshot plugin. It enables developers to write tests which assert immutability of computed results.

## Motivation

The most popular snapshot test plugin compatible with pytest has some core limitations which this package attempts to address by upholding some keys values:
- Extensible: If a particular data type is not supported, users should be able to easily and quickly add support.
- Idiomatic: Snapshot testing should fit naturally among other tests cases in pytest, e.g. `assert x == snapshot` vs. `snapshot.assert_match(x)`.
- Soundness: Snapshot tests should uncover even the most minute issues. Unlike other snapshot libraries, Syrupy will fail a test suite if a snapshot does not exist, not just on snapshot differences.

## Installation

```shell
python -m pip install syrupy
```

## Usage

### Basic Usage

In a pytest test file `test_file.py`:

```python
def test_foo(snapshot):
    actual = "Some computed value!"
    assert actual == snapshot
```

when you run `pytest`, the above test should fail due to a missing snapshot. Re-run pytest with the update snapshots flag like so:

```shell
pytest --update-snapshots
```

A snapshot file should be generated under a `__snapshots__` directory in the same directory as `test_file.py`. The `__snapshots__` directory and all its children should be committed along with your test code.

### Advanced Usage, Plugin Support

```python
import pytest

@pytest.fixture
def snapshot_custom(snapshot):
    return snapshot.with_class(
        io_class=CustomIOClass,
        serializer_class=CustomSerializerClass,
    )

def test_image(snapshot_custom):
    actual = "..."
    assert actual == snapshot_custom
```

Both `CustomIOClass` and `CustomSerializerClass` should extend `syrupy.io.SnapshotIO` and `syrupy.io.SnapshotSerializer` respectively.

## Uninstalling

```python
pip uninstall syrupy
```

## Contributing

Feel free to open a PR. This project is still in a very early stage, and we're still figuring out what direction we want to move towards.

To develop locally, clone this repository and run `. script/bootstrap` to install test dependencies. You can then use `invoke --help` to see a list of commands.

## Contributors

This section is automatically generated via tagging the all-contributors bot in a PR:

```
@all-contributors please add <username> for <contribution type>
```
