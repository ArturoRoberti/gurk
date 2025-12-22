Look for TODOs in code. Otherwise, look at:

# !!! Major !!!
- Update and document pytests, and use them in CI (e.g. fail pytest if there is `✖ Failure` or `⚠ Partial` in output)

# Minor
## CI
- (If possible) Only run CI on new or edited tasks
## Core
- Update logging to file (i.e. `CMSTP START ...`) to only have a single CMSTP section, and fill stuff in there
- Make dev instructions (e.g. to add a task, edit <...>; to add a field to tasks, edit <...>; to add a test, edit <...>; etc.)
## Features
- Add mujoco stuff (mujoco, dmcontrol, sim applications)
- Add file with list of debian file links (then get and dpkg (or step apt?) them)
    - How to specify pkg? Via url, gitref, local path, package path, ...?
- Allow user creation (incl. permission)
    - Read out and automatically add to all groups (except sudo) and if `--sudo` flag is given, also add to sudo group
- Setup Browser Bookmarks
- Setup Autocompletions
