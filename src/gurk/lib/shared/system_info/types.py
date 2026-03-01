from typing import TypedDict


class SystemInfo(TypedDict):
    """Detailed information about the host operating system."""

    # fmt: off
    type:              str
    kernel:            str
    simulate_hardware: bool
    name:              str
    codename:          str
    version:           str
    arch:              str
    manufacturer:      str
    # fmt: on
