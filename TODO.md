Look for TODOs in code. Otherwise, look at:

# !!! Major !!!
- Update the README with proper documentation
- Update and document pytests, and use them in CI (e.g. make sure there is no `✖ Failure` in output)
- Have a `--force` (and/or `--reinstall`) argument to override checks (i.e. run even if already installed/configured)
- Issue assignee workflow seems to trigger twice on each issue creation, if no assignee is given

# Minor
- Add mujoco stuff (mujoco, dmcontrol, sim applications)
- (If possible) Only run CI on new or edited tasks
- Add file with list of debian file links (then get and dpkg (or step apt?) them)
- Maybe, when cmstp is run for the very first time, propose to do pre-setup first (then create mock file in pkg or so to mark that cmstp was already run once)
    - Or just add big NOTE in README -> but that may not be seen by those installing via pipx
- Define and document behaviour of using none, one of, or both `--config-file` and `--config-directory`
    - How can a config file in a config dir repo be specified?
        - (Maybe) If it's an absolute path, look there. If it is relative, look locally and then in the repo
- Reduce the config files here to the most basic, non-invasive ones (just to have some example)
- Test cyclic `supercedes` fields
- Update logging to file (i.e. `CMSTP START ...`) to only have a single CMSTP section, and fill stuff in there
- Remove uninstallations from "enable_all" etc. Or better, have a "counterpart" field or similar and if both install/uninstall are enabled, disable uninstall (say this in debug, not info/warning message)
- It seems that something may suspend all tasks running (if many are running)
    - Maybe this is caused by one task failing?
    - Can be restarted sing `fg %<id>` (bash; manually) (see id from output: `[<id>]+ Stopped`), but ofc that should not be necessary in the long term
- Maybe add a `requires-restart` flag or so to each task and make final message depend on that
- If a dependency task fails, downstream tasks should not be run
- If verbose is set, save the modified scripts in log dir
- Make dev instructions (e.g. to add a task, edit <...>; to add a field to tasks, edit <...>; to add a test, edit <...>; etc.)
- Remove `sudo: mon_handle_sigchld: waitpid: No child processes` outputs
- (If possible) Add checks to PyPI workflow to perform a version bump in pyproject.toml if necessary
- Allow user creation (incl. permission)
    - Read out and automatically add to all groups (except sudo) and if `--sudo` flag is given, also add to sudo group
- Restructure `default.yaml` 'file' field, to specify one for each OS type (ubuntu, macos, windows)
    - If null, then skip with warning via scheduler
    - Shell scripts will be OS-specific. Question is, should python scripts be so too or rather made cross-platform?
