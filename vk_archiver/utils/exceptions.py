"""Custom exception hierarchy for VK Archiver.

This module defines a comprehensive exception hierarchy for the VK Archiver
application. It provides specific exception types for different error scenarios
to enable better error handling and debugging throughout the application.
"""

from typing import Any


class VKScroblerError(Exception):
    """Base exception class for all VK Archiver errors.

    This is the root exception class that all other exceptions in the VK Archiver
    should inherit from. It provides a common interface for error
    handling and can be used as a catch-all for any application-specific errors.

    Attributes:
        message: Human-readable error message
        details: Optional additional details about the error
        original_exception: Optional original exception that caused this error
    """

    def __init__(
        self,
        message: str,
        details: str | None = None,
        original_exception: Exception | None = None,
    ) -> None:
        """
        Initialize VKScroblerError.

        Args:
            message: Human-readable error message
            details: Optional additional details about the error
            original_exception: Optional original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.details = details
        self.original_exception = original_exception

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class AuthenticationError(VKScroblerError):
    """Raised when authentication with VK API fails.

    This exception is raised when there are issues with VK API authentication,
    such as missing or invalid access tokens, expired tokens, or authentication
    configuration problems.
    """

    def __init__(
        self,
        message: str,
        details: str | None = None,
        original_exception: Exception | None = None,
    ) -> None:
        """
        Initialize AuthenticationError.

        Args:
            message: Human-readable error message
            details: Optional additional details about the error
            original_exception: Optional original exception that caused this error
        """
        super().__init__(message, details, original_exception)


class ConfigurationError(VKScroblerError):
    """Raised when there are configuration-related issues.

    This exception is raised when there are problems with application
    configuration, such as missing required settings, invalid configuration
    values, or configuration file issues.
    """

    def __init__(
        self,
        message: str,
        details: str | None = None,
        original_exception: Exception | None = None,
    ) -> None:
        """
        Initialize ConfigurationError.

        Args:
            message: Human-readable error message
            details: Optional additional details about the error
            original_exception: Optional original exception that caused this error
        """
        super().__init__(message, details, original_exception)


class ValidationError(VKScroblerError):
    """Raised when input validation fails.

    This exception is raised when user input or data validation fails,
    such as invalid user IDs, group IDs, chat IDs, or other parameter
    validation issues.
    """

    def __init__(
        self,
        message: str,
        details: str | None = None,
        original_exception: Exception | None = None,
    ) -> None:
        """
        Initialize ValidationError.

        Args:
            message: Human-readable error message
            details: Optional additional details about the error
            original_exception: Optional original exception that caused this error
        """
        super().__init__(message, details, original_exception)


class DownloadError(VKScroblerError):
    """Raised when photo or video download operations fail.

    This exception is raised when there are issues during the download
    process, such as network errors, file system errors, or problems
    with the download itself.
    """

    def __init__(
        self,
        message: str,
        details: str | None = None,
        original_exception: Exception | None = None,
        url: str | None = None,
        file_path: str | None = None,
    ) -> None:
        """
        Initialize DownloadError.

        Args:
            message: Human-readable error message
            details: Optional additional details about the error
            original_exception: Optional original exception that caused this error
            url: Optional URL that failed to download
            file_path: Optional file path where download was attempted
        """
        super().__init__(message, details, original_exception)
        self.url = url
        self.file_path = file_path


class APIError(VKScroblerError):
    """Raised when VK API calls fail or return errors.

    This exception is raised when there are issues with VK API calls,
    such as API rate limiting, API errors, network connectivity issues,
    or invalid API responses.
    """

    def __init__(
        self,
        message: str,
        details: str | None = None,
        original_exception: Exception | None = None,
        api_method: str | None = None,
        response_data: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize APIError.

        Args:
            message: Human-readable error message
            details: Optional additional details about the error
            original_exception: Optional original exception that caused this error
            api_method: Optional VK API method that failed
            response_data: Optional API response data for debugging
        """
        super().__init__(message, details, original_exception)
        self.api_method = api_method
        self.response_data = response_data


class FileSystemError(VKScroblerError):
    """Raised when file system operations fail.

    This exception is raised when there are issues with file system
    operations, such as permission errors, disk space issues, or
    problems creating directories or files.
    """

    def __init__(
        self,
        message: str,
        details: str | None = None,
        original_exception: Exception | None = None,
        file_path: str | None = None,
        operation: str | None = None,
    ) -> None:
        """
        Initialize FileSystemError.

        Args:
            message: Human-readable error message
            details: Optional additional details about the error
            original_exception: Optional original exception that caused this error
            file_path: Optional file path involved in the operation
            operation: Optional file system operation that failed
        """
        super().__init__(message, details, original_exception)
        self.file_path = file_path
        self.operation = operation


class NetworkError(VKScroblerError):
    """Raised when network-related operations fail.

    This exception is raised when there are network connectivity issues,
    such as connection timeouts, DNS resolution failures, or other
    network-related problems.
    """

    def __init__(
        self,
        message: str,
        details: str | None = None,
        original_exception: Exception | None = None,
        url: str | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Initialize NetworkError.

        Args:
            message: Human-readable error message
            details: Optional additional details about the error
            original_exception: Optional original exception that caused this error
            url: Optional URL that caused the network error
            status_code: Optional HTTP status code if applicable
        """
        super().__init__(message, details, original_exception)
        self.url = url
        self.status_code = status_code


class RateLimitError(APIError):
    """Raised when VK API rate limits are exceeded.

    This exception is raised when the application hits VK API rate limits
    and needs to wait before making additional requests.
    """

    def __init__(
        self,
        message: str,
        details: str | None = None,
        original_exception: Exception | None = None,
        retry_after: int | None = None,
        api_method: str | None = None,
    ) -> None:
        """
        Initialize RateLimitError.

        Args:
            message: Human-readable error message
            details: Optional additional details about the error
            original_exception: Optional original exception that caused this error
            retry_after: Optional seconds to wait before retrying
            api_method: Optional VK API method that hit the rate limit
        """
        super().__init__(message, details, original_exception, api_method)
        self.retry_after = retry_after


class PermissionError(VKScroblerError):
    """Raised when permission-related issues occur.

    This exception is raised when there are permission issues, such as
    insufficient VK API permissions, file system permission errors, or
    access denied errors.
    """

    def __init__(
        self,
        message: str,
        details: str | None = None,
        original_exception: Exception | None = None,
        resource: str | None = None,
        required_permission: str | None = None,
    ) -> None:
        """
        Initialize PermissionError.

        Args:
            message: Human-readable error message
            details: Optional additional details about the error
            original_exception: Optional original exception that caused this error
            resource: Optional resource that permission was denied for
            required_permission: Optional permission that was required
        """
        super().__init__(message, details, original_exception)
        self.resource = resource
        self.required_permission = required_permission


class ResourceNotFoundError(VKScroblerError):
    """Raised when a requested resource is not found.

    This exception is raised when a requested resource (user, group, chat,
    photo, etc.) is not found or is inaccessible.
    """

    def __init__(
        self,
        message: str,
        details: str | None = None,
        original_exception: Exception | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> None:
        """
        Initialize ResourceNotFoundError.

        Args:
            message: Human-readable error message
            details: Optional additional details about the error
            original_exception: Optional original exception that caused this error
            resource_type: Optional type of resource that was not found
            resource_id: Optional ID of the resource that was not found
        """
        super().__init__(message, details, original_exception)
        self.resource_type = resource_type
        self.resource_id = resource_id


class InitializationError(VKScroblerError):
    """Raised when application initialization fails.

    This exception is raised when there are issues during application
    initialization, such as missing dependencies, configuration issues,
    or setup problems.
    """

    def __init__(
        self,
        message: str,
        details: str | None = None,
        original_exception: Exception | None = None,
        component: str | None = None,
    ) -> None:
        """
        Initialize InitializationError.

        Args:
            message: Human-readable error message
            details: Optional additional details about the error
            original_exception: Optional original exception that caused this error
            component: Optional component that failed to initialize
        """
        super().__init__(message, details, original_exception)
        self.component = component
