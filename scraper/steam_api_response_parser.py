"""
Steam API Response Parser

Parses Steam API responses into standardized format.
Separated from HTTP and business logic for better maintainability.
"""

import logging
from typing import Any


class SteamApiResponseParser:
    """Parses Steam API responses into standardized format"""

    def parse_bulk_response(self, response: dict[str, Any], app_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Parse Steam bulk API response into standardized format"""
        results = {}

        for app_id in app_ids:
            app_data = response.get(app_id, {})

            if not app_data.get('success', False):
                logging.debug(f"Steam API returned success=false for app {app_id}")
                continue

            parsed_data = self._parse_single_app_response(app_data.get('data', {}), app_id)
            if parsed_data:
                results[app_id] = parsed_data

        return results

    def _parse_single_app_response(self, app_data: dict[str, Any], app_id: str) -> dict[str, Any] | None:
        """Parse individual app response from Steam API"""
        if not app_data:
            logging.debug(f"No data section for app {app_id}")
            return None

        price_overview = app_data.get('price_overview')
        if not price_overview:
            # Free game or no price data
            return {
                'is_free': True,
                'price_eur': None,
                'price_usd': None,
                'discount_percent': 0,
                'original_price_eur': None,
                'original_price_usd': None,
                'is_on_sale': False
            }

        # Extract price information
        currency = price_overview.get('currency', 'EUR')
        final_price = price_overview.get('final', 0)  # Price in cents
        initial_price = price_overview.get('initial', final_price)  # Original price in cents
        discount_percent = price_overview.get('discount_percent', 0)

        # Convert cents to currency string format
        price_str = self._format_price(final_price, currency)
        original_price_str = self._format_price(initial_price, currency) if initial_price != final_price else None

        # Determine which currency this is
        is_eur = currency == 'EUR'
        is_usd = currency == 'USD'

        result = {
            'is_free': final_price == 0,
            'discount_percent': discount_percent,
            'is_on_sale': discount_percent > 0
        }

        # Set currency-specific fields
        if is_eur:
            result['price_eur'] = price_str
            result['original_price_eur'] = original_price_str
            result['price_usd'] = None
            result['original_price_usd'] = None
        elif is_usd:
            result['price_usd'] = price_str
            result['original_price_usd'] = original_price_str
            result['price_eur'] = None
            result['original_price_eur'] = None
        else:
            # Unknown currency, skip
            logging.warning(f"Unknown currency {currency} for app {app_id}")
            return None

        return result

    def _format_price(self, price_cents: int, currency: str) -> str:
        """Format price from cents to currency string"""
        if price_cents == 0:
            return "Free"

        # Convert cents to major currency unit
        price_major = price_cents / 100.0

        if currency == 'EUR':
            return f"€{price_major:.2f}"
        elif currency == 'USD':
            return f"${price_major:.2f}"
        else:
            return f"{price_major:.2f} {currency}"
