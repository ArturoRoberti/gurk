# Overview
Plugins are managed via the `gurk pull`, `gurk upgrade`, and `gurk remove` commands.
- `pull`: Download and install plugins from remote repositories. This also supports specifying specific git branches, commits or versions to pull. Alternatively, install plugins from local directories to a discoverable location.
- `upgrade`: Update installed plugins with known remotes to their latest versions from their remote repositories. Versioning is done by seeing at which commit the version specified in the plugin's `pyproject.toml` file was created, and updating to that commit on the remote repository.
- `remove`: Uninstall plugins from the local system. This also allows purging all cache and mentions of the plugin (**NOTE**: Purging is not possible for officially supported core plugins).
