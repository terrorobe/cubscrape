"""
Steam Data Updater - Orchestrates Steam game updates across multiple channels
"""
import logging
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

from data_manager import DataManager
from models import SteamGameData
from steam_fetcher import SteamDataFetcher


class SteamDataUpdater:
    """
    Orchestrates Steam game data updates by:
    1. Collecting Steam IDs from multiple channel video files
    2. Managing the steam_games.json file
    3. Applying age-based refresh intervals
    4. Using SteamDataFetcher for individual game fetching
    """

    def __init__(self):
        self.data_manager = DataManager(Path.cwd())
        self.steam_data = self.data_manager.load_steam_data()
        self.steam_fetcher = SteamDataFetcher()

    def _save_steam_data(self):
        """Save Steam data to file"""
        self.data_manager.save_steam_data(self.steam_data)

    def _get_interval_name(self, interval_days: int) -> str:
        """Convert interval days to human-readable name"""
        if interval_days == 1:
            return "daily"
        elif interval_days == 7:
            return "weekly"
        else:
            return "monthly"

    def _get_release_date_info(self, game_data: SteamGameData) -> str:
        """Get formatted release date information for logging"""
        if game_data.coming_soon:
            release_timeframe = game_data.planned_release_date or game_data.release_date
            return f", unreleased ({release_timeframe})" if release_timeframe else ", unreleased"
        elif game_data.release_date:
            return f", released {game_data.release_date}"
        else:
            return ""

    def _get_refresh_interval_days(self, game_data: SteamGameData) -> int:
        """
        Get refresh interval in days based on game age or proximity to release.

        For released games: Based on age since release
        For unreleased games: Based on days until earliest possible release
        """
        release_info = game_data.planned_release_date or game_data.release_date
        if not release_info:
            return 30 if game_data.coming_soon else 7  # Monthly for unknown unreleased, weekly for unknown released

        if game_data.coming_soon:
            days_until_release = self._get_days_until_release(release_info)
            return self._interval_for_days_until_release(days_until_release, release_info)
        else:
            try:
                release_date = datetime.strptime(release_info, "%d %b, %Y")
                age_days = (datetime.now() - release_date).days
                return self._interval_for_age(age_days)
            except Exception:
                return 7  # Default to weekly on any error

    def _get_days_until_release(self, release_info: str) -> int:
        """
        Calculate days until the earliest possible release date.
        Returns the number of days until the start of the release window.
        """
        now = datetime.now()

        # Try specific date format first
        try:
            release_date = datetime.strptime(release_info, "%d %b, %Y")
            return (release_date - now).days
        except ValueError:
            pass

        # Try month/year format - use first day of the month
        try:
            release_date = datetime.strptime(release_info, "%B %Y")
            return (release_date - now).days
        except ValueError:
            pass

        # Try quarter format - use first day of the quarter
        if release_info.startswith('Q'):
            try:
                quarter = int(release_info[1])
                year = int(release_info.split()[1])

                # First month of each quarter: Q1=Jan, Q2=Apr, Q3=Jul, Q4=Oct
                quarter_start_month = (quarter - 1) * 3 + 1
                quarter_start = datetime(year, quarter_start_month, 1)
                return (quarter_start - now).days
            except (ValueError, IndexError):
                pass

        # Try year-only format - use January 1st
        try:
            year = int(release_info)
            year_start = datetime(year, 1, 1)
            return (year_start - now).days
        except ValueError:
            pass

        return 365  # Default to distant future for unparseable formats

    def _interval_for_days_until_release(self, days_until: int, release_info: str) -> int:
        """Convert days until release to refresh interval with precision-aware minimums."""
        # Detect precision from format
        is_imprecise = (
            release_info.startswith('Q') or          # Q1 2025
            release_info.isdigit() or                # 2025
            len(release_info.split()) == 2           # "August 2025"
        )

        # Calculate base interval
        if days_until <= 3:
            base_interval = 1  # Daily when very close
        elif days_until <= 33:
            base_interval = 7  # Weekly within a month and a bit
        else:
            base_interval = 30  # Monthly for distant releases

        # Apply weekly minimum for imprecise dates
        if is_imprecise:
            return max(base_interval, 7)
        else:
            return base_interval

    def _interval_for_age(self, age_days: int) -> int:
        """Convert game age to refresh interval in days."""
        if age_days < 30:
            return 1  # Daily for new games
        elif age_days < 365:
            return 7  # Weekly for recent games
        else:
            return 30  # Monthly for older games

    def update_all_games_from_channels(self, channels: list[str], max_updates: int | None = None):
        """
        Update Steam data for all games referenced in the specified channels.

        Args:
            channels: List of channel names to process
            max_updates: Maximum number of games to update (None for all)
        """
        logging.info("Updating Steam data using age-based refresh intervals")

        # Collect all Steam app IDs from all channels
        steam_app_ids = set()
        for channel in channels:
            videos_data = self.data_manager.load_videos_data(channel)
            if videos_data and 'videos' in videos_data:
                for video in videos_data['videos'].values():
                    if video.steam_app_id:
                        steam_app_ids.add(video.steam_app_id)

        logging.info(f"Found {len(steam_app_ids)} unique Steam games")

        updates_done = 0

        for app_id in steam_app_ids:
            # Check if we've hit the max updates limit
            if max_updates and updates_done >= max_updates:
                logging.info(f"Reached max_updates limit ({max_updates})")
                break

            # Check if data needs updating based on age-based refresh intervals
            should_update = True
            if app_id in self.steam_data['games']:
                game_data = self.steam_data['games'][app_id]

                if game_data.last_updated:
                    last_updated_date = datetime.fromisoformat(game_data.last_updated)
                    refresh_interval_days = self._get_refresh_interval_days(game_data)
                    stale_date = datetime.now() - timedelta(days=refresh_interval_days)

                    if last_updated_date > stale_date:
                        days_ago = (datetime.now() - last_updated_date).days
                        interval_name = self._get_interval_name(refresh_interval_days)
                        release_date_info = self._get_release_date_info(game_data)
                        logging.info(f"Skipping app {app_id} ({game_data.name}) - updated {days_ago} days ago, {interval_name} refresh{release_date_info}")
                        should_update = False

            if should_update:
                # Log update info including name and last update if known
                if app_id in self.steam_data['games']:
                    game_data = self.steam_data['games'][app_id]

                    # Calculate days since last update if available
                    if game_data.last_updated:
                        last_updated_date = datetime.fromisoformat(game_data.last_updated)
                        days_ago = (datetime.now() - last_updated_date).days
                        update_info = f"updated {days_ago} days ago"
                    else:
                        update_info = "never updated"

                    # Get fetch interval and release date info
                    refresh_interval_days = self._get_refresh_interval_days(game_data)
                    interval_name = self._get_interval_name(refresh_interval_days)
                    release_date_info = self._get_release_date_info(game_data)

                    logging.info(f"Updating app {app_id} ({game_data.name}) - {update_info}, {interval_name} refresh{release_date_info}")
                else:
                    logging.info(f"Updating app {app_id} (new game)")

                if self._fetch_steam_app_with_related(app_id):
                    updates_done += 1

        # Save updated data
        self._save_steam_data()
        logging.info(f"Steam data update complete. Updated {updates_done} games.")

    def _fetch_steam_app_with_related(self, app_id: str) -> bool:
        """
        Fetch Steam app data and automatically fetch related demo/full game data.

        Args:
            app_id: Steam app ID to fetch

        Returns:
            True if any data was updated, False otherwise
        """
        try:
            steam_url = f"https://store.steampowered.com/app/{app_id}"

            # Fetch the main app using SteamDataFetcher
            steam_data = self.steam_fetcher.fetch_data(steam_url)
            if not steam_data:
                logging.warning(f"  Failed to fetch data for app {app_id}")
                return False

            # Update with timestamp
            steam_data = replace(steam_data, last_updated=datetime.now().isoformat())
            self.steam_data['games'][app_id] = steam_data
            logging.info(f"  Updated: {steam_data.name}")

            # Handle demo -> full game relationship
            if steam_data.is_demo and steam_data.full_game_app_id:
                full_game_id = steam_data.full_game_app_id
                if self._should_update_related_app(full_game_id):
                    logging.info(f"  Found full game {full_game_id}, fetching data")
                    self._fetch_related_app(full_game_id, "full game")

            # Handle main game -> demo relationship
            if steam_data.has_demo and steam_data.demo_app_id:
                demo_id = steam_data.demo_app_id
                if self._should_update_related_app(demo_id):
                    logging.info(f"  Found demo {demo_id}, fetching data")
                    self._fetch_related_app(demo_id, "demo")

            return True

        except Exception as e:
            logging.error(f"  Error fetching Steam data for {app_id}: {e}")
            return False

    def _should_update_related_app(self, app_id: str) -> bool:
        """Check if a related app (demo/full game) should be fetched"""
        # Don't fetch if we already have recent data
        if app_id in self.steam_data['games']:
            game_data = self.steam_data['games'][app_id]
            if game_data.last_updated:
                last_updated_date = datetime.fromisoformat(game_data.last_updated)
                # Use 7 day threshold for related apps
                stale_date = datetime.now() - timedelta(days=7)
                return last_updated_date < stale_date
        return True

    def _fetch_related_app(self, app_id: str, app_type: str) -> bool:
        """
        Fetch related app (demo or full game).

        Args:
            app_id: Steam app ID to fetch
            app_type: Type description for logging ("demo" or "full game")

        Returns:
            True if successfully fetched, False otherwise
        """
        try:
            app_url = f"https://store.steampowered.com/app/{app_id}"
            app_data = self.steam_fetcher.fetch_data(app_url)
            if app_data:
                app_data = replace(app_data, last_updated=datetime.now().isoformat())
                self.steam_data['games'][app_id] = app_data
                logging.info(f"  Updated {app_type}: {app_data.name}")
                return True
            return False
        except Exception as e:
            logging.error(f"  Error fetching {app_type} data: {e}")
            return False

    def fetch_single_app(self, app_id: str) -> bool:
        """
        Fetch a single Steam app (useful for single-app mode).
        Always fetches regardless of staleness.

        Args:
            app_id: Steam app ID to fetch

        Returns:
            True if successfully fetched, False otherwise
        """
        logging.info(f"Fetching single app: {app_id}")

        # For single app mode, we always fetch (ignoring staleness checks)
        success = self._fetch_steam_app_with_related(app_id)

        if success:
            self._save_steam_data()

        return success
