from pytest import Metafunc, Parser

try:
    from gurk import __version__  # noqa: F401
except ImportError:
    raise ImportError("The gurk package needs to be installed to run pytests.")


def pytest_addoption(parser: Parser):
    parser.addoption(
        "--tasks",
        action="store",
        default="",
        help="Comma-separated list of tasks to test",
    )


def pytest_generate_tests(metafunc: Metafunc):
    if "task" in metafunc.fixturenames:
        raw: str = metafunc.config.getoption("--tasks")
        metafunc.parametrize("task", raw.split(","))
