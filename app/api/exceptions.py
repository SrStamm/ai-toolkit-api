"""HTTP-boundary exceptions for the API layer."""

from fastapi import HTTPException


class ApiError(HTTPException):
    """HTTP error carrying the standard API error envelope fields."""

    def __init__(
        self, status_code: int, code: str, message: str, retryable: bool = False
    ) -> None:
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(status_code=status_code, detail=message)
