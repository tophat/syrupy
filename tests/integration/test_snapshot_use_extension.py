import pytest


@pytest.fixture
def testcases_initial(testdir):
    testdir.makeconftest(
        """
        import pytest

        from syrupy.extensions.amber import AmberSnapshotExtension
        from syrupy.extensions.image import (
            PNGImageSnapshotExtension,
            SVGImageSnapshotExtension,
        )
        from syrupy.extensions.single_file import SingleFileSnapshotExtension


        class CustomSnapshotExtension(AmberSnapshotExtension):
            _file_extension = ""

            def serialize(self, data, **kwargs):
                return str(data)

            @classmethod
            def get_snapshot_name(cls, *, test_location, index):
                testname = test_location.testname[::-1]
                return f"{testname}.{index}"

            @classmethod
            def _get_file_basename(cls, *, test_location, index):
                return test_location.basename[::-1]

        @pytest.fixture
        def snapshot_custom(snapshot):
            return snapshot.use_extension(CustomSnapshotExtension)


        @pytest.fixture
        def snapshot_single(snapshot):
            return snapshot.use_extension(SingleFileSnapshotExtension)


        @pytest.fixture
        def snapshot_png(snapshot):
            return snapshot.use_extension(PNGImageSnapshotExtension)


        @pytest.fixture
        def snapshot_svg(snapshot):
            return snapshot.use_extension(SVGImageSnapshotExtension)
        """
    )
    return {
        "passed": (
            """
            def test_passed_custom(snapshot_custom):
                assert snapshot_custom == 'passed1'
                assert snapshot_custom == 'passed2'

            def test_passed_single(snapshot_single):
                assert snapshot_single == b'passed1'
                assert snapshot_single == b'passed2'
            """
        ),
        "failed": (
            """
            def test_failed_single(snapshot_single):
                assert snapshot_single == 'failed'

            def test_failed_image(snapshot_png):
                assert "not a byte string" == snapshot_png
            """
        ),
    }


@pytest.fixture
def testcases_updated(testcases_initial):
    updated_testcases = {
        "passed": (
            """
            def test_passed_single(snapshot_single):
                assert snapshot_single == b'passed'
            """
        )
    }
    return {**testcases_initial, **updated_testcases}


@pytest.fixture
def generate_snapshots(testdir, testcases_initial):
    testdir.makepyfile(test_file=testcases_initial["passed"])
    result = testdir.runpytest("-v", "--snapshot-update")
    return result, testdir, testcases_initial


def test_unsaved_snapshots(testdir, testcases_initial):
    testdir.makepyfile(test_file=testcases_initial["passed"])
    result = testdir.runpytest("-v")
    result.stdout.re_match_lines(
        (r".*Snapshot 'test_passed_single' does not exist!", r".*\+ b'passed1'")
    )
    assert result.ret == 1


def test_failed_snapshots(testdir, testcases_initial):
    testdir.makepyfile(test_file=testcases_initial["failed"])
    result = testdir.runpytest("-v", "--snapshot-update")
    result.stdout.re_match_lines(r"2 snapshots failed\.")
    assert result.ret == 1


def test_generated_snapshots(generate_snapshots):
    result = generate_snapshots[0]
    result.stdout.re_match_lines(r"4 snapshots generated\.")
    assert "snapshots unused" not in result.stdout.str()
    assert result.ret == 0


def test_unmatched_snapshots(generate_snapshots, testcases_updated):
    testdir = generate_snapshots[1]
    testdir.makepyfile(test_file=testcases_updated["passed"])
    result = testdir.runpytest("-v")
    result.stdout.re_match_lines(r"1 snapshot failed\. 2 snapshots unused\.")
    assert result.ret == 1


def test_updated_snapshots(generate_snapshots, testcases_updated):
    testdir = generate_snapshots[1]
    testdir.makepyfile(test_file=testcases_updated["passed"])
    result = testdir.runpytest("-v", "--snapshot-update")
    result.stdout.re_match_lines(r"1 snapshot updated\. 2 unused snapshots deleted\.")
    assert result.ret == 0


def test_warns_on_snapshot_name(generate_snapshots):
    result = generate_snapshots[0]
    result.stdout.re_match_lines(
        (
            r".*Warning:\s+",
            r"\s+Can not relate snapshot location",
            r"\s+Can not relate snapshot name",
            r"4 snapshots generated\.",
        )
    )
    assert result.ret == 0
