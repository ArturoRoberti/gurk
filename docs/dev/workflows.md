# Overview
There are three main GitHub workflows used in this repository:
1. [CI (Continuous Integration)](#ci)
2. [Workflow CI](#workflow-ci)
3. [PyPI Publishing](#pypi-publishing)

# CI
On every PR, the [CI](../../.github/workflows/ci.yml) performs:
- Pre-commit checks (same as local ones, see the [documentation](pre_commit.md))
	- If any fixable checks fail, the workflow auto-pushes fixes
	- If checks are unfixable, the workflow fails
- Unit tests using `pytest` (see [documentation](commands.md)):
	- Tests validity of package configuration files (`default.yaml`, `enabled.yaml`)
	- Tests validity of package scripts
	- Determines the tasks affected by a given PR and tests those

# CI (Workflow)
On every issue and PR, the [Workflow CI](../../.github/workflows/workflow_ci.yml):
- Labels new Issues and PRs or reminds user to do so
- Ensures an assignee is set at all times
- (On PRs) Checks the branch name. The branch name must match the following patterns:
	- `<fix|feature>/<short-description>` for most users
	- `dev/<codeowner_lowercase>` for permanent branches of [CODEOWNERS](../../.github/CODEOWNERS)

# PyPI Publishing
On every push to main, the new package code is automatically published to PyPI using the [PyPI Publishing](../../.github/workflows/pypi_publish.yml) workflow. If necessary, a version bump is automatically performed as well.
