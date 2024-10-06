import pytest


@pytest.fixture
def testcases():
    return {
        "base": (
            """
            def test_a(snapshot):
                assert snapshot(name="xyz") == "case 1"
                assert snapshot(name="zyx") == "case 2"
            """
        ),
        "modified": (
            """
            def test_a(snapshot):
                assert snapshot(name="xyz") == "case 1"
                assert snapshot(name="zyx") == "case ??"
            """
        ),
    }


@pytest.fixture
def run_testcases(testdir, testcases):
    testdir.makepyfile(test_1=testcases["base"])
    result = testdir.runpytest(
        "-v",
        "--snapshot-update",
    )
    result.stdout.re_match_lines(r"2 snapshots generated\.")
    return testdir, testcases


def test_run_all(run_testcases):
    testdir, testcases = run_testcases
    result = testdir.runpytest(
        "-v",
    )
    result.stdout.re_match_lines("2 snapshots passed")
    assert result.ret == 0


def test_failure(run_testcases):
    testdir, testcases = run_testcases
    testdir.makepyfile(test_1=testcases["modified"])
    result = testdir.runpytest(
        "-v",
    )
    result.stdout.re_match_lines("1 snapshot failed. 1 snapshot passed.")
    assert result.ret == 1


def test_update(run_testcases):
    testdir, testcases = run_testcases
    testdir.makepyfile(test_1=testcases["modified"])
    result = testdir.runpytest(
        "-v",
        "--snapshot-update",
    )
    assert "Can not relate snapshot name" not in str(result.stdout)
    result.stdout.re_match_lines("1 snapshot passed. 1 snapshot updated.")
    assert result.ret == 0
