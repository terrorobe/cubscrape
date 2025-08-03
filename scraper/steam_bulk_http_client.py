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

    def make_bulk_request(self, app_ids: list[str], country_code: str) -> dict[str, Any] | None:
        """Make a bulk price request to Steam API"""
        return self._make_steam_api_request(app_ids, country_code, filters="price_overview")

    def make_single_app_request(self, app_id: str, country_code: str = 'at') -> dict[str, Any] | None:
        """Make a single app request to Steam API (for full game data)"""
        return self._make_steam_api_request([app_id], country_code)

    def _make_steam_api_request(self, app_ids: list[str], country_code: str, filters: str | None = None) -> dict[str, Any] | None:
        """Make a request to Steam API with optional filters and retry logic"""
        # Build the request URL
        app_ids_str = ','.join(app_ids)
        url = f"https://store.steampowered.com/api/appdetails?appids={app_ids_str}&cc={country_code}"

        if filters:
            url += f"&filters={filters}"

        max_retries = 10

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
                    # Calculate exponential backoff delay starting at 10s
                    delay = 10 * (2 ** attempt)
                    logging.warning(f"Rate limited (429) on attempt {attempt + 1}/{max_retries}. Waiting {delay:.1f}s before retry...")

                    if attempt < max_retries - 1:  # Don't sleep on last attempt
                        time.sleep(delay)
                        continue
                    else:
                        # Last attempt failed, raise the error
                        response.raise_for_status()
                else:
                    # Other HTTP errors, raise immediately
                    response.raise_for_status()

            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    # Exponential backoff for network errors too starting at 10s
                    delay = 10 * (2 ** attempt)
                    logging.warning(f"Request failed on attempt {attempt + 1}/{max_retries}: {e}. Waiting {delay:.1f}s before retry...")
                    time.sleep(delay)
                    continue
                else:
                    # Last attempt, re-raise the exception
                    raise

        return None
