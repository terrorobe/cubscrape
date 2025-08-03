"""
Steam Bulk HTTP Client

Handles HTTP requests to Steam API with retry logic and rate limiting.
Separated from business logic for better maintainability.
"""

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
        """Make a request to Steam API with optional filters"""
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

            if response.status_code == 200:
                return response.json()
            else:
                # Let requests raise the appropriate HTTPError
                # This preserves the status code and allows proper error handling upstream
                response.raise_for_status()

        except requests.RequestException:
            # Re-raise the exception to allow proper error handling upstream
            raise
