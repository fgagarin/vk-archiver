"""Tests for rate limiter functionality."""

import asyncio
import time
from unittest.mock import MagicMock

import pytest

from vk_archiver.utils.rate_limiter import RateLimitedVKAPI


class TestRateLimitedVKAPI:
    """Test cases for RateLimitedVKAPI class."""

    def test_init(self) -> None:
        """Test RateLimitedVKAPI initialization."""
        mock_vk_api = MagicMock()
        rate_limiter = RateLimitedVKAPI(mock_vk_api, requests_per_second=5)

        assert rate_limiter._vk_api == mock_vk_api
        assert rate_limiter._requests_per_second == 5
        assert len(rate_limiter._request_times) == 0

    def test_init_default_rate_limit(self) -> None:
        """Test RateLimitedVKAPI initialization with default rate limit."""
        mock_vk_api = MagicMock()
        rate_limiter = RateLimitedVKAPI(mock_vk_api)

        assert rate_limiter._requests_per_second == 3

    def test_requests_per_second_property(self) -> None:
        """Test requests_per_second property getter and setter."""
        mock_vk_api = MagicMock()
        rate_limiter = RateLimitedVKAPI(mock_vk_api, requests_per_second=3)

        assert rate_limiter.requests_per_second == 3

        rate_limiter.requests_per_second = 10
        assert rate_limiter.requests_per_second == 10

    def test_requests_per_second_setter_invalid_value(self) -> None:
        """Test requests_per_second setter with invalid value."""
        mock_vk_api = MagicMock()
        rate_limiter = RateLimitedVKAPI(mock_vk_api)

        with pytest.raises(ValueError, match="Requests per second must be positive"):
            rate_limiter.requests_per_second = 0

        with pytest.raises(ValueError, match="Requests per second must be positive"):
            rate_limiter.requests_per_second = -1

    def test_get_stats(self) -> None:
        """Test get_stats method."""
        mock_vk_api = MagicMock()
        rate_limiter = RateLimitedVKAPI(mock_vk_api, requests_per_second=5)

        stats = rate_limiter.get_stats()

        assert stats["requests_per_second"] == 5
        assert stats["current_requests_in_window"] == 0
        assert stats["requests_remaining"] == 5

    @pytest.mark.asyncio
    async def test_call_with_rate_limiting(self) -> None:
        """Test that API calls respect rate limiting."""
        mock_vk_api = MagicMock()
        mock_method = MagicMock(return_value="test_result")
        mock_vk_api.test_method = mock_method

        rate_limiter = RateLimitedVKAPI(mock_vk_api, requests_per_second=2)

        # Make first call - should not wait
        start_time = time.time()
        result = await rate_limiter.call("test_method", arg1="value1")
        first_call_time = time.time() - start_time

        assert result == "test_result"
        assert first_call_time < 0.1  # Should be very fast

        # Make second call - should not wait
        start_time = time.time()
        result = await rate_limiter.call("test_method", arg2="value2")
        second_call_time = time.time() - start_time

        assert result == "test_result"
        # Allow small scheduling jitter on CI
        assert second_call_time < 0.2  # Should be very fast

        # Make third call - should wait
        start_time = time.time()
        result = await rate_limiter.call("test_method", arg3="value3")
        third_call_time = time.time() - start_time

        assert result == "test_result"
        assert third_call_time >= 0.9  # Should wait almost 1 second

        # Verify method was called with correct arguments
        assert mock_method.call_count == 3
        mock_method.assert_any_call(arg1="value1")
        mock_method.assert_any_call(arg2="value2")
        mock_method.assert_any_call(arg3="value3")

    @pytest.mark.asyncio
    async def test_concurrent_calls(self) -> None:
        """Test that concurrent calls are properly rate limited."""
        mock_vk_api = MagicMock()
        mock_method = MagicMock(return_value="test_result")
        mock_vk_api.test_method = mock_method

        rate_limiter = RateLimitedVKAPI(mock_vk_api, requests_per_second=3)

        # Make 5 concurrent calls
        start_time = time.time()
        tasks = [rate_limiter.call("test_method", arg=i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # All calls should succeed
        assert all(result == "test_result" for result in results)

        # Should take at least 1.5 seconds (3 calls in first second, 2 calls in second second)
        assert total_time >= 1.5

        # Verify all calls were made
        assert mock_method.call_count == 5

    def test_getattr_delegation(self) -> None:
        """Test that __getattr__ properly delegates to underlying VK API."""
        mock_vk_api = MagicMock()
        mock_vk_api.existing_attribute = "test_value"
        mock_vk_api.existing_method = MagicMock(return_value="method_result")

        rate_limiter = RateLimitedVKAPI(mock_vk_api)

        # Test attribute access
        assert rate_limiter.existing_attribute == "test_value"

        # Test method access (should return a callable)
        method = rate_limiter.existing_method
        assert callable(method)

    def test_getattr_nonexistent_attribute(self) -> None:
        """Test that __getattr__ raises AttributeError for nonexistent attributes."""
        mock_vk_api = MagicMock()
        rate_limiter = RateLimitedVKAPI(mock_vk_api)

        with pytest.raises(
            AttributeError,
            match="'RateLimitedVKAPI' object has no attribute 'nonexistent'",
        ):
            _ = rate_limiter.nonexistent
