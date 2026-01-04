# Overview
This package uses pre-commit hooks that
- Check code syntax
- Format code
- Format config files
- Scan code for security secrets
- Checks that the package version is higher than the latest PyPI version

Please install these pre-commit hooks when contributing to the project; via:
```bash
pipx install pre-commit
cd <gurk_repo> && pre-commit install
```

They will run automatically before each commit. Alternatively, you can run them manually via:
```bash
pre-commit run --all-files
```

Don't change the pre-commit hooks unless absolutely necessary. If you do, please inform the maintainers.
