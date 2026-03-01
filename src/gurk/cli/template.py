import shutil
from pathlib import Path

from gurk.lib.context import GurkContext, Logger
from gurk.lib.core.plugins import (
    DefaultNamespace,
    GurkArgumentParser,
    get_relevant_plugin_files,
)
from gurk.lib.shared.configs import dump_toml, dump_yaml, load_toml, load_yaml
from gurk.lib.shared.dicts import filter_typed_dict
from gurk.lib.shared.plugins import PluginMetadata
from gurk.lib.utils import (
    GURK_MANIFEST_FILENAME,
    GURK_METADATA_FILENAME,
    TEMPLATE_PLUGIN_NAME,
    TEMPLATE_PLUGIN_PATH,
    PatternCollection,
)


class TemplateNamespace(DefaultNamespace):
    # fmt: off
    name:      str
    directory: str
    force:     bool
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
        default=TEMPLATE_PLUGIN_NAME,
        help="Name of the new plugin",
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=str,
        default=".",
        help="Directory to create the plugin in",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Allow overwriting an existing (plugin) folder in the current working directory",
    )
    args = parser.parse_args(argv)

    # Execute without writing to plugins
    with GurkContext(
        logger=Logger(
            verbose=args.verbose,
            non_interactive=args.non_interactive,
            description="Creating template plugin",
        ),
        writable=False,
    ) as ctx:
        # Check if the template plugin is available
        if TEMPLATE_PLUGIN_PATH is None:
            ctx.logger.fatal(
                "Template plugin is not available. Please ensure "
                f"'{TEMPLATE_PLUGIN_NAME}' is installed via pip."
            )

        # Check plugin name validity
        if not args.name.strip():
            ctx.logger.fatal("Plugin name cannot be empty.")
        elif not PatternCollection.NAMING.patterns.match(args.name):
            special_chars = ("-", "_")
            import sys

            print(PatternCollection.NAMING.patterns, file=sys.stderr)
            print(args.name, file=sys.stderr)
            print(
                PatternCollection.NAMING.patterns.match(args.name),
                file=sys.stderr,
            )
            if args.name.startswith(special_chars) or args.name.endswith(
                special_chars
            ):
                ctx.logger.fatal(
                    f"Plugin name '{args.name}' must start and end with a lowercase letter."
                )
            else:
                ctx.logger.fatal(
                    f"Plugin name '{args.name}' cannot have any special "
                    "characters except '_' or '-' and must be lowercase"
                )

        # Determine destination path
        dest = Path(args.directory) / args.name
        if dest.exists():
            if args.force:
                shutil.rmtree(dest)
                ctx.logger.debug(
                    f"Removed existing folder '{dest.as_posix()}'."
                )
            else:
                ctx.logger.fatal(
                    f"Cannot create plugin folder '{args.name}' in '{dest.parent.as_posix()}': "
                    f"Destination path '{dest.as_posix()}' already exists."
                )

        # Copy the template plugin to the current working directory
        relevant_files = get_relevant_plugin_files(TEMPLATE_PLUGIN_PATH)
        for rfile in relevant_files:
            dest_file = dest / rfile
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(TEMPLATE_PLUGIN_PATH / rfile, dest_file)
        ctx.logger.debug(f"Copied template plugin to '{dest.as_posix()}'")

        # Edit metadata
        versioning_file = dest / GURK_METADATA_FILENAME
        metadata = load_toml(versioning_file)
        ## Remove unnecessary fields
        metadata = filter_typed_dict(metadata, PluginMetadata)
        ## Replace plugin name
        if args.name != TEMPLATE_PLUGIN_NAME:
            # Metadata
            metadata["project"]["name"] = args.name
        dump_toml(metadata, versioning_file)
        ctx.logger.debug("Updated metadata")

        # Edit manifest
        if args.name != TEMPLATE_PLUGIN_NAME:
            # Read data
            manifest_file = dest / GURK_MANIFEST_FILENAME
            data = load_yaml(manifest_file)
            seen_task_maps: set[int] = set()

            def rename_tasks_in_mapping(task_map):
                # task_map is a mapping: {task_name: task_def}
                obj_id = id(task_map)
                if obj_id in seen_task_maps:
                    return
                seen_task_maps.add(obj_id)

                for task_name in list(task_map.keys()):
                    task = task_map.pop(task_name)
                    new_name = task_name.replace(
                        TEMPLATE_PLUGIN_NAME, args.name
                    )
                    task_map[new_name] = task

            # Replace plugin name
            tasks = data.get("tasks")
            if tasks:
                rename_tasks_in_mapping(tasks)
            for option in data["options"].values():
                rename_tasks_in_mapping(option)

            dump_yaml(data, manifest_file)
            ctx.logger.debug("Updated manifest")

        ctx.logger.done(
            f"Template plugin '{args.name}' created successfully at '{dest.as_posix()}'."
        )
