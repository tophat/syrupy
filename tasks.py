import os
import re

from invoke import (
    exceptions,
    task,
)

from setup import install_requires


def ctx_run(ctx, *args, **kwargs):
    kwargs["pty"] = os.name == "posix"
    return ctx.run(*args, **kwargs)


@task
def clean(ctx):
    """
    Remove build files e.g. package, distributable, compiled etc.
    """
    ctx_run(ctx, "rm -rf *.egg-info dist build __pycache__ .pytest_cache artifacts/*")


def _parse_min_versions(requirements):
    result = []
    for req in sorted(requirements):
        match = re.match(r"([\w_]+)>=([^,]+),.*(;.*)", req)
        if match is None:
            continue
        pkg_name = match.group(1)
        min_version = match.group(2)
        result.append(f"{pkg_name}=={min_version}{match.group(3) or ''}")
    return result


@task
def requirements(ctx, upgrade=False):
    """
    Build test & dev requirements lock file
    """
    args = [
        "--no-emit-find-links",
        "--no-emit-index-url",
        "--allow-unsafe",
        "--rebuild",
    ]
    if upgrade:
        args.append("--upgrade")
    ctx_run(
        ctx,
        f"echo '-e .[dev]' | python -m piptools compile "
        f"{' '.join(args)} - -qo- | sed '/^-e / d' > dev_requirements.txt",
    )

    with open("min_requirements.txt", "w", encoding="utf-8") as f:
        min_requirements = _parse_min_versions(install_requires)
        f.write("\n".join(min_requirements))
        f.write("\n")


@task
def lint(ctx, fix=False):
    """
    Check and fix syntax
    """
    lint_commands = {
        "isort": f"python -m isort {'' if fix else '--check'} .",
        "black": f"python -m black {'' if fix else '--check'} .",
        "flake8": "python -m flake8 src tests benchmarks *.py",
        "mypy": "python -m mypy --strict src benchmarks",
    }
    last_error = None
    for section, command in lint_commands.items():
        print(f"\033[1m[{section}]\033[0m")
        try:
            ctx_run(ctx, command)
        except exceptions.Failure as ex:
            last_error = ex
        print()
    if last_error:
        raise last_error


@task
def install(ctx):
    """
    Install the current development version of syrupy
    """
    ctx_run(ctx, "python -m pip install -U .")


@task(
    help={
        "coverage": "Build and report on test coverage",
        "dev": "Use syrupy development version",
        "test-pattern": "Pattern used to select test files to run",
        "update-snapshots": "Create, update or delete snapshot files",
        "verbose": "Verbose output e.g. non captured logs etc.",
    }
)
def test(
    ctx,
    coverage=False,
    dev=False,
    test_pattern=None,
    update_snapshots=False,
    verbose=False,
):
    """
    Run entire test suite
    """
    env = {"PYTHONPATH": "./src"} if dev else {}
    flags = {
        "-s -vv": verbose,
        f"-k {test_pattern}": test_pattern,
        "--snapshot-update": update_snapshots,
    }
    coverage_module = "coverage run -m " if coverage else ""
    test_flags = " ".join(flag for flag, enabled in flags.items() if enabled)
    ctx_run(ctx, f"python -m {coverage_module}pytest {test_flags} .", env=env)
    if coverage:
        if not os.environ.get("CI"):
            ctx_run(ctx, "coverage report")
        else:
            ctx_run(ctx, "codecov")


@task(help={"report": "Publish report as github status"})
def benchmark(ctx, report=False):
    import benchmarks

    benchmarks.main(report=report)


@task(pre=[clean])
def build(ctx):
    """
    Generate version from scm and build package distributable
    """
    ctx_run(ctx, "python setup.py sdist bdist_wheel")


@task
def publish(ctx, dry_run=True):
    """
    Upload built package to pypi
    """
    repo_url = "--repository-url https://test.pypi.org/legacy/" if dry_run else ""
    ctx_run(ctx, f"twine upload --skip-existing {repo_url} dist/*")


@task(pre=[build])
def release(ctx, dry_run=True):
    """
    Build and publish package to pypi index based on scm version
    """
    from semver import parse_version_info

    if not dry_run and not os.environ.get("CI"):
        print("This is a CI only command")
        exit(1)

    # get version created in build
    with open("version.txt", "r", encoding="utf-8") as f:
        version = str(f.read())

    try:
        should_publish_to_pypi = not dry_run and parse_version_info(version)
    except ValueError:
        should_publish_to_pypi = False

    # publish to test to verify builds
    publish(ctx, dry_run=True)

    # publish to pypi if test succeeds
    if should_publish_to_pypi:
        publish(ctx, dry_run=False)
