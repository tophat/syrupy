from pathlib import Path


def test_multiple_file_extensions(testdir):
    file_extension = "ext2.ext1"

    testcase = f"""
    import pytest
    from syrupy.extensions.single_file import SingleFileSnapshotExtension

    class DotInFileExtension(SingleFileSnapshotExtension):
        _file_extension = "{file_extension}"

    @pytest.fixture
    def snapshot(snapshot):
        return snapshot.use_extension(DotInFileExtension)

    def test_dot_in_filename(snapshot):
        assert b"expected_data" == snapshot
    """

    test_file: Path = testdir.makepyfile(test_file=testcase)

    result = testdir.runpytest("-v", "--snapshot-update")
    result.stdout.re_match_lines(r"1 snapshot generated\.")
    assert "snapshots unused" not in result.stdout.str()
    assert result.ret == 0

    snapshot_file = (
        Path(test_file).parent
        / "__snapshots__"
        / "test_file"
        / f"test_dot_in_filename.{file_extension}"
    )
    assert snapshot_file.exists()

    result = testdir.runpytest("-v")
    result.stdout.re_match_lines(r"1 snapshot passed\.")
    assert "snapshots unused" not in result.stdout.str()
    assert result.ret == 0


def test_class_style(testdir):
    """
    Regression test for https://github.com/syrupy-project/syrupy/issues/717
    """

    testcase = """
    import pytest
    from syrupy.extensions.json import JSONSnapshotExtension

    @pytest.fixture
    def snapshot(snapshot):
        return snapshot.use_extension(JSONSnapshotExtension)

    class TestFoo:
        def test_foo(self, snapshot):
            assert { 'key': 'value' } == snapshot
    """

    test_file: Path = testdir.makepyfile(test_file=testcase)

    result = testdir.runpytest("-v", "--snapshot-update")
    result.stdout.re_match_lines(r"1 snapshot generated\.")
    assert "deleted" not in result.stdout.str()
    assert result.ret == 0

    snapshot_file = (
        Path(test_file).parent / "__snapshots__" / "test_file" / "TestFoo.test_foo.json"
    )
    assert snapshot_file.exists()

    result = testdir.runpytest("-v")
    result.stdout.re_match_lines(r"1 snapshot passed\.")
    assert "snapshots unused" not in result.stdout.str()
    assert result.ret == 0
