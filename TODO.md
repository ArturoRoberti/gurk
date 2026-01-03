Look for TODOs in code. Otherwise, look at:

# !!! Major !!!
- Docs (incl. pytests)
- Pytests: Handle/Fix `RUNNER_SPECIFIC_TASKS` (see `utils/tasks.py`). These should make use of the `simulate_hardware` flag.    - ...
- Expand uninstallation scripts. These can then also be used to lessen the size of installations on CI runners.
- Output handling in PTY has issues
    - Tracebacks are unclear (just lots of `^` characters) - maybe reduce to last file in traceback only?
    - `Logger.logrichprint` colored output is not properly rendered

# Minor
## Core
- Make dev instructions (e.g. to add a task, edit <...>; to add a field to tasks, edit <...>; to add a test, edit <...>; etc.)
## Features
- Add mujoco stuff (mujoco, dmcontrol, sim applications)
- Add file with list of debian file links (then get and dpkg (or step apt?) them)
    - How to specify pkg? Via url, gitref, local path, package path, ...?
- Allow user creation (incl. permission)
    - Read out and automatically add to all groups (except sudo) and if `--sudo` flag is given, also add to sudo group
- Setup Browser Bookmarks
- Setup Autocompletions
- (Where possible) Add pytest for non-core cmstp commands
