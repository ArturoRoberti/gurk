# Contributing to cmstp
Thank you for your interest in contributing! Your help is appreciated.

## How to Contribute
For new feature suggestions or bug fixes, please

1. **Create an issue** using a proposed issue template in the [Issues](https://github.com/ArturoRoberti/cmstp/issues) tab
2. **Create a branch** following the naming convention `(feature|fix)/<description>`
3. **Test your changes** to ensure nothing is broken. Make sure to install and use the pre-commit hooks to ensure no issues on the CI (see the [pre-commit hooks](#pre-commit-hooks) section)
4. **Commit and push your changes** with clear, descriptive messages
5. **Create a pull request** using a proposed pull request template in the [Pull Requests](https://github.com/ArturoRoberti/cmstp/pulls) tab. As github only allows one PR template (see [issue](https://github.com/refined-github/refined-github/issues/1621)), please follow its instructions guiding you to the other templates. Also, please add applicable labels to your PR.

Furthermore, feel free to fork this repo to implement more personal touches. If you do something you think others may benefit from, please contribute back to this main repository.

## Code Guidelines
- Add or edit tasks in the `config/default.yaml` file. Please conform to the guidelines laid out at the top of it
- In each task, you may use `# (STEP) ...` comments, which indicate progress steps and are used to advance the progress bar. These are substituted with print stataments (with variable expansion) at runtime. As each instance of such a comment is counted as only one step when counting the total progress of a task, please don't insert them into reusable code and/or loops, as they would print and advance the progress bar multiple times.
- For updating a task progress without advancing it, you may use `Logger.step()` (python) resp. `log_step` (bash) function calls. Should these send (via a passed argument) output to stderr, then a function will be marked as partially done if the rest of the task completes successfully.
- Please use a `check_<task>` function in each task (or major sub-task) that can be used at the start and end of the task to verify the task software is (not) installed
- Make the dependency tree clear via the `config/default.yaml` file (`depends_on` entries). Additionally, please also check for dependencies at the start of each task code itself.
- Write clear, concise descriptions, comments and git commit messages
- Add pytests where applicable

## Pre-commit hooks
Please install the pre-commit hooks for this repo, to ensure code quality. The pre-commit hooks will also run in GitHub PRs and are required to pass.

To install the pre-commit hooks, use
```bash
pipx install pre-commit
cd <cmstp-path> && pre-commit install
```
The hooks will then run on each commit. You can also run the hooks manually via
```bash
pre-commit run --all-files
```

## Code of Conduct
Please be respectful and considerate in all interactions.

Thank you for helping improve this project!
