import textwrap
from pathlib import Path

import pytest

import syrupy

SUBDIR = "subdir_not_on_default_path"


@pytest.fixture(autouse=True)
def cache_clear():
    syrupy.__import_extension.cache_clear()


@pytest.fixture
def testfile(testdir):
    subdir = testdir.mkdir(SUBDIR)

    Path(
        subdir,
        "extension_file.py",
    ).write_text(
        textwrap.dedent(
            """
            from syrupy.extensions.single_file import SingleFileSnapshotExtension
            class MySingleFileExtension(SingleFileSnapshotExtension):
                pass
            """
        )
    )

    testdir.makepyfile(
        test_file=(
            """
            def test_default(snapshot):
                assert b"default extension serializer" == snapshot
            """
        )
    )

    return testdir


def test_snapshot_default_extension_option_success(testfile):
    testfile.makeini(
        f"""
        [pytest]
        pythonpath =
            {Path(testfile.tmpdir, SUBDIR)}
    """
    )

    result = testfile.runpytest(
        "-v",
        "--snapshot-update",
        "--snapshot-default-extension",
        "extension_file.MySingleFileExtension",
    )
    result.stdout.re_match_lines((r"1 snapshot generated\."))
    assert Path(
        testfile.tmpdir, "__snapshots__", "test_file", "test_default.raw"
    ).exists()
    assert not result.ret


def test_snapshot_default_extension_option_module_not_found(testfile):
    result = testfile.runpytest(
        "-v",
        "--snapshot-update",
        "--snapshot-default-extension",
        "extension_file.MySingleFileExtension",
    )
    result.stdout.re_match_lines((r".*: Module 'extension_file' does not exist.*",))
    assert not Path(
        testfile.tmpdir, "__snapshots__", "test_file", "test_default.raw"
    ).exists()
    assert result.ret


def test_snapshot_default_extension_option_failure(testfile):
    testfile.makeini(
        f"""
        [pytest]
        pythonpath =
            {Path(testfile.tmpdir, SUBDIR)}
    """
    )

    result = testfile.runpytest(
        "-v",
        "--snapshot-update",
        "--snapshot-default-extension",
        "extension_file.DoesNotExistExtension",
    )
    result.stdout.re_match_lines((r".*: Member 'DoesNotExistExtension' not found.*",))
    assert not Path(
        testfile.tmpdir, "__snapshots__", "test_file", "test_default.raw"
    ).exists()
    assert result.ret
