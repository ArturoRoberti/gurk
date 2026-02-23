from enum import Enum


class RegistryKind(Enum):
    # fmt: off
    HOME    = 0
    PACKAGE = 1
    # fmt: on


class ExpectedOutcome(Enum):
    SUCCESS = (0, False)
    PARTIAL = (0, True)
    FAILURE = (1, True)

    @property
    def exit_code(self) -> int:
        return self.value[0]

    @property
    def contains_errors(self) -> bool:
        return self.value[1]
