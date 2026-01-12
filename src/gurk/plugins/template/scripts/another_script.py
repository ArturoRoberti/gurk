from gurk import parse_task_args


def another_function(*args: list[str]) -> None:
    """This is another descriptive docstring for another_function."""
    # Parse task args (if needed)
    task_args = parse_task_args(args)

    print("This is another sample function in another_script.py")


if __name__ == "__main__":
    another_function("arg1", "arg2")
