# Package Configs
Main configuration files are in `src/cmstp/config/`:
- `default.yaml`: Defines all available tasks used by core commands.
- `enabled.yaml`: The default config file as would be created by the user. Enables all tasks, except ones that may be too disruptive or take up too much space for the average user.

Each file has minimal instructions at its top - these can also be printed with
```bash
cmstp info [-c|--custom-config] [-d|--default-config]
```

# Config directory
Some tasks may use their own config files for lists of packages, settings, etc. These should be stored under `src/cmstp/config/<command>` for the resp. task command.

For any simple lists, please use `.txt` files with one entry per line. For more complex configs, please use `.json(c)` or `.yaml` files with appropriate structure. Add comments at the top of each file to briefly explain how to populate it.

Please also open a PR (or contact the maintainers) to add this file to this package's sister repository, [`cmstp_config`](https://github.com/ArturoRoberti/cmstp_config).
