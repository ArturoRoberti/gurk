import pytest

from gurk.cli import template


def gurk_template(argv: list[str]) -> None:
    """
    Helper function to execute the 'gurk template' command. As this should cause no errors, it asserts that the exit code is 0 and returns nothing.

    :param argv: List of command-line arguments to pass to 'gurk template'.
    :type argv: list[str]
    """
    with pytest.raises(SystemExit) as e:
        template.main(
            argv,
            prog="gurk template",
            description="Generate a plugin template in the current working directory.",
        )
    assert (
        e.value.code == 0
    ), f"Template generation failed with exit code {e.value.code}"
