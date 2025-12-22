Look for TODOs in code. Otherwise, look at:

# !!! Major !!!
- Update and document pytests (one for each task)
- Run CI on new or edited tasks only:
    - See changed files, and which functions they contain (or entrypoints)
    - See which tasks use those functions/entrypoints
    - Run only those tasks via corresponding pytests, which check there is no `✖ Failure` or `⚠ Partial` in output

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
