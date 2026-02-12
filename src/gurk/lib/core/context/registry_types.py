from __future__ import annotations

from copy import deepcopy
from typing import NotRequired, TypeAlias, TypedDict

from gurk.lib.utils.git_query import GitQuery


def _deepcopy_tuple(tup: tuple) -> tuple:
    """
    Deepcopy a tuple by deepcopying each item and returning a new tuple.

    :param tup: Tuple to deepcopy
    :type tup: tuple
    :return: Deepcopied tuple
    :rtype: tuple
    """
    return tuple(deepcopy(item) for item in tup)


class PluginRegistryEntry(TypedDict):
    # fmt: off
    local:   None | str
    remote:  None | GitQuery
    # fmt: on


PluginRegistry: TypeAlias = dict[str, PluginRegistryEntry]


class LocalPluginRegistryEntry(TypedDict):
    # fmt: off
    local:   None | str
    remote:  NotRequired[None | GitQuery]
    # fmt: on


class RemotePluginRegistryEntry(TypedDict):
    # fmt: off
    local:   NotRequired[None | str]
    remote:  None | GitQuery
    # fmt: on
