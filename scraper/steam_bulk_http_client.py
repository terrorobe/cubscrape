"""
Steam Bulk HTTP Client

Handles HTTP requests to Steam API with retry logic and rate limiting.
Separated from business logic for better maintainability.
"""

import time
from typing import Any

import requests

from .constants import HTTP_TIMEOUT_SECONDS, USER_AGENT


class SteamBulkHttpClient:
    """Handles HTTP requests to Steam API with retry logic"""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.headers = {
            'User-Agent': USER_AGENT
        }
        self.cookies = {'birthtime': '0', 'mature_content': '1'}

    def make_bulk_request(self, app_ids: list[str], country_code: str) -> dict[str, Any] | None:
        """Make a bulk price request to Steam API"""
        return self._make_steam_api_request(app_ids, country_code, filters="price_overview")

    def make_single_app_request(self, app_id: str, country_code: str = 'at') -> dict[str, Any] | None:
        """Make a single app request to Steam API (for full game data)"""
        return self._make_steam_api_request([app_id], country_code)

    def _make_steam_api_request(self, app_ids: list[str], country_code: str, filters: str | None = None) -> dict[str, Any] | None:
        """Make a request to Steam API with comprehensive retry logic

        Handles all retryable errors at the HTTP layer including:
        - 429 rate limiting with exponential backoff
        - 500/502/503 server errors with linear backoff
        - Network errors (timeouts, connection issues)

        This centralizes all retry logic in the HTTP layer to maintain proper separation of concerns.
        """
        # Import error handler here to avoid circular dependencies
        from .bulk_fetch_error_handler import BulkFetchErrorHandler
        error_handler = BulkFetchErrorHandler(self.config)

        # Build the request URL
        app_ids_str = ','.join(app_ids)
        url = f"https://store.steampowered.com/api/appdetails?appids={app_ids_str}&cc={country_code}"

        if filters:
            url += f"&filters={filters}"

        max_retries = int(self.config.get('max_retries', 5))

        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    cookies=self.cookies,
                    timeout=HTTP_TIMEOUT_SECONDS
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limited
                    should_retry, delay = error_handler.handle_rate_limit(attempt)
                    if should_retry:
                        time.sleep(delay)
                        continue
                    else:
                        response.raise_for_status()  # Final failure
                elif response.status_code in [500, 502, 503]:  # Server errors
                    # Server overload - bubble up immediately for batch size reduction
                    response.raise_for_status()
                else:
                    # Other HTTP errors, don't retry
                    response.raise_for_status()

            except requests.exceptions.HTTPError:
                # HTTP errors that couldn't be retried, re-raise to business logic
                raise
            except requests.RequestException as e:
                should_retry, delay = error_handler.handle_network_error(e, attempt)
                if should_retry:
                    time.sleep(delay)
                    continue
                else:
                    # Final network error, re-raise
                    raise

        return None
