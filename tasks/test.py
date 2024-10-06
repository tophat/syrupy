
from invoke import task

from .utils import ctx_run


@task(
    help={
        "coverage": "Build and report on test coverage",
        "test-pattern": "Pattern used to select test files to run",
        "update-snapshots": "Create, update or delete snapshot files",
        "verbose": "Verbose output e.g. non captured logs etc.",
    }
)
def test(
    ctx,
    coverage=False,
    test_pattern=None,
    update_snapshots=False,
    verbose=False,
    debug=False,
):
    """
    Run entire test suite
    """
    flags = {
        "-s -vv": verbose,
        f"-k {test_pattern}": test_pattern,
        "--snapshot-update": update_snapshots,
    }
    coverage_module = "coverage run -m " if coverage else ""
    test_flags = " ".join(flag for flag, enabled in flags.items() if enabled)

    if debug and coverage:
        raise Exception("The debug and coverage options are mutually exclusive.")

    if debug:
        ctx_run(
            ctx,
            f"python -m debugpy --listen 5678 --wait-for-client -m pytest {test_flags} ./tests",
        )
    else:
        ctx_run(ctx, f"python -m {coverage_module}pytest {test_flags} ./tests")

    if coverage:
        ctx_run(ctx, "coverage lcov -o coverage/coverage.lcov")
