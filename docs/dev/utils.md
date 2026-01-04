# Overview
The utility import hierarchy is as follows:
1. `cli/utils.py`: **Self-contained** utilities for CLI commands
2. `common.py` and `patterns.py`: Shared helpers and regex patterns
3. Other utility modules in `src/gurk/utils/` (can also be used by Python scripts)
4. Other utility modules in `src/gurk/scripts/python/helpers/` (should only be used by Python scripts)

No lower-level utils should depend on higher-level ones to avoid circular dependencies.
