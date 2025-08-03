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

    def handle_server_error(self, current_batch_size: int, attempts: int) -> tuple[int, bool]:
        """
        Handle HTTP 500 errors by reducing batch size

        Returns:
            tuple: (new_batch_size, should_continue)
        """
        new_batch_size = int(current_batch_size * self.config['batch_size_reduction_factor'])
        # Ensure we never go below 1
        new_batch_size = max(new_batch_size, 1)

        # Always continue as long as we have retries left
        should_continue = True

        logging.warning(f"HTTP 500 error (attempt {attempts + 1}), reducing batch size: {current_batch_size} → {new_batch_size}")

        return new_batch_size, should_continue

    def handle_rate_limit(self, rate_limit_attempts: int) -> tuple[bool, float]:
        """
        Handle HTTP 429 rate limiting with exponential backoff

        Returns:
            tuple: (should_retry, delay_seconds)
        """
        should_retry = self._should_retry_rate_limit(rate_limit_attempts)

        if should_retry:
            delay = self.config['rate_limit_delay'] * (2 ** rate_limit_attempts)
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

    def should_retry_general_error(self, error: Exception, attempts: int) -> bool:
        """Check if we should retry after a general exception"""
        should_retry = attempts < self.config['max_retries'] - 1

        if should_retry:
            logging.warning(f"General error (attempt {attempts + 1}): {error}")
        else:
            logging.error(f"General error exceeded max retries: {error}")

        return should_retry

    def handle_standard_retry(self, status_code: int, attempts: int, request_type: str = "API") -> tuple[bool, float]:
        """
        Handle standard retry logic for non-429/non-500 errors

        Returns:
            tuple: (should_retry, delay_seconds)
        """
        should_retry = attempts < self.config['max_retries'] - 1

        if should_retry:
            delay = self.config['rate_limit_delay'] * (2 ** attempts)
            logging.warning(f"HTTP {status_code} for {request_type} request (attempt {attempts + 1}), retrying in {delay}s")
            return True, delay
        else:
            logging.error(f"Failed {request_type} request after {self.config['max_retries']} attempts: HTTP {status_code}")
            return False, 0.0

    def handle_request_exception(self, error: Exception, attempts: int, request_type: str = "API") -> tuple[bool, float]:
        """
        Handle request exceptions with retry logic

        Returns:
            tuple: (should_retry, delay_seconds)
        """
        should_retry = attempts < self.config['max_retries'] - 1

        if should_retry:
            delay = self.config['rate_limit_delay'] * (2 ** attempts)
            logging.warning(f"Network error for {request_type} request (attempt {attempts + 1}): {error}, retrying in {delay}s")
            return True, delay
        else:
            logging.error(f"Network error for {request_type} request after {self.config['max_retries']} attempts: {error}")
            return False, 0.0

    def _should_retry_rate_limit(self, rate_limit_attempts: int) -> bool:
        """Check if we should retry after rate limiting"""
        return rate_limit_attempts < self.config['max_retries'] - 1
