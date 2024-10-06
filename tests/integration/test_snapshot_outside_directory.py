import pytest


@pytest.fixture(params=["__snapshots__", "snapshots"])
def testcases(testdir, tmp_path, request):
    dirname = tmp_path.joinpath(request.param)
    testdir.makeconftest(
        f"""
        import pytest

        from syrupy.extensions.amber import AmberSnapshotExtension

        class CustomSnapshotExtension(AmberSnapshotExtension):
            @classmethod
            def dirname(cls, *, test_location):
                return {str(dirname)!r}

        @pytest.fixture
        def snapshot(snapshot):
            return snapshot.use_extension(CustomSnapshotExtension)
        """
    )
    return {
        "zero": (
            """
            def test_do_it(snapshot):
                pass
            """
        ),
        "one": (
            """
            def test_do_it(snapshot):
                assert snapshot == 'passed1'
            """
        ),
        "two": (
            """
            def test_do_it(snapshot):
                assert snapshot == 'passed1'
                assert snapshot == 'passed2'
            """
        ),
    }


@pytest.fixture
def generate_snapshots(testdir, testcases):
    testdir.makepyfile(test_file=testcases["two"])
    result = testdir.runpytest("-v", "--snapshot-update")
    return result, testdir, testcases


def test_generated_snapshots(generate_snapshots):
    result = generate_snapshots[0]
    result.stdout.re_match_lines(r"2 snapshots generated\.")
    assert "snapshots unused" not in result.stdout.str()
    assert result.ret == 0


def test_unmatched_snapshots(generate_snapshots):
    _, testdir, testcases = generate_snapshots
    testdir.makepyfile(test_file=testcases["one"])
    result = testdir.runpytest("-v")
    result.stdout.re_match_lines(r"1 snapshot passed. 1 snapshot unused\.")
    assert result.ret == 1


def test_updated_snapshots_partial_delete(generate_snapshots):
    _, testdir, testcases = generate_snapshots
    testdir.makepyfile(test_file=testcases["one"])
    result = testdir.runpytest("-v", "--snapshot-update")
    result.stdout.re_match_lines(r"1 snapshot passed. 1 unused snapshot deleted\.")
    assert result.ret == 0


def test_updated_snapshots_full_delete(generate_snapshots):
    _, testdir, testcases = generate_snapshots
    testdir.makepyfile(test_file=testcases["zero"])
    result = testdir.runpytest("-v", "--snapshot-update")
    result.stdout.re_match_lines(r"2 unused snapshots deleted\.")
    assert result.ret == 0
