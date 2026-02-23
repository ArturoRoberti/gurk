class _PytestException(Exception):
    """Base class for custom exceptions in pytests."""

    def __init__(self, message: str):
        prefix = f"[{self.__class__.__name__}] "
        super().__init__(prefix + message)


class PytestInputException(_PytestException):
    """Custom exception type for invalid input in pytests."""

    def __init__(self, message: str):
        prefix = "Invalid input: "
        super().__init__(prefix + message)


class PytestUnexpectedException(_PytestException):
    """Exception raised when an unexpected error occurs during testing."""

    def __init__(self, message: str):
        prefix = "Unexpected error: "
        super().__init__(prefix + message)
