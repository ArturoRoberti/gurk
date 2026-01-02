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
Please follow the guidelines defined in the [documentation](../docs/).

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

# Pytests
Please ensure your code is up-to date via the pre-commit hooks mentioned above. Furthermore, you can test the validity of package configs and scripts you may have edited/created via
```bash
cmstp pytest tests/configs.py
cmstp pytest tests/scripts.py
```

You can also test individual tasks via either using the cmstp core commands as any user would or using
```bash
cmstp pytest tests/tasks.py --tasks TASK1[,TASK2,TASK3,...]
```

Please ensure clear and concise descriptions in your commit messages.

## Code of Conduct
Please be respectful and considerate in all interactions.

Thank you for helping improve this project!
