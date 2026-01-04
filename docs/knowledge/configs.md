# Overview
As mentioned in the [commands overview](commands.md#1-use-a-config-file), you may use a config file to customize which tasks run and with which arguments.

Furthermore, some tasks use their own config files to read lists of packages, settings, etc. to apply. This document describes how to work with these config files.

# Config directory structure
By default, gurk uses a built-in config directory located inside the installation. You can find its location by running (for any core command):
```bash
gurk <command> --help
```
and looking for the `--config-directory` flag's default in its description. There, in each config file, you can see the expected structure and file formats. In general, the config directory is has one subfolder for each core command.

# Use custom config directories
You can point gurk to your own config directory (local path or git URL) via the `--config-directory` flag on any core command. This config directory should mirror the default layout, with subfolders for each core command containing equally named config files. Should a task-specific config file be missing, gurk disables that task if enabled.

The config directory can also be specified via a git repo, e.g.
```bash
gurk <command> --config-directory git@github.com:ArturoRoberti/gurk_config.git
```
We can **highly recommend** to create your own config directory in a git repository and point gurk to it via the `--config-directory` flag, so that you can easily set up any new system with your preferred settings and packages. This is what is done in the above [example config repo](https://github.com/ArturoRoberti/gurk_config.git).
