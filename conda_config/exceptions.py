"""
Holds the exception classes for this library

* ConfigError
    - ArgumentError
    - OperationNotAllowed
"""
from __future__ import annotations


class CondaConfigError(Exception):
    def __init__(self, message: str, original_exception: Exception | None = None):
        self.message = message
        self.original_exception = original_exception


class ArgumentError(CondaConfigError):
    pass


class OperationNotAllowed(CondaConfigError):
    pass
