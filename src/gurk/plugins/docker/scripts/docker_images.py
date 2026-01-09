from typing import NotRequired, TypedDict

import commentjson

from gurk.core.logger import Logger
from gurk.lib.helpers import (
    InstallCommands,
    get_config_args,
    install_packages_from_list,
)


def install_docker_images(*args: list[str]) -> None:
    """
    Pull docker images from Docker Hub.

    :param args: Configuration arguments
    :type args: list[str]
    """
    # Parse config args
    _, config_file, _, _ = get_config_args(args)
    if config_file is None:
        Logger.step(
            "Skipping pulling of docker images, as no task config file is provided",
            warning=True,
        )
        return

    # Typing helper classes
    class DockerImageInfo(TypedDict):
        # fmt: off
        image:    str
        registry: NotRequired[str]
        tag:      NotRequired[str]
        # fmt: on

    # Load docker images - also expand environment variables
    docker_images_info: list[DockerImageInfo] = commentjson.load(
        config_file.open("r", encoding="utf-8")
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
