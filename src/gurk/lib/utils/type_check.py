import json
import os
from functools import cache, wraps
from importlib.metadata import Distribution

from pydantic import ConfigDict, ValidationError, validate_call

from .constants import NO_ANSWERS, PACKAGE_NAME, YES_ANSWERS


@cache
def _is_typecheck_active() -> bool:
    # (Priority) Check environment variable override
    gurk_typecheck = os.getenv("GURK_TYPECHECK")
    if gurk_typecheck in YES_ANSWERS:
        return True
    elif gurk_typecheck in NO_ANSWERS:
        return False
    else:
        # See if the package is installed in editable mode
        direct_url = Distribution.from_name(PACKAGE_NAME).read_text(
            "direct_url.json"
        )
        return (
            json.loads(direct_url).get("dir_info", {}).get("editable", False)
        )


class InputValidationError(Exception):
    """Custom error type for input validation errors in typecheck."""

    pass


_typecheck = validate_call(
    config=ConfigDict(
        strict=True, extra="forbid", arbitrary_types_allowed=True
    )
)


def typecheck(func):
    """
    Decorator to perform runtime type checking on function inputs using Pydantic's validate_call.
    It also formats validation errors to include the offending input type and value for easier debugging.

    :raises InputValidationError: If the input validation fails, with details on the offending inputs.
    """
    if not _is_typecheck_active():
        return func

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return _typecheck(func)(*args, **kwargs)
        except ValidationError as e:
            # Format errors with the offending input type/value for easier debugging
            messages = []
            for err in e.errors():
                loc = ".".join(str(x) for x in err["loc"])
                bad_input = err.get("input", "<missing>")
                bad_type = type(bad_input).__name__
                # Limit repr length to keep messages compact
                bad_repr = repr(bad_input)
                if len(bad_repr) > 200:
                    bad_repr = bad_repr[:197] + "..."
                messages.append(
                    f"{loc}: {err['msg']} (got {bad_type}: {bad_repr})"
                )
            raise InputValidationError(
                "Wrong input(s) to '"
                + func.__name__
                + "':\n"
                + "\n".join(messages)
            ) from None

    return wrapper
