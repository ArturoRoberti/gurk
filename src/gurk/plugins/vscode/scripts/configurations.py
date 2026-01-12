from pathlib import Path

import commentjson

from gurk import Logger, LoggerSeverity, parse_task_args


def configure_vscode_keybindings(*args: list[str]) -> None:
    """
    Configure VSCode keybindings.
    """
    # Parse task args
    task_args = parse_task_args(args)

    # Ensure VSCode keybindings file exists
    vscode_keys = Path.home() / ".config/Code/User/keybindings.json"
    vscode_keys.parent.mkdir(parents=True, exist_ok=True)
    if not vscode_keys.exists():
        Logger.logrichprint(
            LoggerSeverity.WARNING,
            "VSCode keybindings file does not exist, creating an empty one.",
        )
        vscode_keys.write_text("[]", encoding="utf-8")

    # Load both JSON files (supporting comments)
    existing = commentjson.load(vscode_keys.open("r", encoding="utf-8"))
    new_keys = commentjson.load(
        task_args.config_file.open("r", encoding="utf-8")
    )

    # Merge arrays like jq -s '.[0] + .[1]'
    merged = existing + new_keys

    # Write merged file back
    vscode_keys.write_text(
        commentjson.dumps(merged, indent=2), encoding="utf-8"
    )
    Logger.step("VSCode keybindings configured successfully.")
