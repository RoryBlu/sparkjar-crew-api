"""
Exception classes for CrewClient

This module defines all exception classes used by the crew client
to avoid circular import issues.
"""


class CrewClientError(Exception):
    """Base exception for crew client errors"""
    pass


class CrewNotFoundError(CrewClientError):
    """Raised when requested crew is not found"""
    pass


class CrewExecutionError(CrewClientError):
    """Raised when crew execution fails"""
    pass


class CrewServiceUnavailableError(CrewClientError):
    """Raised when crews service is unavailable"""
    pass