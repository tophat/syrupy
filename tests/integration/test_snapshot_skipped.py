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
        "raise-skipped": (
            """
            import pytest
            def test_skipped(snapshot):
                pytest.skip("Skipping...")
                assert snapshot == 'unused'
            """
        ),
        "mark-skipped": (
            """
            import pytest
            @pytest.mark.skip
            def test_skipped(snapshot):
                assert snapshot == 'unused'
            """
        ),
        "not-skipped": (
            """
            def test_skipped(snapshot):
                assert snapshot == 'unused'
            """
        ),
    }


@pytest.fixture
def run_testcases(testdir, testcases):
    pyfile_content = "\n\n".join([testcases["used"], testcases["not-skipped"]])
    testdir.makepyfile(test_file=pyfile_content)
    result = testdir.runpytest("-v", "--snapshot-update")
    result.stdout.re_match_lines(r"2 snapshots generated\.")
    return testdir, testcases


def test_mark_skipped_snapshots(run_testcases):
    testdir, testcases = run_testcases
    pyfile_content = "\n\n".join([testcases["used"], testcases["mark-skipped"]])
    testdir.makepyfile(test_file=pyfile_content)

    result = testdir.runpytest("-v")
    result.stdout.re_match_lines(r"1 snapshot passed\.$")
    assert result.ret == 0


def test_raise_skipped_snapshots(run_testcases):
    testdir, testcases = run_testcases
    pyfile_content = "\n\n".join([testcases["used"], testcases["raise-skipped"]])
    testdir.makepyfile(test_file=pyfile_content)

    result = testdir.runpytest("-v")
    result.stdout.re_match_lines(r"1 snapshot passed\.$")
    assert result.ret == 0


def test_skipped_snapshots_update(run_testcases):
    testdir, testcases = run_testcases
    pyfile_content = "\n\n".join([testcases["used"], testcases["raise-skipped"]])
    testdir.makepyfile(test_file=pyfile_content)

    result = testdir.runpytest("-v", "--snapshot-update")
    result.stdout.re_match_lines(r"1 snapshot passed\.$")
    assert result.ret == 0
