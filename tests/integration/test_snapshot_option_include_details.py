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
def extra_testcases():
    return {
        "extra_a": (
            """
            def test_extra_a(snapshot):
                assert snapshot == 'extra_a'
            """
        ),
        "extra_b": (
            """
            def test_extra_b(snapshot):
                assert snapshot == 'extra_b'
            """
        ),
    }


@pytest.fixture
def run_testfiles_with_update(testdir):
    def run_testfiles_with_update_impl(**testfiles):
        testdir.makepyfile(
            **{
                filename: "\n\n".join(cases.values())
                for (filename, cases) in testfiles.items()
            }
        )
        result = testdir.runpytest("-v", "--snapshot-update")
        result.stdout.re_match_lines(r"[0-9]+ snapshots generated\.")
        return testdir

    return run_testfiles_with_update_impl


@pytest.mark.parametrize(
    (
        "options",
        "expected_status_code",
    ),
    (
        (("-v", "--snapshot-details"), 1),
        (("-v", "--snapshot-details", "--snapshot-warn-unused"), 0),
    ),
)
def test_unused_snapshots_details(
    options, expected_status_code, run_testfiles_with_update, testcases
):
    testdir = run_testfiles_with_update(test_file=testcases)
    testdir.makepyfile(test_file=testcases["used"])

    result = testdir.runpytest(*options)
    result.stdout.re_match_lines(
        (
            r"1 snapshot passed\. 1 snapshot unused\.",
            r"Unused test_unused \(__snapshots__[\\/]test_file.ambr\)",
            r"Re-run pytest with --snapshot-update to delete unused snapshots\.",
        )
    )
    assert result.ret == expected_status_code


def test_unused_snapshots_details_multiple_tests(
    run_testfiles_with_update, testcases, extra_testcases
):
    testdir = run_testfiles_with_update(
        test_file=testcases, test_second_file=extra_testcases
    )
    testdir.makepyfile(
        test_file="\n\n".join(testcases.values()),
        test_second_file="",
    )

    result = testdir.runpytest("-v", "--snapshot-details")
    result.stdout.re_match_lines(
        (
            r"2 snapshots passed\. 2 snapshots unused\.",
            r"Unused test_extra_a, test_extra_b "
            r"\(__snapshots__[\\/]test_second_file.ambr\)",
            r"Re-run pytest with --snapshot-update to delete unused snapshots\.",
        )
    )
    assert result.ret == 1


def test_unused_snapshots_details_multiple_locations(
    run_testfiles_with_update, testcases, extra_testcases
):
    testdir = run_testfiles_with_update(
        test_file=testcases, test_second_file=extra_testcases
    )
    testdir.makepyfile(
        test_file=testcases["used"],
        test_second_file=extra_testcases["extra_a"],
    )

    result = testdir.runpytest("-v", "--snapshot-details")
    result.stdout.re_match_lines_random(
        (
            r"2 snapshots passed\. 2 snapshots unused\.",
            r"Unused test_extra_b \(__snapshots__[\\/]test_second_file.ambr\)",
            r"Unused test_unused \(__snapshots__[\\/]test_file.ambr\)",
            r"Re-run pytest with --snapshot-update to delete unused snapshots\.",
        )
    )
    assert result.ret == 1


def test_unused_snapshots_details_no_details_on_deletion(
    run_testfiles_with_update, testcases
):
    testdir = run_testfiles_with_update(test_file=testcases)
    testdir.makepyfile(test_file=testcases["used"])

    result = testdir.runpytest("-v", "--snapshot-details", "--snapshot-update")
    result.stdout.re_match_lines(
        (
            r"1 snapshot passed\. 1 unused snapshot deleted\.",
            r"Deleted test_unused \(__snapshots__[\\/]test_file.ambr\)",
        )
    )
    assert result.ret == 0
