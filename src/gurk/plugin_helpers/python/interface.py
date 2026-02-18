from gurk.lib.utils import typecheck


@typecheck
def log_step(message: str, /, *, warning: bool = False) -> None:
    """
        Log a step message without advancing progress. Only to be used from within tasks.

    :param message: Message to log
    :type message: str
    :param warning: Whether or not this is a warning (default: false)
    :type warning: bool
    """
    step_type = "STEP_NO_PROGRESS"
    if warning:
        step_type += "_WARNING"
    print(f"\n__{step_type}__: {message}")
