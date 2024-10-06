def test_ignores_non_function_nodes(testdir):
    conftest = """
        import pytest

        class CustomItem(pytest.Item):
            def __init__(self, name, **kwargs):
                super().__init__(name, **kwargs)
                self._nodeid += "::CUSTOM"

            def runtest(self):
                pass

        def pytest_collect_file(file_path, parent):
            return CustomItem.from_parent(
                name=file_path.name,
                path=file_path,
                parent=parent
            )
        """
    testcase = """
        def test_example(snapshot):
            assert snapshot == 1
        """
    testdir.makeconftest(conftest)
    testdir.makepyfile(test_file=testcase)
    result = testdir.runpytest("test_file.py", "-v", "--snapshot-update")
    result.stdout.re_match_lines(r".*test_file.py::CUSTOM.*")
    assert result.ret == 0


def test_handles_pyargs_non_module_when_both_given(testdir):
    testdir.makeconftest("")
    testcase = """
        def test_example(snapshot):
            assert snapshot == 1
        """
    testdir.makepyfile(test_file=testcase)
    result = testdir.runpytest(
        "-v", "test_file.py", "--pyargs", "test_file", "--snapshot-update"
    )
    assert result.ret == 0


def test_does_not_print_empty_snapshot_report(testdir):
    testdir.makeconftest("")
    testcase_no_snapshots = """
        def test_example(snapshot):
            assert 1
        """
    testcase_yes_snapshots = """
        def test_example(snapshot):
            assert snapshot == 1
        """
    testdir.makepyfile(
        test_file_no=testcase_no_snapshots, test_file_yes=testcase_yes_snapshots
    )

    result = testdir.runpytest("-v", "test_file_no.py", "--snapshot-update")
    result.stdout.re_match_lines(r".*test_file_no.py.*")
    assert "snapshot report" not in result.stdout.str()
    assert "test_file_yes" not in result.stdout.str()
    assert result.ret == 0

    result = testdir.runpytest("-v", "test_file_yes.py", "--snapshot-update")
    result.stdout.re_match_lines((r".*test_file_yes.py.*", r".*snapshot report.*"))
    assert result.ret == 0
