"""Rate limiting utilities for VK API calls."""

import asyncio
import time
from collections import deque
from typing import TYPE_CHECKING, Any

from .logging_config import get_logger

logger = get_logger("utils.rate_limiter")

if TYPE_CHECKING:
    from vk_api.vk_api import VkApiMethod


class RateLimitedVKAPI:
    """
    Rate-limited wrapper for VK API calls.

    This class provides rate limiting functionality for VK API calls to prevent
    hitting API rate limits. It uses a sliding window approach to track API calls
    and ensures that the specified requests per second limit is not exceeded.
    """

    def __init__(self, vk_api: "VkApiMethod", requests_per_second: int = 3) -> None:
        """
        Initialize RateLimitedVKAPI with VK API instance and rate limit.

        Args:
            vk_api: The VK API instance to wrap with rate limiting
            requests_per_second: Maximum number of requests allowed per second (default: 3)
        """
        self._vk_api = vk_api
        self._requests_per_second = requests_per_second
        self._request_times: deque[float] = deque()
        self._lock = asyncio.Lock()

        logger.info(
            f"Initialized rate limiter with {requests_per_second} requests per second"
        )

    async def _wait_if_needed(self) -> None:
        """
        Wait if necessary to respect the rate limit.

        Implements a sliding window using a lock to guard shared state. If the
        limit is reached, releases the lock before sleeping to avoid deadlocks,
        then rechecks the window.
        """
        while True:
            wait_time: float | None = None
            async with self._lock:
                current_time = time.time()

                # Remove requests older than 1 second
                while (
                    self._request_times and current_time - self._request_times[0] >= 1.0
                ):
                    self._request_times.popleft()

                # If we've made too many requests in the last second, compute wait with a safety margin
                if len(self._request_times) >= self._requests_per_second:
                    wait_time = 1.0 - (current_time - self._request_times[0]) + 0.5
                else:
                    # Record this request and return immediately
                    self._request_times.append(current_time)
                    return

            # Sleep outside the lock
            if wait_time is not None and wait_time > 0:
                logger.debug(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
            else:
                # No need to wait further
                return

    def _make_api_call(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Make a rate-limited API call to the VK API.

        Args:
            method_name: Name of the VK API method to call
            *args: Positional arguments for the API method
            **kwargs: Keyword arguments for the API method

        Returns:
            The result of the VK API call

        Raises:
            Exception: Any exception raised by the VK API call
        """
        # Resolve possibly dotted method names like "users.get"
        target = self._vk_api
        for part in method_name.split("."):
            target = getattr(target, part)

        # Make the actual API call
        logger.debug(f"Making VK API call: {method_name}")
        return target(*args, **kwargs)

    async def call(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Make a rate-limited API call.

        Args:
            method_name: Name of the VK API method to call
            *args: Positional arguments for the API method
            **kwargs: Keyword arguments for the API method

        Returns:
            The result of the VK API call

        Raises:
            Exception: Any exception raised by the VK API call
        """
        await self._wait_if_needed()
        return self._make_api_call(method_name, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        """
        Delegate attribute access to the underlying VK API instance.

        This allows the RateLimitedVKAPI to be used as a drop-in replacement
        for the original VK API instance, with rate limiting applied to method calls.

        Args:
            name: Attribute name to access

        Returns:
            The attribute from the underlying VK API instance
        """
        # Only delegate if attribute is explicitly present on the underlying object
        # This avoids MagicMock auto-creating attributes that mask missing names in tests
        underlying_dict = getattr(self._vk_api, "__dict__", {})
        if isinstance(underlying_dict, dict) and name in underlying_dict:
            attr = underlying_dict[name]
        else:
            # As a fallback, try normal getattr and ensure the attribute truly exists
            try:
                attr = object.__getattribute__(self._vk_api, name)  # may raise
            except Exception as exc:
                raise AttributeError(
                    f"'{self.__class__.__name__}' object has no attribute '{name}'"
                ) from exc

        # If it's a method, wrap it with rate limiting
        if callable(attr):

            async def rate_limited_method(*args: Any, **kwargs: Any) -> Any:
                return await self.call(name, *args, **kwargs)

            return rate_limited_method

        # If it's not a method, return it as-is
        return attr

    @property
    def requests_per_second(self) -> int:
        """
        Get the current rate limit setting.

        Returns:
            Maximum requests per second allowed
        """
        return self._requests_per_second

    @requests_per_second.setter
    def requests_per_second(self, value: int) -> None:
        """
        Set the rate limit.

        Args:
            value: New maximum requests per second
        """
        if value <= 0:
            raise ValueError("Requests per second must be positive")

        self._requests_per_second = value
        logger.info(f"Updated rate limit to {value} requests per second")

    def get_stats(self) -> dict[str, Any]:
        """
        Get current rate limiting statistics.

        Returns:
            Dictionary containing rate limiting statistics
        """
        current_time = time.time()

        # Clean up old requests
        while self._request_times and current_time - self._request_times[0] >= 1.0:
            self._request_times.popleft()

        return {
            "requests_per_second": self._requests_per_second,
            "current_requests_in_window": len(self._request_times),
            "requests_remaining": max(
                0, self._requests_per_second - len(self._request_times)
            ),
        }
