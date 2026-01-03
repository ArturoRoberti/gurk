There are 2 types of commands available via `cmstp`: [core](#core-commands) and [additional](#additional-commands) ones.

# Core commands
These are the commands that are able to run a variety of tasks, e.g. installing packages. See the available commands via
```bash
cmstp --help
```

## Use a central config file
You can specify tasks to run via a config file. Please see the instructions on the `enabled.yaml` config file in the [`config README`](../src/cmstp/config/README.md) for more information, or use the `info` command to get more details (see [below](#info)).

## Use command line
You can also run tasks directly via the command line. All instructions can be found via
```bash
cmstp <command> --help
```

For example, to run specific installation tasks, use
```bash
cmstp install --tasks <task1>:arg1 <task2> <task3>:arg1:arg2
```

## Note on task fields
You can pass arguments to each task via the config file or command line, see above.

Furthermore, some tasks use their own config file (e.g. to specify a list of packages to install) - these have to have the same names and the default ones and be placed in a config directory, which can be specified via the `--config-directory` flag when running a core command. Further information on this (incl. examples) can be found in the default [config directory](../src/cmstp/config/) and it [README](../src/cmstp/config/README.md) or via the `info` command (see [below](#info)).


# Additional commands
## setup
This command should be used before using any core command, as it sets up the necessary environment for `cmstp` to run properly. It sets up git (SSH keys, user credentials), gives instructions on how to disable secure boot, and more. See details via
```bash
cmstp setup --help
```

## info
This command can give you more information about available tasks, how to use configuration files, and can print out system information. See details via
```bash
cmstp info --help
```
