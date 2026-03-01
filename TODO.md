Look for TODOs in code. Otherwise, look at:

# !!! Major !!!
- Pytests
    - Handle/Fix `RUNNER_SPECIFIC_TASKS` (see `utils/tasks.py`). These should make use of the `simulate_hardware` flag.
    - (Where possible) Add pytest for non-core gurk commands
- Expand uninstallation scripts. These can then also be used to lessen the size of installations on CI runners.
- Allow versioning via tags

# Minor
## Features
- Add mujoco stuff (mujoco, dmcontrol, sim applications)
- Add file with list of debian file links (then get and dpkg (or step apt?) them)
    - How to specify pkg? Via url, git query, local path, package path, ...?
- Allow user creation (incl. permission)
    - Read out and automatically add to all groups (except sudo) and if `--sudo` flag is given, also add to sudo group
- Setup Browser Bookmarks
- Setup Autocompletions
- Split task dependencies into "required" and "optional" dependencies.
    - "Optional" dependencies would allow the dependency to run first, but would not be a requirement before running a task.
    - If that task is added in the run option, it is run first. Otherwise, it is not run
    - Could be useful for:
        - "install-mamba" (mamba, not micromamba) which requires conda to be installed, but could be skipped if micromamba is used instead.
        - configuring the filestructure first, then copying repos and symlinks.
        - pinning apps after installing any packages
