# Overview
There are four main GitHub workflows used in this repository:
1. [CI (Continuous Integration)](#ci)
2. [Workflow CI](#workflow-ci)
3. [Version Bumping](#version-bumping)
4. [PyPI Publishing](#pypi-publishing)

# CI
On every PR, the [CI](../../.github/workflows/ci.yml) performs:
- Pre-commit checks (same as local ones, see the [documentation](pre_commit.md))
	- If any fixable checks fail, the workflow auto-pushes fixes
	- If checks are unfixable, the workflow fails
- Unit tests using `pytest` (see [documentation](commands.md)):
	- Tests validity of affected task configuration files
	- Tests validity of affected task scripts
	- Tests affected tasks themselves

# CI (Workflow)
On every issue and PR, the [Workflow CI](../../.github/workflows/workflow_ci.yml):
- Labels new Issues and PRs or reminds user to do so
- Ensures an assignee is set at all times
- (On PRs) Checks the branch name. The branch name must match the following patterns:
	- `<fix|feature>/<short-description>` for most users
	- `dev/<codeowner_lowercase>` for permanent branches of [CODEOWNERS](../../.github/CODEOWNERS)

# Version Bumping
At a daily interval, the [Version Bumping](../../.github/workflows/versioning.yml) workflow checks if any package plugin has a new release. If so, the package version is bumped to the remote version, and a PR is created with the changes (on which the CI runs).

# PyPI Publishing
On every push to main, the new package code is automatically published to PyPI using the [PyPI Publishing](../../.github/workflows/pypi_publish.yml) workflow. If necessary, a version bump is automatically performed as well.
