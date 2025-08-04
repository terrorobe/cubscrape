"""
Steam API Response Parser

Parses Steam API responses into standardized format.
Separated from HTTP and business logic for better maintainability.
"""

import logging
from typing import Any


class SteamApiResponseParser:
    """Parses Steam API responses into standardized format"""

    def parse_bulk_response(self, response: dict[str, Any], app_ids: list[str], existing_games: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
        """Parse Steam bulk API response into standardized format"""
        results, _ = self.parse_bulk_response_with_removal_info(response, app_ids, existing_games)
        return results

    def parse_bulk_response_with_removal_info(self, response: dict[str, Any], app_ids: list[str], existing_games: dict[str, Any] | None = None) -> tuple[dict[str, dict[str, Any]], list[str]]:
        """
        Parse bulk Steam API response and return both successful results and removed games

        Args:
            response: Raw Steam API response
            app_ids: List of app IDs that were requested
            existing_games: Optional dict of existing game data for comparison

        Returns:
            Tuple of (successful_results, removed_app_ids)
            - successful_results: Dict of games that exist on Steam {app_id: parsed_data}
            - removed_app_ids: List of app IDs where Steam returned success=false
        """
        results = {}
        removed_games = []
        existing_games = existing_games or {}

        for app_id in app_ids:
            app_data = response.get(app_id, {})

            if not app_data.get('success', False):
                # Steam explicitly said this game doesn't exist
                removed_games.append(app_id)
                logging.debug(f"Steam API returned success=false for app {app_id}")
                continue

            existing_game = existing_games.get(app_id)
            parsed_data = self._parse_single_app_response(app_data.get('data', {}), app_id, existing_game)
            if parsed_data:
                results[app_id] = parsed_data

        return results, removed_games

    def _parse_single_app_response(self, app_data: dict[str, Any], app_id: str, existing_game: Any = None) -> dict[str, Any] | None:
        """Parse individual app response from Steam API"""
        # Handle empty data array (Steam returns [] for free/demo/unreleased games)
        if not app_data or isinstance(app_data, list):
            # Check if this game had pricing before but now doesn't (price disappeared)
            if existing_game and (getattr(existing_game, 'price_eur', None) or getattr(existing_game, 'price_usd', None)):
                logging.info(f"App {app_id} had pricing before but now has empty response - flagging for full refresh")
                return {
                    'needs_full_refresh': True,
                    'price_eur': None,
                    'price_usd': None,
                    'original_price_eur': None,
                    'original_price_usd': None,
                    'is_on_sale': False
                }
            else:
                # No existing price data, probably unreleased - skip
                logging.debug(f"No data or empty data array for app {app_id} - skipping (no existing price data)")
                return None

        price_overview = app_data.get('price_overview')
        if not price_overview:
            # Check if this game had pricing before but now doesn't (price disappeared)
            if existing_game and (getattr(existing_game, 'price_eur', None) or getattr(existing_game, 'price_usd', None)):
                logging.info(f"App {app_id} had pricing before but now has no price_overview - flagging for full refresh")
                return {
                    'needs_full_refresh': True,
                    'price_eur': None,
                    'price_usd': None,
                    'original_price_eur': None,
                    'original_price_usd': None,
                    'is_on_sale': False
                }
            else:
                # No existing price data and no price_overview - skip
                logging.debug(f"No price_overview for app {app_id} - skipping (no existing price data)")
                return None

        # Extract price information
        currency = price_overview.get('currency', 'EUR')
        final_price_cents = price_overview.get('final', 0)  # Price in cents
        initial_price_cents = price_overview.get('initial', final_price_cents)  # Original price in cents
        discount_percent = price_overview.get('discount_percent', 0)

        # Check if this game didn't have pricing before but now does (price appeared)
        needs_full_refresh = False
        if (existing_game and
            not (getattr(existing_game, 'price_eur', None) or getattr(existing_game, 'price_usd', None)) and
            final_price_cents > 0):  # New pricing appeared
            logging.info(f"App {app_id} didn't have pricing before but now has price data - flagging for full refresh")
            needs_full_refresh = True

        # Determine which currency this is
        is_eur = currency == 'EUR'
        is_usd = currency == 'USD'

        result = {
            'is_free': final_price_cents == 0,
            'is_on_sale': discount_percent > 0
        }

        if needs_full_refresh:
            result['needs_full_refresh'] = True

        # Only set discount_percent if it's non-zero
        if discount_percent > 0:
            result['discount_percent'] = discount_percent

        # Set currency-specific fields (storing cents directly)
        if is_eur:
            result['price_eur'] = final_price_cents if final_price_cents > 0 else None
            result['original_price_eur'] = initial_price_cents if initial_price_cents != final_price_cents and initial_price_cents > 0 else None
            result['price_usd'] = None
            result['original_price_usd'] = None
        elif is_usd:
            result['price_usd'] = final_price_cents if final_price_cents > 0 else None
            result['original_price_usd'] = initial_price_cents if initial_price_cents != final_price_cents and initial_price_cents > 0 else None
            result['price_eur'] = None
            result['original_price_eur'] = None
        else:
            # Unknown currency, skip
            logging.warning(f"Unknown currency {currency} for app {app_id}")
            return None

        return result

