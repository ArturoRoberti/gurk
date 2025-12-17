Look for TODOs in code. Otherwise, look at:

# !!! Major !!!
- Update and document pytests, and use them in CI (e.g. make sure there is no `✖ Failure` or `⚠ Partial` in output)
- Find a safer way than to use askpass file for scripts

# Minor
## CI
- (If possible) Only run CI on new or edited tasks
## Core
- Test cyclic `supercedes` fields
- Update logging to file (i.e. `CMSTP START ...`) to only have a single CMSTP section, and fill stuff in there
- Remove uninstallations from "enable_all" etc. Or better, have a "counterpart" field or similar and if both install/uninstall are enabled, disable uninstall (say this in debug, not info/warning message)
- Maybe add a `requires-restart` flag or so to each task and make final message depend on that
- Make dev instructions (e.g. to add a task, edit <...>; to add a field to tasks, edit <...>; to add a test, edit <...>; etc.)
- Restructure `default.yaml` 'file' field, to specify one for each OS type (ubuntu, macos, windows)
    - If null, then skip with warning via scheduler
    - Shell scripts will be OS-specific. Question is, should python scripts be so too or rather made cross-platform?
- Make uninstallation scripts (current and future) such that if e.g. files are removed, than even if one fails (e.g. "cannot remove file: No such file or directory"), the rest is still run
## Features
- Add mujoco stuff (mujoco, dmcontrol, sim applications)
- Add file with list of debian file links (then get and dpkg (or step apt?) them)
    - How to specify pkg? Via url, gitref, local path, package path, ...?
- Allow user creation (incl. permission)
    - Read out and automatically add to all groups (except sudo) and if `--sudo` flag is given, also add to sudo group
