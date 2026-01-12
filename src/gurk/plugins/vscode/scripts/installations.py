from gurk import (
    InstallCommands,
    install_packages_from_txt_file,
    parse_task_args,
)


def install_vscode_extensions(*args: list[str]) -> None:
    """
    Install VSCode extensions.
    """
    # Parse task args
    task_args = parse_task_args(args)

    # Install extensions
    install_packages_from_txt_file(
        InstallCommands.VSC_EXT, task_args.config_file
    )
