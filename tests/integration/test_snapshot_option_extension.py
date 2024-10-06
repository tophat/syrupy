from pathlib import Path

import pytest


@pytest.fixture
def testfile(testdir):
    testdir.makepyfile(
        test_file=(
            """
            def test_default(snapshot):
                assert b"default extension serializer" == snapshot
            """
        ),
    )
    return testdir


def test_snapshot_default_extension_option_success(testfile):
    result = testfile.runpytest(
        "-v",
        "--snapshot-update",
        "--snapshot-default-extension",
        "syrupy.extensions.single_file.SingleFileSnapshotExtension",
    )
    result.stdout.re_match_lines(r"1 snapshot generated\.")
    assert Path(
        testfile.tmpdir, "__snapshots__", "test_file", "test_default.raw"
    ).exists()
    assert not result.ret


def test_snapshot_default_extension_option_failure(testfile):
    result = testfile.runpytest(
        "-v",
        "--snapshot-update",
        "--snapshot-default-extension",
        "syrupy.extensions.amber.DoesNotExistExtension",
    )
    result.stdout.re_match_lines((r".*: Member 'DoesNotExistExtension' not found.*",))
    assert not Path(
        testfile.tmpdir, "__snapshots__", "test_file", "test_default.raw"
    ).exists()
    assert result.ret
