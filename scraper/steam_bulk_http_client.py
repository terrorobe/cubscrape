"""
Steam Bulk HTTP Client

Handles HTTP requests to Steam API with retry logic and rate limiting.
Separated from business logic for better maintainability.
"""

import logging
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
        self.last_request_time = 0.0

    def make_bulk_request(self, app_ids: list[str], country_code: str) -> dict[str, Any] | None:
        """Make a bulk price request to Steam API"""
        return self._make_steam_api_request(app_ids, country_code, filters="price_overview")

    def make_single_app_request(self, app_id: str, country_code: str = 'at') -> dict[str, Any] | None:
        """Make a single app request to Steam API (for full game data)"""
        return self._make_steam_api_request([app_id], country_code)

    def _make_steam_api_request(self, app_ids: list[str], country_code: str, filters: str | None = None) -> dict[str, Any] | None:
        """Make a request to Steam API with optional filters"""
        self._wait_for_rate_limit()

        # Build the request URL
        app_ids_str = ','.join(app_ids)
        url = f"https://store.steampowered.com/api/appdetails?appids={app_ids_str}&cc={country_code}"

        if filters:
            url += f"&filters={filters}"

        try:
            response = requests.get(
                url,
                headers=self.headers,
                cookies=self.cookies,
                timeout=HTTP_TIMEOUT_SECONDS
            )

            self.last_request_time = time.time()

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                logging.warning("Rate limited (HTTP 429) for Steam API request")
                return None
            elif response.status_code == 500:
                logging.warning("Server error (HTTP 500) for Steam API request")
                return None
            else:
                logging.warning(f"Unexpected HTTP {response.status_code} for Steam API request")
                return None

        except requests.RequestException as e:
            logging.error(f"Request exception in Steam API request: {e}")
            return None

    def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.config['rate_limit_delay']:
            wait_time = self.config['rate_limit_delay'] - elapsed
            logging.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            time.sleep(wait_time)
