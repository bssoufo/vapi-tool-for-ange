class VAPIException(Exception):
    """Base exception for VAPI related errors."""
    pass


class VAPIAPIError(VAPIException):
    """Exception raised for VAPI API errors."""

    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class AssistantNotFoundError(VAPIException):
    """Exception raised when an assistant is not found."""
    pass


class SquadNotFoundError(VAPIException):
    """Exception raised when a squad is not found."""
    pass


class AgentNotFoundError(VAPIException):
    """Exception raised when an agent is not found."""
    pass


class ValidationError(VAPIException):
    """Exception raised for validation errors."""
    pass