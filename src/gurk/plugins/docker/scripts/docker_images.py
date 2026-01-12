from typing import NotRequired, TypedDict

import commentjson

from gurk.lib.helpers import (
    InstallCommands,
    Logger,
    install_packages_from_list,
    parse_task_args,
)


def install_docker_images(*args: list[str]) -> None:
    """
    Pull docker images from Docker Hub.
    """
    # Parse task args
    task_args = parse_task_args(args)

    # Typing helper classes
    class DockerImageInfo(TypedDict):
        # fmt: off
        image:    str
        registry: NotRequired[str]
        tag:      NotRequired[str]
        # fmt: on

    # Load docker images - also expand environment variables
    docker_images_info: list[DockerImageInfo] = commentjson.load(
        task_args.config_file.open("r", encoding="utf-8")
    )
    docker_images = [
        f"{item.get('registry', 'docker.io')}/{item['image']}:{item.get('tag', 'latest')}"
        for item in docker_images_info
    ]
    if not docker_images:
        Logger.step(
            "No docker images found in the provided config file. Skipping pulling of docker images.",
        )
        return

    # (STEP) Pulling docker images
    install_packages_from_list(InstallCommands.DOCKER, docker_images)
