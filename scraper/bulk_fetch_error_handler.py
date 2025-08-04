"""
Bulk Fetch Error Handler

Handles different error types with appropriate strategies.
Separated from HTTP and business logic for better maintainability.
"""

import contextlib
import logging
from typing import Any

import requests


class BulkFetchErrorHandler:
    """Handles different error types with appropriate strategies"""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def should_retry_empty_response(self, attempts: int) -> bool:
        """Check if we should retry after empty API response"""
        return attempts < self.config['max_retries'] - 1

    def handle_server_error(self, current_batch_size: int, attempts: int) -> tuple[int, bool, float]:
        """
        Handle HTTP 500 errors by reducing batch size with short delays

        Server errors typically indicate overload, so we use aggressive batch reduction
        and short delays to recover quickly.

        Returns:
            tuple: (new_batch_size, should_continue, delay_seconds)
        """
        # Aggressive batch reduction for server errors
        reduction_factor = self.config['server_error_batch_reduction']
        new_batch_size = int(current_batch_size * reduction_factor)
        # Ensure we never go below 1
        new_batch_size = max(new_batch_size, 1)

        # Short delays for server errors - they often recover quickly
        max_delay = self.config['server_error_max_delay']
        delay = min(2 * (attempts + 1), max_delay)

        # Continue as long as we have retries left
        should_continue = True

        logging.warning(f"HTTP 500 error (attempt {attempts + 1}), reducing batch size: {current_batch_size} → {new_batch_size}, waiting {delay}s")

        return new_batch_size, should_continue, delay

    def handle_rate_limit(self, rate_limit_attempts: int) -> tuple[bool, float]:
        """
        Handle HTTP 429 rate limiting with exponential backoff and caps

        Rate limits require respectful exponential backoff but with reasonable caps.

        Returns:
            tuple: (should_retry, delay_seconds)
        """
        should_retry = self._should_retry_rate_limit(rate_limit_attempts)

        if should_retry:
            base_delay = self.config['rate_limit_delay']
            max_delay = self.config['rate_limit_max_delay']
            delay = min(base_delay * (2 ** rate_limit_attempts), max_delay)
            logging.warning(f"Rate limited (attempt {rate_limit_attempts + 1}), waiting {delay}s")
            return True, delay
        else:
            logging.error(f"Rate limit exceeded after {rate_limit_attempts + 1} attempts")
            return False, 0.0

    def handle_unexpected_http_error(self, status_code: int, error_response: requests.Response | None = None) -> bool:
        """
        Handle unexpected HTTP errors (not 500 or 429)

        Returns:
            bool: should_retry (always False for unexpected errors)
        """
        error_text = ""
        if error_response:
            with contextlib.suppress(Exception):
                error_text = f" - {error_response.text[:200]}"

        logging.error(f"Unexpected HTTP {status_code} error{error_text}")
        return False  # Don't retry unexpected HTTP errors

    def should_retry_general_error(self, error: Exception, attempts: int) -> tuple[bool, float]:
        """Check if we should retry after a general exception with network error handling"""
        return self.handle_network_error(error, attempts)

    def handle_standard_retry(self, status_code: int, attempts: int, request_type: str = "API") -> tuple[bool, float]:
        """
        Handle standard retry logic for non-429/non-500 errors using network error strategy

        Returns:
            tuple: (should_retry, delay_seconds)
        """
        should_retry = attempts < self.config['max_retries'] - 1

        if should_retry:
            base_delay = self.config['network_error_base_delay']
            increment = self.config['network_error_delay_increment']
            max_delay = self.config['network_error_max_delay']
            delay = min(base_delay + (attempts * increment), max_delay)

            logging.warning(f"HTTP {status_code} for {request_type} request (attempt {attempts + 1}), retrying in {delay}s")
            return True, delay
        else:
            logging.error(f"Failed {request_type} request after {self.config['max_retries']} attempts: HTTP {status_code}")
            return False, 0.0

    def handle_network_error(self, error: Exception, attempts: int) -> tuple[bool, float]:
        """
        Handle network errors (connection issues, timeouts) with linear backoff

        Network errors often resolve quickly, so we use linear rather than exponential delays.

        Returns:
            tuple: (should_retry, delay_seconds)
        """
        should_retry = attempts < self.config['max_retries'] - 1

        if should_retry:
            # Linear increase for network issues instead of exponential
            base_delay = self.config['network_error_base_delay']
            increment = self.config['network_error_delay_increment']
            max_delay = self.config['network_error_max_delay']
            delay = min(base_delay + (attempts * increment), max_delay)

            logging.warning(f"Network error (attempt {attempts + 1}): {error}, retrying in {delay}s")
            return True, delay
        else:
            logging.error(f"Network error after {self.config['max_retries']} attempts: {error}")
            return False, 0.0

    def handle_request_exception(self, error: Exception, attempts: int, request_type: str = "API") -> tuple[bool, float]:
        """
        Handle request exceptions with retry logic - delegates to network error handler

        Returns:
            tuple: (should_retry, delay_seconds)
        """
        should_retry = attempts < self.config['max_retries'] - 1

        if should_retry:
            # Use network error strategy but with request type context
            base_delay = self.config['network_error_base_delay']
            increment = self.config['network_error_delay_increment']
            max_delay = self.config['network_error_max_delay']
            delay = min(base_delay + (attempts * increment), max_delay)

            logging.warning(f"{request_type} request exception (attempt {attempts + 1}): {error}, retrying in {delay}s")
            return True, delay
        else:
            logging.error(f"{request_type} request exception after {self.config['max_retries']} attempts: {error}")
            return False, 0.0

    def _should_retry_rate_limit(self, rate_limit_attempts: int) -> bool:
        """Check if we should retry after rate limiting"""
        return rate_limit_attempts < self.config['max_retries'] - 1
