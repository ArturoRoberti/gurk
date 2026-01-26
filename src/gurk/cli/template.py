import shutil
from pathlib import Path

import tomli_w
from ruamel.yaml import YAML

from gurk.lib.logger import ActiveLogger, Logger
from gurk.lib.utils.common import PACKAGE_SRC_PATH
from gurk.lib.utils.configs import load_toml
from gurk.lib.utils.plugins import GURK_MANIFEST_FILENAME, GurkArgumentParser


def main(argv, prog, description):
    parser = GurkArgumentParser(
        prog=prog,
        description=description,
    )
    parser.add_argument(
        "-n",
        "--name",
        type=str,
        default="template-gurk-plugin",
        help="Name of the new plugin",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Allow overwriting an existing (plugin) folder in the current working directory.",
    )
    args = parser.parse_args(argv)

    # Execute with active logger
    logger = Logger(args.verbose, args.non_interactive)
    with ActiveLogger(logger):
        # Determine destination path
        dest: Path = Path.cwd() / args.name
        if dest.exists():
            if args.force:
                shutil.rmtree(dest)
                logger.debug(f"Removed existing folder '{dest.as_posix()}'.")
            else:
                logger.fatal(
                    f"Cannot create plugin folder '{args.name}' in '{dest.parent.as_posix()}': "
                    f"Destination path '{dest.as_posix()}' already exists."
                )
                return

        # Copy the template plugin to the current working directory
        shutil.copytree(
            PACKAGE_SRC_PATH / "plugins" / "template",
            dest,
        )
        logger.debug(f"Copied template plugin to '{dest.as_posix()}'")

        # Replace plugin name
        versioning_file = dest / "pyproject.toml"
        metadata = load_toml(versioning_file)
        metadata["project"]["name"] = args.name
        with versioning_file.open("wb") as f:
            f.write(tomli_w.dumps(metadata).encode("utf-8"))

        # Rename manifest names
        ## Setup YAML handler
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=2, offset=0)
        yaml.Representer.add_representer(
            type(None),
            lambda self, data: self.represent_scalar(
                "tag:yaml.org,2002:null", "null"
            ),
        )  # conserve 'null'

        ## Read data
        manifest_file = dest / GURK_MANIFEST_FILENAME
        with manifest_file.open("r") as f:
            data = yaml.load(f)

        ## Modify data
        seen_task_maps: set[int] = set()

        def rename_tasks_in_mapping(task_map):
            # task_map is a mapping: {task_name: task_def}
            obj_id = id(task_map)
            if obj_id in seen_task_maps:
                return
            seen_task_maps.add(obj_id)

            for task_name in list(task_map.keys()):
                task = task_map.pop(task_name)
                new_name = task_name.replace("template", args.name)
                print(f"Renaming task '{task_name}' to '{new_name}'")
                task_map[new_name] = task

        tasks = data.get("tasks")
        if tasks:
            rename_tasks_in_mapping(tasks)

        for option in data["options"].values():
            rename_tasks_in_mapping(option)

        # Write back
        with manifest_file.open("w") as f:
            yaml.dump(data, f)
