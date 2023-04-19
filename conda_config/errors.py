"""
Module with helper functions that help deal with parsing errors of the condarc file.
"""

from pathlib import Path
from typing import Sequence

from pydantic import ValidationError

#: Suggestion for where to find a documentation on configuration parameters
CONDARC_PARSE_ERROR_SUGGESTION = (
    "Please refer to our documentation to read more about configuration variables"
    " and the values the can have:\n"
    "https://docs.conda.io/projects/conda/en/latest/configuration.html"
)

CONFIG_ERROR_PREFIX = "Unable to parse configuration file"


def format_validation_error(exc: ValidationError, path: Path) -> str:
    """
    Formats a ``pydantic.Validation`` error as a ``str``
    """
    error_str = []
    for err in exc.errors():
        loc = ",".join(err.get("loc", tuple()))
        ctx = err.get("ctx", {})
        given = ctx.get("given")
        permitted = ctx.get("permitted")
        msg = err.get("msg")

        # Add strings
        error_str.append(f"\n  {loc}: \n")
        error_str.append(f"    {msg}\n")

        if given and permitted:
            error_str.append("  provided_value: ")
            error_str.append(f"'{given}'\n")

    return "".join(
        (f"{CONFIG_ERROR_PREFIX}: {path}\n", *error_str),
    )


def format_all_validation_errors(validation_errors: Sequence[str]) -> str:
    """
    Formats a sequence of errors as a single ``str``
    """
    error_str = "\n\n".join(validation_errors)
    error_str += f"\n\n{CONDARC_PARSE_ERROR_SUGGESTION}"

    return error_str
