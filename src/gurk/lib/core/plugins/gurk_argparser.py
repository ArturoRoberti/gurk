import json
import os
import re
from argparse import (
    SUPPRESS,
    ArgumentDefaultsHelpFormatter,
    ArgumentParser,
    ArgumentTypeError,
    Namespace,
    RawTextHelpFormatter,
    _ArgumentGroup,
)
from collections import defaultdict
from pathlib import Path
from typing import Generic, Sequence, TypeVar

from gurk.lib.utils.common import YES_ANSWERS
from gurk.lib.utils.system_info import SystemInfo
from gurk.lib.utils.tasks import ArgsDefinition, ArgsDefinitionCollection
from gurk.lib.utils.typed_dict import validate_typed_dict


def _create_wildcard_validator(patterns: list[str]) -> tuple:
    """
    Create a validator function for wildcard patterns.

    :param patterns: List of wildcard patterns to validate against
    :type patterns: list[str]
    :return: A tuple containing a validator function and a metavar string
    :rtype: tuple
    :raises ArgumentTypeError: If validation fails
    """
    regexes = [
        re.compile("^" + re.escape(p).replace(r"\*", ".*") + "$")
        for p in patterns
    ]

    quoted = ", ".join(f"'{p}'" for p in patterns)
    metavar = "{" + ",".join(patterns) + "}"

    def validate(value: str) -> str:
        if any(rx.match(value) for rx in regexes):
            return value
        raise ArgumentTypeError(
            f"invalid choice: {value!r} (choose from {quoted})"
        )

    return validate, metavar


def check_args_dict(args_dict: ArgsDefinitionCollection) -> None:
    """
    Extend the parser with arguments defined in a plugin.

    :param args_dict: Dictionary of argument definitions
    :type args_dict: ArgsDefinitionCollection
    :raises ArgumentTypeError: If argument definitions are invalid
    """
    # Validate structure
    if not (
        isinstance(args_dict, dict)
        and all(isinstance(key, str) for key in args_dict.keys())
        and all(
            validate_typed_dict(arg_spec, ArgsDefinition)
            for arg_spec in args_dict.values()
        )
    ):
        raise ArgumentTypeError("Invalid argument definitions structure")

    # Validate mutually exclusive groups
    mutex_groups = defaultdict(list)
    for name, spec in args_dict.items():
        mutex = spec.get("mutex")
        if mutex:
            mutex_groups[mutex].append(name)
    for members in mutex_groups.values():
        if len(members) < 2:
            raise ArgumentTypeError(
                "Mutually exclusive group must have at least two members"
            )

    # Validate arguments
    for name, spec in args_dict.items():
        # nargs
        nargs = spec.get("nargs")
        if nargs and not (isinstance(nargs, int) or nargs in ("?", "*", "+")):
            raise ArgumentTypeError(
                f"Invalid nargs value for argument '{name}'"
            )

        # Boolean flags - Validate nothing else is set
        default = spec.get("default")
        if isinstance(default, bool) and any(
            k not in ("help", "default", "mutex")
            for k, v in spec.items()
            if v is not None
        ):
            raise ArgumentTypeError(
                f"Invalid boolean flag argument definition for '{name}'"
            )

        # choices
        choices = spec.get("choices")
        if choices is not None:
            # Validate choices structure
            if (
                not isinstance(choices, list)
                or not choices
                or not all(isinstance(c, str) for c in choices)
            ):
                raise ArgumentTypeError(
                    f"Invalid choices structure for argument '{name}'"
                )

            # Validate default(s) against choices
            if default is not None:
                if not isinstance(default, list):
                    default = [default]

                # Validate default structure
                if not default or not all(isinstance(d, str) for d in default):
                    raise ArgumentTypeError(
                        f"Invalid default structure for argument '{name}'"
                    )

                # Validate that all defaults are in choices
                validator, _ = _create_wildcard_validator(choices)
                for d in default:
                    try:
                        validator(d)
                    except ArgumentTypeError:
                        raise ArgumentTypeError(
                            f"Default value {d!r} for argument '{name}' is not in choices"
                        )

            # Validate nargs if no default is given
            elif nargs in ("?", "*"):
                raise ArgumentTypeError(
                    f"Invalid nargs value for argument '{name}' when no default is given"
                )


class CleanHelpFormatter(RawTextHelpFormatter, ArgumentDefaultsHelpFormatter):
    """
    Custom formatter that:
      - preserves newlines in help text
      - hides default=None and default=False for boolean flags
      - annotates mutually exclusive args automatically
      - respects max_help_position
    """

    def __init__(self, prog):
        super().__init__(prog, max_help_position=80)

    def _get_help_string(self, action):
        if action.default not in (None, SUPPRESS):
            # A default is specified and is not purposefully suppressed
            # NOTE: Includes boolean flags ("store_true" / "store_false")
            default_suffix = f"(default: {action.default!s})"
            if not action.help:
                return default_suffix
            else:
                return action.help + " " + default_suffix
        else:
            # No default specified or default is purposefully suppressed
            return action.help or ""


class VerboseNamespace(Namespace):
    verbose: bool


class NonInteractiveNamespace(Namespace):
    non_interactive: bool


class ForceNamespace(Namespace):
    force: bool


class SimpleTaskNamespace(Namespace):
    system_info: str
    config_file: str | None


class ComplexTaskNamespace(Namespace):
    system_info: SystemInfo
    config_file: Path | None


class TaskParserNamespace(ForceNamespace, ComplexTaskNamespace):
    pass


class DefaultNamespace(VerboseNamespace, NonInteractiveNamespace):
    pass


T = TypeVar("T", bound=Namespace)


class GurkArgumentParser(Generic[T], ArgumentParser):
    """
    Custom ArgumentParser that uses CleanHelpFormatter and adds common gurk CLI options.
    """

    def __init__(
        self,
        add_verbose_arg: bool = True,
        add_non_interactive_arg: bool = True,
        add_force_arg: bool = False,
        add_task_args: bool = False,
        allow_complex_types: bool = True,
        *args,
        **kwargs,
    ):
        # Some gurk internal variables
        self.required_group_title = "required arguments"
        self.add_non_interactive_arg = add_non_interactive_arg
        self.allow_complex_types = allow_complex_types

        # Use CleanHelpFormatter
        kwargs["formatter_class"] = lambda prog: CleanHelpFormatter(prog)

        # Call super init
        super().__init__(*args, **kwargs)

        # Add logger options
        if add_verbose_arg:
            self.add_argument(
                "-v",
                "--verbose",
                action="store_true",
                help="Enable verbose output",
            )
        if add_non_interactive_arg:
            self.add_argument(
                "--non-interactive",
                action="store_true",
                help="Run in non-interactive mode (disable prompts)",
            )
        if add_task_args:
            self._add_task_args()
        if add_force_arg:
            self.add_argument(
                "-f",
                "--force",
                action="store_true",
                help="Force execution of task(s) even if they don't need to run",
            )

    def _add_task_args(self) -> None:
        """
        Add common task arguments to the parser.

        :raises ArgumentTypeError: If argument validation fails
        """

        # Add system-info argument
        def json_dict(value: str) -> SystemInfo:
            """
            Validate that the input is a JSON object (dictionary).

            :param value: Input string
            :type value: str
            :return: Parsed JSON object
            :rtype: dict
            :raises ArgumentTypeError: If the input is not a valid JSON object
            """
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as e:
                raise ArgumentTypeError(f"Invalid JSON for --system-info: {e}")
            if not isinstance(parsed, dict):
                raise ArgumentTypeError(
                    "--system-info must be a JSON object (dictionary)"
                )
            return parsed

        self.add_argument(
            "--system-info",
            type=json_dict if self.allow_complex_types else str,
            required=True,
            help="JSON object with system information",
        )

        # Add config-file argument
        def existing_path(value: str) -> Path:
            """
            Validate that the input path exists.

            :param value: Input path string
            :type value: str
            :return: Path object
            :rtype: Path
            :raises ArgumentTypeError: If the path does not exist
            """
            path = Path(value)
            if not path.exists():
                raise ArgumentTypeError(f"Config file not found: {path}")
            return path

        self.add_argument(
            "--config-file",
            type=existing_path if self.allow_complex_types else str,
            default=None,
            help="Path to an existing config file",
        )

    def add_required_group(self, mutex: bool = False) -> _ArgumentGroup:
        """
        Add a 'required arguments' group to the parser.

        :param mutex: Whether the group is mutually exclusive
        :type mutex: bool
        :return: The created argument group
        :rtype: _ArgumentGroup
        """
        required = self.add_argument_group(self.required_group_title)
        if mutex:
            return required.add_mutually_exclusive_group(required=True)
        else:
            return required

    def extend_arguments(self, args_dict: ArgsDefinitionCollection) -> None:
        """
        Extend the parser with arguments defined in a plugin.

        :param args_dict: Dictionary of argument definitions
        :type args_dict: ArgsDefinitionCollection
        :raises ArgumentTypeError: If argument definitions are invalid
        """
        try:
            check_args_dict(args_dict)
        except ArgumentTypeError as e:
            raise ArgumentTypeError(
                f"Invalid argument definitions: {e}"
            ) from e

        # Collect mutually exclusive groups
        mutex_groups = defaultdict(list)
        for name, spec in args_dict.items():
            mutex = spec.get("mutex")
            if mutex:
                mutex_groups[mutex].append(name)
        argparse_mutex_groups = {
            name: self.add_mutually_exclusive_group() for name in mutex_groups
        }

        # Add arguments
        for name, spec in args_dict.items():
            kwargs = {"help": spec["help"]}  # To be passed to add_argument()

            default = spec.get("default")
            nargs = spec.get("nargs")
            choices = spec.get("choices")

            # Boolean flags
            if isinstance(default, bool):
                kwargs["action"] = "store_false" if default else "store_true"

            else:
                # Choices
                if choices is not None:
                    validator, metavar = _create_wildcard_validator(choices)
                    kwargs["type"] = validator
                    kwargs["metavar"] = metavar

                # All non-boolean argument types
                if default is not None:
                    # optional argument
                    kwargs["default"] = default
                elif nargs not in ("?", "*"):
                    # required argument
                    kwargs["required"] = True

                if nargs is not None:
                    kwargs["nargs"] = nargs

            # Choose correct target (parser or mutex group)
            mutex = spec.get("mutex")
            target = argparse_mutex_groups[mutex] if mutex else self

            # Finally, add the argument
            target.add_argument(name, **kwargs)

    def _reorder_actions(self):
        """
        Reorder actions to have required ones first.
        """
        # Reorder action groups to have 'required arguments' first
        required_group = None
        for g in self._action_groups:
            if g.title == self.required_group_title:
                required_group = g
                break
        if required_group:
            self._action_groups.remove(required_group)
            self._action_groups.insert(0, required_group)

    def print_help(self, file=None) -> None:
        # Reorder action groups to have 'required arguments' first
        self._reorder_actions()

        # Call the original print_help
        return super().print_help(file)

    def parse_args(
        self, args: Sequence[str] | None = None, namespace: None = None
    ) -> T:
        # Reorder action groups to have 'required arguments' first
        self._reorder_actions()

        # Call the original parse_args
        args = super().parse_args(args, namespace)

        # Get non-interactive mode from env var if not specified
        if self.add_non_interactive_arg and not args.non_interactive:
            args.non_interactive = (
                os.getenv("GURK_NON_INTERACTIVE", "false").lower()
                in YES_ANSWERS
            )

        return args
