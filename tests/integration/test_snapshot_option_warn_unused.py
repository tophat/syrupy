import pytest


@pytest.fixture
def testcases():
    return {
        "used": (
            """
            def test_used(snapshot):
                assert snapshot == 'used'
            """
        ),
        "unused": (
            """
            def test_unused(snapshot):
                assert snapshot == 'unused'
            """
        ),
    }


@pytest.fixture
def run_testcases(testdir, testcases):
    pyfile_content = "\n\n".join(testcases.values())
    testdir.makepyfile(test_file=pyfile_content)
    result = testdir.runpytest("-v", "--snapshot-update")
    result.stdout.re_match_lines(r"2 snapshots generated\.")
    return testdir, testcases


def test_unused_snapshots_failure(run_testcases):
    testdir, testcases = run_testcases
    testdir.makepyfile(test_file=testcases["used"])

    result = testdir.runpytest("-v")
    result.stdout.re_match_lines(
        (
            r"1 snapshot passed\. 1 snapshot unused\.",
            r"Re-run pytest with --snapshot-update to delete unused snapshots\.",
        )
    )
    assert result.ret == 1


def test_unused_snapshots_warning(run_testcases):
    testdir, testcases = run_testcases
    testdir.makepyfile(test_file=testcases["used"])

    result = testdir.runpytest("-v", "--snapshot-warn-unused")
    result.stdout.re_match_lines(
        (
            r"1 snapshot passed\. 1 snapshot unused\.",
            r"Re-run pytest with --snapshot-update to delete unused snapshots\.",
        )
    )
    assert result.ret == 0


def test_unused_snapshots_deletion(run_testcases):
    testdir, testcases = run_testcases
    testdir.makepyfile(test_file=testcases["used"])

    result = testdir.runpytest("-v", "--snapshot-update")
    result.stdout.re_match_lines(
        (
            r"1 snapshot passed\. 1 unused snapshot deleted\.",
            r"Deleted test_unused \(__snapshots__[\\/]test_file\.ambr\)",
        )
    )
    assert result.ret == 0
