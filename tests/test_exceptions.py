"""Tests for the VK Photos Scrobler exception hierarchy."""

from typing import TYPE_CHECKING

from vk_photos.utils.exceptions import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    DownloadError,
    FileSystemError,
    InitializationError,
    NetworkError,
    PermissionError,
    RateLimitError,
    ResourceNotFoundError,
    ValidationError,
    VKScroblerError,
)

if TYPE_CHECKING:
    pass


class TestVKScroblerError:
    """Test the base VKScroblerError class."""

    def test_base_exception_creation(self) -> None:
        """Test that VKScroblerError can be created with basic parameters."""
        error = VKScroblerError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.details is None
        assert error.original_exception is None

    def test_base_exception_with_details(self) -> None:
        """Test that VKScroblerError can be created with details."""
        error = VKScroblerError("Test error", "Additional details")
        assert str(error) == "Test error: Additional details"
        assert error.message == "Test error"
        assert error.details == "Additional details"

    def test_base_exception_with_original_exception(self) -> None:
        """Test that VKScroblerError can be created with original exception."""
        original = ValueError("Original error")
        error = VKScroblerError("Test error", original_exception=original)
        assert error.original_exception == original


class TestAuthenticationError:
    """Test the AuthenticationError class."""

    def test_authentication_error_creation(self) -> None:
        """Test that AuthenticationError can be created."""
        error = AuthenticationError("Authentication failed")
        assert isinstance(error, VKScroblerError)
        assert str(error) == "Authentication failed"


class TestConfigurationError:
    """Test the ConfigurationError class."""

    def test_configuration_error_creation(self) -> None:
        """Test that ConfigurationError can be created."""
        error = ConfigurationError("Configuration invalid")
        assert isinstance(error, VKScroblerError)
        assert str(error) == "Configuration invalid"


class TestValidationError:
    """Test the ValidationError class."""

    def test_validation_error_creation(self) -> None:
        """Test that ValidationError can be created."""
        error = ValidationError("Invalid input")
        assert isinstance(error, VKScroblerError)
        assert str(error) == "Invalid input"


class TestDownloadError:
    """Test the DownloadError class."""

    def test_download_error_creation(self) -> None:
        """Test that DownloadError can be created with basic parameters."""
        error = DownloadError("Download failed")
        assert isinstance(error, VKScroblerError)
        assert str(error) == "Download failed"
        assert error.url is None
        assert error.file_path is None

    def test_download_error_with_url_and_path(self) -> None:
        """Test that DownloadError can be created with URL and file path."""
        error = DownloadError(
            "Download failed",
            url="https://example.com/image.jpg",
            file_path="/path/to/file.jpg",
        )
        assert error.url == "https://example.com/image.jpg"
        assert error.file_path == "/path/to/file.jpg"


class TestAPIError:
    """Test the APIError class."""

    def test_api_error_creation(self) -> None:
        """Test that APIError can be created with basic parameters."""
        error = APIError("API call failed")
        assert isinstance(error, VKScroblerError)
        assert str(error) == "API call failed"
        assert error.api_method is None
        assert error.response_data is None

    def test_api_error_with_method_and_data(self) -> None:
        """Test that APIError can be created with API method and response data."""
        response_data = {"error": "Rate limit exceeded"}
        error = APIError(
            "API call failed", api_method="users.get", response_data=response_data
        )
        assert error.api_method == "users.get"
        assert error.response_data == response_data


class TestFileSystemError:
    """Test the FileSystemError class."""

    def test_file_system_error_creation(self) -> None:
        """Test that FileSystemError can be created with basic parameters."""
        error = FileSystemError("File operation failed")
        assert isinstance(error, VKScroblerError)
        assert str(error) == "File operation failed"
        assert error.file_path is None
        assert error.operation is None

    def test_file_system_error_with_path_and_operation(self) -> None:
        """Test that FileSystemError can be created with file path and operation."""
        error = FileSystemError(
            "File operation failed", file_path="/path/to/file", operation="write"
        )
        assert error.file_path == "/path/to/file"
        assert error.operation == "write"


class TestNetworkError:
    """Test the NetworkError class."""

    def test_network_error_creation(self) -> None:
        """Test that NetworkError can be created with basic parameters."""
        error = NetworkError("Network connection failed")
        assert isinstance(error, VKScroblerError)
        assert str(error) == "Network connection failed"
        assert error.url is None
        assert error.status_code is None

    def test_network_error_with_url_and_status(self) -> None:
        """Test that NetworkError can be created with URL and status code."""
        error = NetworkError(
            "Network connection failed", url="https://example.com", status_code=404
        )
        assert error.url == "https://example.com"
        assert error.status_code == 404


class TestRateLimitError:
    """Test the RateLimitError class."""

    def test_rate_limit_error_creation(self) -> None:
        """Test that RateLimitError can be created with basic parameters."""
        error = RateLimitError("Rate limit exceeded")
        assert isinstance(error, APIError)
        assert isinstance(error, VKScroblerError)
        assert str(error) == "Rate limit exceeded"
        assert error.retry_after is None

    def test_rate_limit_error_with_retry_after(self) -> None:
        """Test that RateLimitError can be created with retry_after."""
        error = RateLimitError(
            "Rate limit exceeded", retry_after=60, api_method="users.get"
        )
        assert error.retry_after == 60
        assert error.api_method == "users.get"


class TestPermissionError:
    """Test the PermissionError class."""

    def test_permission_error_creation(self) -> None:
        """Test that PermissionError can be created with basic parameters."""
        error = PermissionError("Permission denied")
        assert isinstance(error, VKScroblerError)
        assert str(error) == "Permission denied"
        assert error.resource is None
        assert error.required_permission is None

    def test_permission_error_with_resource_and_permission(self) -> None:
        """Test that PermissionError can be created with resource and permission."""
        error = PermissionError(
            "Permission denied", resource="user profile", required_permission="read"
        )
        assert error.resource == "user profile"
        assert error.required_permission == "read"


class TestResourceNotFoundError:
    """Test the ResourceNotFoundError class."""

    def test_resource_not_found_error_creation(self) -> None:
        """Test that ResourceNotFoundError can be created with basic parameters."""
        error = ResourceNotFoundError("Resource not found")
        assert isinstance(error, VKScroblerError)
        assert str(error) == "Resource not found"
        assert error.resource_type is None
        assert error.resource_id is None

    def test_resource_not_found_error_with_type_and_id(self) -> None:
        """Test that ResourceNotFoundError can be created with resource type and ID."""
        error = ResourceNotFoundError(
            "Resource not found", resource_type="user", resource_id="12345"
        )
        assert error.resource_type == "user"
        assert error.resource_id == "12345"


class TestInitializationError:
    """Test the InitializationError class."""

    def test_initialization_error_creation(self) -> None:
        """Test that InitializationError can be created with basic parameters."""
        error = InitializationError("Initialization failed")
        assert isinstance(error, VKScroblerError)
        assert str(error) == "Initialization failed"
        assert error.component is None

    def test_initialization_error_with_component(self) -> None:
        """Test that InitializationError can be created with component."""
        error = InitializationError("Initialization failed", component="VK API")
        assert error.component == "VK API"


class TestExceptionHierarchy:
    """Test the exception hierarchy relationships."""

    def test_exception_inheritance(self) -> None:
        """Test that all exceptions properly inherit from VKScroblerError."""
        exceptions = [
            AuthenticationError("test"),
            ConfigurationError("test"),
            ValidationError("test"),
            DownloadError("test"),
            APIError("test"),
            FileSystemError("test"),
            NetworkError("test"),
            RateLimitError("test"),
            PermissionError("test"),
            ResourceNotFoundError("test"),
            InitializationError("test"),
        ]

        for exception in exceptions:
            assert isinstance(exception, VKScroblerError)

    def test_rate_limit_error_inheritance(self) -> None:
        """Test that RateLimitError inherits from both APIError and VKScroblerError."""
        error = RateLimitError("test")
        assert isinstance(error, APIError)
        assert isinstance(error, VKScroblerError)
