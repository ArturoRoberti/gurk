from gurk.lib.helpers import (
    InstallCommands,
    Logger,
    get_config_args,
    install_packages_from_txt_file,
)


def install_vscode_extensions(*args: list[str]) -> None:
    """
    Install VSCode extensions.

    :param args: Configuration arguments
    :type args: list[str]
    """
    # Parse config args
    _, config_file, _, _ = get_config_args(args)
    if config_file is None:
        Logger.step(
            "Skipping installation of VSCode extensions, as no task config file is provided",
            warning=True,
        )
        return

    # Install extensions
    install_packages_from_txt_file(InstallCommands.VSC_EXT, config_file)
