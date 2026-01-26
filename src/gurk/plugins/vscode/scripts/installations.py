from gurk import (
    InstallCommandsBase,
    install_packages_from_txt_file,
    parse_task_args,
)


class VSCodeInstallCommands(InstallCommandsBase):
    VSC_EXT = "code --install-extension"


def install_vscode_extensions(*args: list[str]) -> None:
    """
    Install VSCode extensions.
    """
    # Parse task args
    task_args = parse_task_args(args)

    # Install extensions
    install_packages_from_txt_file(
        VSCodeInstallCommands.VSC_EXT, task_args.config_file
    )
