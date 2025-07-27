"""
Other Games Data Updater - Orchestrates other platform game updates across multiple channels

Handles updating other platform games (Itch.io, CrazyGames) data using batch processing
similar to the Steam updater approach.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dateutil.parser import parse as dateutil_parse

from .config_manager import ConfigManager
from .crazygames_fetcher import CrazyGamesDataFetcher
from .data_manager import DataManager, SteamDataDict
from .itch_fetcher import ItchDataFetcher
from .models import OtherGameData
from .unified_data_collector import UnifiedDataCollector
from .update_logger import GameUpdateLogger

if TYPE_CHECKING:
    from .scraper import YouTubeSteamScraper


class OtherGamesUpdater:
    """
    Orchestrates other platform game data updates by:
    1. Collecting URLs from multiple channel video files
    2. Managing the other_games.json file
    3. Applying age-based refresh intervals (max monthly)
    4. Using platform-specific fetchers for individual game fetching
    """

    def __init__(self) -> None:
        # Get project root
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent

        self.data_manager = DataManager(project_root)
        self.config_manager = ConfigManager(project_root)
        self.other_games_data = self.data_manager.load_other_games_data()
        self.itch_fetcher = ItchDataFetcher(self.data_manager)
        self.crazygames_fetcher = CrazyGamesDataFetcher()
        self.data_collector = UnifiedDataCollector(self.data_manager)

        # Deferred save support
        self.has_pending_updates = False
        self.pending_update_count = 0

        # Check for required Itch.io authentication
        self._validate_itch_authentication()

    def _validate_itch_authentication(self) -> None:
        """Validate that Itch.io authentication is properly configured"""
        import os

        # Check if ITCH_COOKIES is set in environment
        itch_cookies = os.getenv('ITCH_COOKIES')
        if not itch_cookies:
            raise RuntimeError(
                "ITCH_COOKIES environment variable is not set. "
                "Itch.io authentication is required for accurate data extraction. "
                "Please configure the .env file with your Itch.io authentication cookies."
            )

        # Check if the fetcher has cookies in headers
        if 'Cookie' not in self.itch_fetcher.headers:
            raise RuntimeError(
                "Itch.io authentication cookies not found in fetcher headers. "
                "Please ensure the .env file is properly configured with ITCH_COOKIES."
            )

        logging.info("Itch.io authentication validated successfully")

    def _save_other_games_data(self, force: bool = False, pending_steam_data: 'SteamDataDict | None' = None) -> None:
        """Save other games data to file"""
        if self.has_pending_updates and not force:
            logging.debug("Deferring other games save until Steam updates complete")
            return

        self.data_manager.save_other_games_data(self.other_games_data, pending_steam_data)
        self.has_pending_updates = False
        self.pending_update_count = 0

    def enable_deferred_save(self) -> None:
        """Enable deferred save mode - updates will be accumulated but not saved until save_pending_updates() is called"""
        self.has_pending_updates = True
        logging.debug("Enabled deferred save mode for other games updates")

    def save_pending_updates(self, pending_steam_data: 'SteamDataDict | None' = None) -> None:
        """Save any pending updates that were deferred"""
        if self.has_pending_updates and self.pending_update_count > 0:
            self._save_other_games_data(force=True, pending_steam_data=pending_steam_data)
            logging.info(f"Saved {self.pending_update_count} pending other games updates")
        elif self.has_pending_updates:
            logging.debug("No pending other games updates to save")
            self.has_pending_updates = False

    def discard_pending_updates(self) -> None:
        """Discard any pending updates and reload from disk"""
        if self.has_pending_updates:
            self.other_games_data = self.data_manager.load_other_games_data()
            self.has_pending_updates = False
            self.pending_update_count = 0
            logging.info("Discarded pending other games updates and reloaded from disk")

    def _get_release_date_info(self, game_data: OtherGameData) -> str:
        """Get formatted release date information for logging"""
        if game_data.release_date:
            return f", released {game_data.release_date}"
        else:
            return ""


    def _calculate_refresh_interval(self, game_data: OtherGameData) -> int:
        """
        Calculate refresh interval based on game data.
        More conservative than Steam since other platforms change less frequently.

        Returns interval in days:
        - Stub entries: 30 days (monthly) to avoid frequent retries
        - New games (< 30 days): 7 days (weekly)
        - All other games: 30 days (monthly) - max as requested
        """
        # For stub entries, use monthly refresh interval to avoid frequent retries
        if game_data.is_stub:
            return 30

        release_date_str = game_data.release_date or ''

        if not release_date_str:
            return 30  # Monthly for games without release dates

        try:
            # Try to parse the release date
            release_date = dateutil_parse(release_date_str, fuzzy=True)
            days_since_release = (datetime.now() - release_date.replace(tzinfo=None)).days

            if days_since_release < 30:
                return 7  # Weekly for very new games
            else:
                return 30  # Monthly for everything else (max interval)

        except (ValueError, TypeError):
            # If we can't parse the date, default to monthly
            return 30

    def _should_update_game(self, _url: str, game_data: OtherGameData) -> tuple[bool, str]:
        """
        Determine if a game should be updated based on age-based intervals.

        Returns (should_update, reason)
        """
        last_updated_str = game_data.last_updated

        if not last_updated_str:
            return True, "never updated"

        # Missing release date is reason for immediate refresh (except for stubs)
        if not game_data.release_date and not game_data.is_stub:
            return True, "missing release date"

        try:
            last_updated = dateutil_parse(last_updated_str)
            days_since_update = (datetime.now() - last_updated.replace(tzinfo=None)).days
            required_interval = self._calculate_refresh_interval(game_data)

            if days_since_update >= required_interval:
                interval_name = GameUpdateLogger.get_interval_name(required_interval)
                return True, f"{interval_name} refresh due ({days_since_update}d old)"
            else:
                return False, f"recently updated ({days_since_update}d ago)"

        except (ValueError, TypeError):
            return True, "invalid last_updated date"

    def _collect_urls_from_unified_data(self, all_videos_data: dict[str, Any]) -> dict[str, set[str]]:
        """
        Collect all Itch.io and CrazyGames URLs from unified video data.

        Args:
            all_videos_data: Unified video data from UnifiedDataCollector (guaranteed Pydantic models)

        Returns dict with 'itch' and 'crazygames' keys containing sets of URLs.
        """
        urls: dict[str, set[str]] = {'itch': set(), 'crazygames': set()}

        total_videos = 0
        for channel_data in all_videos_data.values():
            videos = channel_data.get('videos', {})
            total_videos += len(videos)

            # All video data is guaranteed to be VideoData objects by UnifiedDataCollector
            for video_data in videos.values():
                for game_ref in video_data.game_references:
                    # Clean, type-safe access - no runtime type checking needed
                    if game_ref.platform == 'itch' and game_ref.platform_id:
                        urls['itch'].add(game_ref.platform_id)
                    elif game_ref.platform == 'crazygames' and game_ref.platform_id:
                        urls['crazygames'].add(game_ref.platform_id)

        logging.info(f"Collected {len(urls['itch'])} Itch.io URLs and {len(urls['crazygames'])} CrazyGames URLs from {total_videos} videos")
        return urls

    def _fetch_game_data(self, url: str, platform: str) -> OtherGameData | None:
        """Fetch game data for the specified platform and URL"""
        try:
            if platform == 'itch':
                return self.itch_fetcher.fetch_data(url)
            elif platform == 'crazygames':
                return self.crazygames_fetcher.fetch_data(url)
            else:
                logging.error(f"Unknown platform: {platform}")
                return None
        except Exception as e:
            logging.error(f"Error fetching {platform} game {url}: {e}")
            return None

    def update_games_from_channels(self, channel_ids: list[str], max_updates: int | None = None,
                                   pending_scrapers: list['YouTubeSteamScraper'] | None = None) -> int:
        """
        Update other platform games referenced in the specified channels.

        Args:
            channel_ids: List of channel IDs to process
            max_updates: Maximum number of games to update (None for no limit)
            pending_scrapers: List of scrapers with in-memory video data to include

        Returns:
            Number of games successfully updated
        """
        if not channel_ids:
            logging.warning("No channels provided for other games update")
            return 0

        # Collect all URLs from unified data source (both saved and pending)
        all_videos_data = self.data_collector.collect_all_videos_data(channel_ids, pending_scrapers)
        collected_urls = self._collect_urls_from_unified_data(all_videos_data)
        all_urls = set()
        all_urls.update(collected_urls['itch'])
        all_urls.update(collected_urls['crazygames'])

        if not all_urls:
            logging.info("No other platform game URLs found in specified channels")
            return 0

        # Determine which games need updates
        games_to_update = []

        for url in all_urls:
            existing_game = self.other_games_data.get('games', {}).get(url)

            if not existing_game:
                # Determine platform from URL
                if 'itch.io' in url:
                    platform = 'itch'
                elif 'crazygames.com' in url:
                    platform = 'crazygames'
                else:
                    logging.warning(f"Unknown platform for URL: {url}")
                    continue

                games_to_update.append((url, platform, "new game"))
            else:
                should_update, reason = self._should_update_game(url, existing_game)
                if should_update:
                    platform = existing_game.platform
                    games_to_update.append((url, platform, reason))
                else:
                    # Log skip info with detailed reason
                    platform = existing_game.platform
                    game_name = existing_game.name or "Unknown"
                    refresh_interval_days = self._calculate_refresh_interval(existing_game)
                    release_date_info = self._get_release_date_info(existing_game)

                    GameUpdateLogger.log_game_skip(platform, game_name, existing_game.last_updated,
                                                 refresh_interval_days, reason, release_date_info)

        if not games_to_update:
            logging.info("No other platform games need updates")
            return 0

        # Sort by reason to prioritize new games, then by URL for consistency
        games_to_update.sort(key=lambda x: (x[2] != "new game", x[0]))

        # Apply max_updates limit
        if max_updates:
            games_to_update = games_to_update[:max_updates]

        logging.info(f"Updating {len(games_to_update)} other platform games...")

        updated_count = 0

        for url, platform, reason in games_to_update:
            # Log update info including name and last update if known
            existing_game = self.other_games_data.get('games', {}).get(url)
            if existing_game and existing_game.name:
                refresh_interval_days = self._calculate_refresh_interval(existing_game)
                release_date_info = self._get_release_date_info(existing_game)
                GameUpdateLogger.log_game_update_start(platform, existing_game.name, existing_game.last_updated,
                                                     refresh_interval_days, reason, release_info=release_date_info)
            else:
                logging.info(f"Updating {platform} game: {url} ({reason})")

            game_data = self._fetch_game_data(url, platform)
            if game_data:
                # Update timestamp and store object directly
                game_data.last_updated = datetime.now().isoformat()

                # Ensure games dict exists
                if 'games' not in self.other_games_data:
                    self.other_games_data['games'] = {}

                self.other_games_data['games'][url] = game_data
                updated_count += 1

                # Track pending updates for deferred save
                if self.has_pending_updates:
                    self.pending_update_count += 1

                GameUpdateLogger.log_game_update_success(game_data.name)
            else:
                GameUpdateLogger.log_game_update_failure(url, platform)

        # Save data if any updates were made
        if updated_count > 0:
            self._save_other_games_data()
            if self.has_pending_updates:
                logging.info(f"Other games update completed. Updated {updated_count}/{len(games_to_update)} games (deferred save)")
            else:
                logging.info(f"Other games update completed. Updated {updated_count}/{len(games_to_update)} games")
        else:
            logging.info("No other platform games were successfully updated")

        return updated_count

    def update_all_other_games(self, force_update: bool = False) -> int:
        """
        Update all existing other games data by re-fetching from their URLs.
        This is the simpler method used by the refresh-other CLI command.

        Args:
            force_update: If True, update all games regardless of refresh intervals
        """
        games = self.other_games_data.get('games', {})
        if not games:
            logging.info("No other platform games to update")
            return 0

        updated_count = 0
        total_games = len(games)

        logging.info(f"Updating {total_games} existing other platform games...")

        for url, game_data in games.items():
            platform = game_data.platform
            game_name = game_data.name or "Unknown"

            if force_update:
                should_update, reason = True, "forced update"
            else:
                should_update, reason = self._should_update_game(url, game_data)

            if should_update:
                refresh_interval_days = self._calculate_refresh_interval(game_data)
                release_date_info = self._get_release_date_info(game_data)
                GameUpdateLogger.log_game_update_start(platform, game_name, game_data.last_updated,
                                                     refresh_interval_days, reason, release_info=release_date_info)

                updated_data = self._fetch_game_data(url, platform)

                if updated_data:
                    # Update timestamp and store object directly
                    updated_data.last_updated = datetime.now().isoformat()
                    self.other_games_data['games'][url] = updated_data
                    updated_count += 1
                    GameUpdateLogger.log_game_update_success(updated_data.name)
                else:
                    GameUpdateLogger.log_game_update_failure(url, platform)
            else:
                # Log skip info with detailed reason
                refresh_interval_days = self._calculate_refresh_interval(game_data)
                release_date_info = self._get_release_date_info(game_data)
                GameUpdateLogger.log_game_skip(platform, game_name, game_data.last_updated,
                                             refresh_interval_days, reason, release_date_info)

        if updated_count > 0:
            self._save_other_games_data()
            logging.info(f"Other games refresh completed. Updated {updated_count}/{total_games} games")
        else:
            logging.info("No other platform games needed updates")

        return updated_count
