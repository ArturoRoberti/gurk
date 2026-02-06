import shutil
from pathlib import Path

from gurk.lib.logger import ActiveLogger, Logger
from gurk.lib.utils.common import PACKAGE_SRC_PATH
from gurk.lib.utils.configs import dump_toml, dump_yaml, load_toml, load_yaml
from gurk.lib.utils.plugins import (
    GURK_MANIFEST_FILENAME,
    DefaultNamespace,
    GurkArgumentParser,
)


class TemplateNamespace(DefaultNamespace):
    # fmt: off
    name:  str
    force: bool
    # fmt: on


def main(argv, prog, description):
    parser = GurkArgumentParser[TemplateNamespace](
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
        help="Allow overwriting an existing (plugin) folder in the current working directory",
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
        dump_toml(versioning_file, metadata)

        # Rename manifest names
        ## Read data
        manifest_file = dest / GURK_MANIFEST_FILENAME
        data = load_yaml(manifest_file)

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
                task_map[new_name] = task

        tasks = data.get("tasks")
        if tasks:
            rename_tasks_in_mapping(tasks)

        for option in data["options"].values():
            rename_tasks_in_mapping(option)

        ## Write back
        dump_yaml(data, manifest_file)
