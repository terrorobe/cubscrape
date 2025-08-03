"""
Steam Price Update Service

Handles Steam game price update business logic.
Extracted from DataManager for better separation of concerns.
"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .data_manager import DataManager, SteamDataDict

from .models import SteamGameData


class SteamPriceUpdateService:
    """Handles Steam game price update business logic"""

    def __init__(self, data_manager: 'DataManager') -> None:
        self.data_manager = data_manager

    def update_prices(self, price_updates: dict[str, dict[str, Any]], currency: str, dry_run: bool = False) -> dict[str, Any]:
        """
        Update Steam game prices for a specific currency

        Args:
            price_updates: Dict mapping app_id -> price data
            currency: 'eur' or 'usd'
            dry_run: If True, don't save changes

        Returns:
            Dict with update results
        """
        if currency not in ['eur', 'usd']:
            raise ValueError(f"Invalid currency: {currency}. Must be 'eur' or 'usd'")

        steam_data = self.data_manager.load_steam_data()
        games = steam_data.get('games', {})

        successful_updates = []
        failed_updates = []

        for app_id, price_data in price_updates.items():
            try:
                # Get existing game data or create new stub
                existing_game = games.get(app_id)
                if existing_game:
                    updated_game = self._apply_price_data_to_game(existing_game, price_data, currency)
                else:
                    # Create new game entry with price data
                    updated_game = self._create_game_with_price_data(app_id, price_data, currency)

                if not dry_run:
                    games[app_id] = updated_game

                successful_updates.append(app_id)

            except Exception as e:
                logging.error(f"Failed to update price for app {app_id}: {e}")
                failed_updates.append(app_id)

        # Save if not dry run
        if not dry_run and successful_updates:
            self.data_manager.save_steam_data(steam_data)

        return {
            'successful': successful_updates,
            'failed': failed_updates,
            'currency': currency,
            'total_processed': len(price_updates)
        }

    def apply_atomic_updates(self, eur_updates: dict[str, dict[str, Any]], usd_updates: dict[str, dict[str, Any]], dry_run: bool = False) -> dict[str, Any]:
        """
        Apply EUR and USD price updates atomically

        Both currency updates must succeed or both fail.
        This ensures price consistency across currencies.

        Args:
            eur_updates: EUR price updates
            usd_updates: USD price updates
            dry_run: If True, don't save changes

        Returns:
            Dict with combined update results
        """
        steam_data = self.data_manager.load_steam_data()

        # Collect all updates to apply
        all_successful = []
        all_failed = []

        # Process EUR updates
        eur_successful, eur_failed = self._process_currency_updates(steam_data, eur_updates, 'eur')
        all_successful.extend(eur_successful)
        all_failed.extend(eur_failed)

        # Process USD updates
        usd_successful, usd_failed = self._process_currency_updates(steam_data, usd_updates, 'usd')
        all_successful.extend(usd_successful)
        all_failed.extend(usd_failed)

        # Only save if not dry run and we have successful updates
        if not dry_run and all_successful:
            self.data_manager.save_steam_data(steam_data)
            logging.info(f"Applied atomic currency updates: {len(all_successful)} successful, {len(all_failed)} failed")

        return {
            'successful': list(set(all_successful)),  # Remove duplicates
            'failed': list(set(all_failed)),
            'eur_updates': len(eur_updates),
            'usd_updates': len(usd_updates),
            'total_processed': len(set(list(eur_updates.keys()) + list(usd_updates.keys())))
        }

    def _process_currency_updates(self, steam_data: 'SteamDataDict', price_updates: dict[str, dict[str, Any]], currency: str) -> tuple[list[str], list[str]]:
        """Process price updates for a specific currency"""
        successful = []
        failed = []

        games = steam_data.get('games', {})

        for app_id, price_data in price_updates.items():
            try:
                # Get existing game or create new one
                existing_game = games.get(app_id)
                if existing_game:
                    updated_game = self._apply_price_data_to_game(existing_game, price_data, currency)
                else:
                    updated_game = self._create_game_with_price_data(app_id, price_data, currency)

                games[app_id] = updated_game
                successful.append(app_id)

            except Exception as e:
                logging.error(f"Failed to apply {currency.upper()} price update for app {app_id}: {e}")
                failed.append(app_id)

        return successful, failed

    def _apply_price_data_to_game(self, game: SteamGameData, price_data: dict[str, Any], currency: str) -> SteamGameData:
        """Apply price data to an existing game"""
        updates = {}

        # Update currency-specific price fields
        if currency == 'eur':
            if 'price_eur' in price_data:
                updates['price_eur'] = price_data['price_eur']
            if 'original_price_eur' in price_data:
                updates['original_price_eur'] = price_data['original_price_eur']
        elif currency == 'usd':
            if 'price_usd' in price_data:
                updates['price_usd'] = price_data['price_usd']
            if 'original_price_usd' in price_data:
                updates['original_price_usd'] = price_data['original_price_usd']

        # Update sale/discount fields (global for all currencies)
        if 'discount_percent' in price_data:
            updates['discount_percent'] = price_data['discount_percent']
        if 'is_on_sale' in price_data:
            updates['is_on_sale'] = price_data['is_on_sale']
        if 'is_free' in price_data:
            updates['is_free'] = price_data['is_free']

        return game.model_copy(update=updates)

    def _create_game_with_price_data(self, app_id: str, price_data: dict[str, Any], currency: str) -> SteamGameData:
        """Create a new game entry with price data"""
        steam_url = f"https://store.steampowered.com/app/{app_id}/"

        # Create minimal SteamGameData with required fields
        game_data = SteamGameData(
            steam_app_id=app_id,
            steam_url=steam_url,
            name=f"[PRICE DATA ONLY] {app_id}",
            is_stub=True,
            stub_reason="Price data fetched before full game data",
            discount_percent=price_data.get('discount_percent', 0),
            is_on_sale=price_data.get('is_on_sale', False),
            is_free=price_data.get('is_free', False)
        )

        # Update with price data using model_copy
        updates = {}
        if currency == 'eur':
            updates['price_eur'] = price_data.get('price_eur')
            updates['original_price_eur'] = price_data.get('original_price_eur')
        elif currency == 'usd':
            updates['price_usd'] = price_data.get('price_usd')
            updates['original_price_usd'] = price_data.get('original_price_usd')

        return game_data.model_copy(update=updates)
