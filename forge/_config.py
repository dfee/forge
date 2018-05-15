_run_validators = True


def get_run_validators() -> bool:
    """
    Return whether or not validators are run.
    """
    return _run_validators


def set_run_validators(run: bool) -> None:
    """
    Set whether or not validators are run.  By default, they are run.
    """
    # pylint: disable=W0603, global-statement
    if not isinstance(run, bool):
        raise TypeError("'run' must be bool.")
    global _run_validators
    _run_validators = run