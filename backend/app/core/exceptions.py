"""
Application errors.

Services raise these errors. One handler in main.py turns them into
JSON responses, so routes never have to build error responses by hand.
"""


class AppError(Exception):
    """Base class for every expected application error."""

    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class BusinessRuleError(AppError):
    """The request is valid JSON but breaks an accounting or business rule."""

    status_code = 422


class AuthenticationError(AppError):
    status_code = 401
