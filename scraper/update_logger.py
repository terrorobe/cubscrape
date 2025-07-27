"""
Game Update Logging Utility

Provides consolidated logging functionality for game updates across different platforms.
Used by both Steam and other platform updaters to ensure consistent log output.
"""

import logging
from datetime import datetime

from dateutil.parser import parse as dateutil_parse


class GameUpdateLogger:
    """Handles consistent logging for game updates across platforms"""

    @staticmethod
    def get_interval_name(interval_days: int) -> str:
        """Convert interval days to human-readable name"""
        interval_map = {
            0: "continuous",
            1: "daily",
            7: "weekly",
            30: "monthly"
        }
        return interval_map.get(interval_days, f"{interval_days}d")

    @staticmethod
    def calculate_days_since_update(last_updated_str: str | None) -> tuple[int | None, str]:
        """
        Calculate days since last update.

        Returns:
            (days_ago, update_info_str)
        """
        if not last_updated_str:
            return None, "never updated"

        try:
            last_updated_date = dateutil_parse(last_updated_str)
            days_ago = (datetime.now() - last_updated_date.replace(tzinfo=None)).days
            return days_ago, f"updated {days_ago} days ago"
        except (ValueError, TypeError):
            return None, "invalid last update"

    @staticmethod
    def log_game_skip(platform: str, game_name: str, last_updated_str: str | None,
                     refresh_interval_days: int, reason: str | None = None, release_info: str | None = None) -> None:
        """
        Log when a game is skipped during updates.

        Args:
            platform: Platform name (e.g., "steam", "itch", "crazygames")
            game_name: Name of the game
            last_updated_str: ISO timestamp string of last update
            refresh_interval_days: Refresh interval in days
            reason: Optional specific reason for skipping
            release_info: Optional release date information (for Steam games)
        """
        days_ago, update_info = GameUpdateLogger.calculate_days_since_update(last_updated_str)
        interval_name = GameUpdateLogger.get_interval_name(refresh_interval_days)

        # Build release info part (for Steam games)
        release_part = release_info if release_info else ""

        # Determine entity type based on platform
        entity_type = "app" if platform == "steam" else "game"

        if days_ago is not None:
            logging.debug(f"Skipping {platform} {entity_type} ({game_name}) - updated {days_ago} days ago, {interval_name} refresh{release_part}")
        else:
            skip_reason = reason or update_info
            logging.debug(f"Skipping {platform} {entity_type} ({game_name}) - {skip_reason}")

    @staticmethod
    def log_game_update_start(platform: str, game_name: str, last_updated_str: str | None,
                             refresh_interval_days: int, update_reason: str,
                             identifier: str | None = None, release_info: str | None = None) -> None:
        """
        Log when starting to update a game.

        Args:
            platform: Platform name (e.g., "steam", "itch", "crazygames")
            game_name: Name of the game
            last_updated_str: ISO timestamp string of last update
            refresh_interval_days: Refresh interval in days
            update_reason: Reason for the update
            identifier: Optional identifier (app_id for Steam, URL for others)
            release_info: Optional release date information
        """
        _, update_info = GameUpdateLogger.calculate_days_since_update(last_updated_str)
        interval_name = GameUpdateLogger.get_interval_name(refresh_interval_days)

        # Build identifier part
        id_part = f" {identifier}" if identifier else ""

        # Build release info part
        release_part = release_info if release_info else ""

        # Determine entity type based on platform
        entity_type = "app" if platform == "steam" else "game"

        # Steam includes app ID, others don't
        logging.info(f"Updating {platform} {entity_type}{id_part} ({game_name}) - {update_info}, {interval_name} refresh{release_part} ({update_reason})")

    @staticmethod
    def log_game_update_success(game_name: str, additional_info: str | None = None) -> None:
        """
        Log successful game update.

        Args:
            game_name: Name of the updated game
            additional_info: Optional additional information (e.g., "with Itch.io link")
        """
        if additional_info:
            logging.info(f"  Updated: {game_name} ({additional_info})")
        else:
            logging.info(f"  Updated: {game_name}")

    @staticmethod
    def log_game_update_failure(identifier: str, platform: str, error_msg: str | None = None) -> None:
        """
        Log failed game update.

        Args:
            identifier: Game identifier (app_id for Steam, URL for others)
            platform: Platform name
            error_msg: Optional specific error message
        """
        entity_type = "app" if platform == "steam" else "game"

        if error_msg:
            logging.error(f"  Error fetching {platform} data for {identifier}: {error_msg}")
        else:
            # Steam format: "app 123", other platforms: "game: url"
            separator = " " if platform == "steam" else ": "
            logging.warning(f"  Failed to fetch data for {platform} {entity_type}{separator}{identifier}")
