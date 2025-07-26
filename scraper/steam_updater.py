"""
Steam Data Updater - Orchestrates Steam game updates across multiple channels
"""
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from dateutil.parser import parse as dateutil_parse

if TYPE_CHECKING:
    from .scraper import YouTubeSteamScraper

from .data_manager import DataManager, SteamDataDict
from .models import SteamGameData
from .steam_fetcher import SteamDataFetcher
from .update_logger import GameUpdateLogger
from .utils import extract_steam_app_id


class SteamDataUpdater:
    """
    Orchestrates Steam game data updates by:
    1. Collecting Steam IDs from multiple channel video files
    2. Managing the steam_games.json file
    3. Applying age-based refresh intervals
    4. Using SteamDataFetcher for individual game fetching
    """

    def __init__(self) -> None:
        self.data_manager = DataManager(Path.cwd())
        self.steam_data: SteamDataDict = self.data_manager.load_steam_data()
        self.steam_fetcher = SteamDataFetcher(self.data_manager)

    def _save_steam_data(self) -> None:
        """Save Steam data to file"""
        self.data_manager.save_steam_data(self.steam_data)


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

        For stub entries: Always return 30 days (monthly) to avoid frequent retries
        For released games: Based on age since release
        For unreleased games: Based on days until earliest possible release
        """
        # For stub entries, use monthly refresh interval to avoid frequent retries
        if game_data.is_stub:
            return 30

        release_info = game_data.planned_release_date or game_data.release_date
        if not release_info:
            return 30 if game_data.coming_soon else 7  # Monthly for unknown unreleased, weekly for unknown released

        if game_data.coming_soon:
            days_until_release = self._get_days_until_release(release_info)
            return self._interval_for_days_until_release(days_until_release, release_info)
        else:
            # For released games, use flexible parsing
            parsed_date, granularity = self._parse_steam_date(release_info)
            if parsed_date:
                age_days = (datetime.now() - parsed_date).days
                return self._interval_for_age(age_days)
            else:
                return 7  # Default to weekly if unparseable

    def _get_days_until_release(self, release_info: str) -> int:
        """
        Calculate days until the earliest possible release date using flexible parsing.
        Returns the number of days until the start of the release window.
        """
        now = datetime.now()

        # Use new flexible parsing with granularity detection
        parsed_date, granularity = self._parse_steam_date(release_info)

        if parsed_date:
            return (parsed_date - now).days

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
        if age_days <= 1:
            return 0  # Every cycle for first day after release
        elif age_days < 14:
            return 1  # Daily for new games
        elif age_days < 365:
            return 7  # Weekly for recent games
        else:
            return 30  # Monthly for older games

    def _parse_steam_date(self, date_str: str) -> tuple[datetime | None, str | None]:
        """
        Parse Steam release dates with granularity detection.
        Returns (parsed_date, granularity) or (None, None) if unparseable.
        For imprecise dates (year, quarter), returns the earliest possible date.
        """
        if not date_str:
            return None, None

        date_str = date_str.strip()

        # Detect granularity first
        granularity = self._detect_granularity(date_str)

        # Handle quarter format - use first day of the quarter
        if granularity == 'quarter' and date_str.upper().startswith('Q'):
            try:
                quarter = int(date_str[1])
                year = int(date_str.split()[1])
                # First month of each quarter: Q1=Jan, Q2=Apr, Q3=Jul, Q4=Oct
                quarter_start_month = (quarter - 1) * 3 + 1
                quarter_start = datetime(year, quarter_start_month, 1)
                return quarter_start, granularity
            except (ValueError, IndexError):
                return None, None

        # Handle year-only format - use January 1st
        elif granularity == 'year':
            try:
                year = int(date_str)
                year_start = datetime(year, 1, 1)
                return year_start, granularity
            except ValueError:
                return None, None

        # Use dateutil for flexible parsing of all other dates
        try:
            parsed = dateutil_parse(date_str)
            # For month-level dates, ensure we use first day of month
            if granularity == 'month':
                parsed = parsed.replace(day=1)
            return parsed, granularity
        except Exception:
            return None, None

    def _detect_granularity(self, date_str: str) -> str:
        """Detect the granularity of a date string."""
        date_str = date_str.lower().strip()

        # Quarter notation
        if re.match(r'q[1-4]\s+\d{4}', date_str):
            return 'quarter'

        # Year only
        if re.match(r'^\d{4}$', date_str):
            return 'year'

        # Month + Year (two words, second is 4-digit year)
        if re.match(r'^\w+\s+\d{4}$', date_str):
            return 'month'

        # Assume anything else is day-level if it has more components
        return 'day'

    def _is_overdue_release(self, game_data: SteamGameData) -> bool:
        """Check if game has passed its exact release date but is still marked as coming soon."""
        if not game_data.coming_soon:
            return False

        release_info = game_data.planned_release_date or game_data.release_date
        if not release_info:
            return False

        # Use new flexible parsing
        parsed_date, granularity = self._parse_steam_date(release_info)

        # Only check day-level dates for overdue (skip imprecise dates)
        if parsed_date and granularity == 'day':
            return datetime.now() >= parsed_date

        return False

    def _extract_steam_app_id(self, steam_url: str) -> str | None:
        """Extract Steam app ID from a Steam URL"""
        if not steam_url:
            return None

        return extract_steam_app_id(steam_url)

    def _collect_steam_app_ids_from_videos(self, videos_dict: dict, steam_app_ids: set,
                                         latest_video_dates: dict[str, datetime]) -> None:
        """Helper method to collect Steam app IDs from a videos dictionary"""
        for video in videos_dict.values():
            # Check multi-game format
            for game_ref in video.game_references:
                if game_ref.platform == 'steam':
                    steam_app_ids.add(game_ref.platform_id)

                    # Track latest video date for this game
                    if video.published_at:
                        try:
                            video_date = datetime.fromisoformat(video.published_at.replace('Z', '+00:00'))
                            if game_ref.platform_id not in latest_video_dates or video_date > latest_video_dates[game_ref.platform_id]:
                                latest_video_dates[game_ref.platform_id] = video_date
                        except ValueError:
                            continue

    def update_all_games_from_channels(self, channels: list[str], max_updates: int | None = None,
                                     pending_scrapers: list['YouTubeSteamScraper'] | None = None) -> None:
        """
        Update Steam data for all games referenced in the specified channels.

        Args:
            channels: List of channel names to process
            max_updates: Maximum number of games to update (None for all)
            pending_scrapers: List of scrapers with in-memory video data to include
        """
        logging.info("Updating Steam data using age-based refresh intervals")

        # Collect all Steam app IDs from all channels and build latest video date cache
        steam_app_ids: set[str] = set()
        latest_video_dates: dict[str, datetime] = {}  # app_id -> latest datetime

        # First, collect from saved video data
        for channel in channels:
            videos_data = self.data_manager.load_videos_data(channel)
            if videos_data and 'videos' in videos_data:
                self._collect_steam_app_ids_from_videos(videos_data['videos'], steam_app_ids, latest_video_dates)

        # Second, collect from pending in-memory scrapers
        if pending_scrapers:
            for scraper in pending_scrapers:
                if scraper.videos_data and 'videos' in scraper.videos_data:
                    self._collect_steam_app_ids_from_videos(scraper.videos_data['videos'], steam_app_ids, latest_video_dates)

        # Also collect Steam app IDs from other games data (Itch.io with Steam links)
        # Track mapping of Steam app IDs to their Itch URLs
        steam_to_itch_urls = {}  # app_id -> itch_url
        other_games_data = self.data_manager.load_other_games_data()
        other_steam_count = 0
        if other_games_data and 'games' in other_games_data:
            for itch_url, game_data in other_games_data['games'].items():
                if game_data.steam_url:
                    # Extract app ID from Steam URL
                    app_id = self._extract_steam_app_id(game_data.steam_url)
                    if app_id and app_id not in steam_app_ids:
                        steam_app_ids.add(app_id)
                        other_steam_count += 1
                        logging.info(f"Found Steam link from {game_data.platform}: {game_data.name} -> {app_id}")

                    # Track the Itch URL for this Steam game
                    if app_id and game_data.platform == 'itch':
                        steam_to_itch_urls[app_id] = itch_url

        if other_steam_count > 0:
            logging.info(f"Added {other_steam_count} Steam games from other platforms")

        # Collect resolved_to targets from stub entries that need fetching
        missing_resolved_targets = set()
        for stub_app_id, stub_game_data in self.steam_data['games'].items():
            if stub_game_data.is_stub and stub_game_data.resolved_to and stub_game_data.resolved_to not in self.steam_data['games']:
                missing_resolved_targets.add(stub_game_data.resolved_to)
                logging.info(f"Found missing resolved target: {stub_app_id} -> {stub_game_data.resolved_to}")
        # Add missing resolved targets to the fetch list
        steam_app_ids.update(missing_resolved_targets)
        if missing_resolved_targets:
            logging.info(f"Added {len(missing_resolved_targets)} missing resolved targets to fetch list")

        logging.info(f"Found {len(steam_app_ids)} unique Steam games total")

        updates_done = 0

        for app_id in steam_app_ids:
            # Check if we've hit the max updates limit
            if max_updates and updates_done >= max_updates:
                logging.info(f"Reached max_updates limit ({max_updates})")
                break

            # Check if data needs updating based on various triggers
            should_update = True
            update_reason = "new game"

            if app_id in self.steam_data['games']:
                steam_game_data: SteamGameData = self.steam_data['games'][app_id]

                # Check for overdue release trigger
                if self._is_overdue_release(steam_game_data):
                    should_update = True
                    update_reason = "overdue release"

                # Check for recent video reference trigger
                elif steam_game_data.last_updated:
                    last_updated_date = datetime.fromisoformat(steam_game_data.last_updated)
                    latest_video_date = latest_video_dates.get(app_id)

                    if latest_video_date and latest_video_date > last_updated_date:
                        should_update = True
                        update_reason = "recent video reference"

                    # Check normal age-based refresh intervals
                    else:
                        refresh_interval_days = self._get_refresh_interval_days(steam_game_data)
                        stale_date = datetime.now() - timedelta(days=refresh_interval_days)

                        if last_updated_date > stale_date:
                            release_date_info = self._get_release_date_info(steam_game_data)
                            GameUpdateLogger.log_game_skip("steam", steam_game_data.name, steam_game_data.last_updated,
                                                         refresh_interval_days, release_info=release_date_info)
                            should_update = False
                        else:
                            update_reason = "scheduled refresh"

            if should_update:
                # Log update info including name and last update if known
                if app_id in self.steam_data['games']:
                    steam_game_data_for_logging: SteamGameData = self.steam_data['games'][app_id]
                    refresh_interval_days = self._get_refresh_interval_days(steam_game_data_for_logging)
                    release_date_info = self._get_release_date_info(steam_game_data_for_logging)

                    GameUpdateLogger.log_game_update_start("steam", steam_game_data_for_logging.name, steam_game_data_for_logging.last_updated,
                                                         refresh_interval_days, update_reason, app_id, release_date_info)
                else:
                    logging.info(f"Updating steam app {app_id} ({update_reason})")

                # Pass Itch URL if this Steam game was discovered from Itch
                related_itch_url: str | None = steam_to_itch_urls.get(app_id)
                if self._fetch_steam_app_with_related(app_id, related_itch_url):
                    updates_done += 1

        # Save updated data
        self._save_steam_data()
        logging.info(f"Steam data update complete. Updated {updates_done} games.")

    def _fetch_steam_app_with_related(self, app_id: str, itch_url: str | None = None) -> bool:
        """
        Fetch Steam app data and automatically fetch related demo/full game data.

        Args:
            app_id: Steam app ID to fetch
            itch_url: Optional Itch.io URL if this Steam game was discovered from Itch

        Returns:
            True if any data was updated, False otherwise
        """
        try:
            steam_url = f"https://store.steampowered.com/app/{app_id}"

            # Check if we need to fetch USD price
            fetch_usd = False
            if app_id in self.steam_data['games']:
                existing_data = self.steam_data['games'][app_id]
                # Fetch USD if it's missing or if EUR price changed
                fetch_usd = not existing_data.price_usd
            else:
                # New game, fetch both prices
                fetch_usd = True

            # Fetch the main app using SteamDataFetcher
            existing_game_data = self.steam_data['games'].get(app_id) if app_id in self.steam_data['games'] else None
            steam_data = self.steam_fetcher.fetch_data(steam_url, fetch_usd=fetch_usd, existing_data=existing_game_data)
            if not steam_data:
                GameUpdateLogger.log_game_update_failure(app_id, "steam")
                return False

            # Check if EUR price changed and we need to update USD
            if app_id in self.steam_data['games'] and not fetch_usd:
                existing_data = self.steam_data['games'][app_id]
                if existing_data.price_eur != steam_data.price_eur:
                    # EUR price changed, fetch USD too
                    steam_data_with_usd = self.steam_fetcher.fetch_data(steam_url, fetch_usd=True, existing_data=existing_data)
                    if steam_data_with_usd:
                        steam_data.price_usd = steam_data_with_usd.price_usd
                else:
                    # EUR price hasn't changed, preserve existing USD price
                    steam_data.price_usd = existing_data.price_usd

            # Save old data before updating (needed for demo removal detection)
            old_data = self.steam_data['games'].get(app_id)

            # Update with timestamp and Itch URL if provided
            steam_data = steam_data.model_copy(update={
                'last_updated': datetime.now().isoformat(),
                'itch_url': itch_url
            })
            self.steam_data['games'][app_id] = steam_data

            # Check if a demo became stubbed and clean up main game reference
            if (steam_data.is_stub and
                old_data and
                old_data.is_demo and
                old_data.full_game_app_id and
                not old_data.is_stub):

                # Demo was working but is now stubbed - clean up main game reference
                main_game_id = old_data.full_game_app_id
                if main_game_id in self.steam_data['games']:
                    main_game = self.steam_data['games'][main_game_id]
                    if main_game.demo_app_id == app_id:
                        # Remove the demo reference from the main game
                        updated_main_game = main_game.model_copy(update={
                            'demo_app_id': None,
                            'has_demo': False,
                            'last_updated': datetime.now().isoformat()
                        })
                        self.steam_data['games'][main_game_id] = updated_main_game
                        logging.info(f"  Cleaned up demo reference {app_id} from main game {main_game_id}")
            if itch_url:
                GameUpdateLogger.log_game_update_success(steam_data.name, additional_info="with Itch.io link")
            else:
                GameUpdateLogger.log_game_update_success(steam_data.name)

            # Handle demo -> full game relationship
            if steam_data.is_demo and steam_data.full_game_app_id:
                full_game_id = steam_data.full_game_app_id
                if self._should_update_related_app(full_game_id):
                    logging.info(f"  Found full game {full_game_id}, fetching data")
                    self._fetch_related_app(full_game_id, "full game")

            # Handle main game -> demo relationship
            # Check both current data and old data for demo_app_id
            demo_id = None
            force_demo_check = False

            if steam_data.has_demo and steam_data.demo_app_id:
                demo_id = steam_data.demo_app_id
            elif old_data and old_data.demo_app_id:
                demo_id = old_data.demo_app_id
                # Force immediate check when demo was removed
                force_demo_check = True
                logging.info(f"  Game no longer has demo, forcing check of previous demo {demo_id}")

            if demo_id and (force_demo_check or self._should_update_related_app(demo_id)):
                logging.info(f"  Fetching demo {demo_id}")
                self._fetch_related_app(demo_id, "demo")

            return True

        except Exception as e:
            GameUpdateLogger.log_game_update_failure(app_id, "steam", str(e))
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
            # Always fetch both prices for related apps
            existing_app_data = self.steam_data['games'].get(app_id)
            app_data = self.steam_fetcher.fetch_data(app_url, fetch_usd=True, existing_data=existing_app_data)
            if app_data:
                app_data = app_data.model_copy(update={'last_updated': datetime.now().isoformat()})
                self.steam_data['games'][app_id] = app_data
                GameUpdateLogger.log_game_update_success(app_data.name, additional_info=app_type)
                return True
            return False
        except Exception as e:
            GameUpdateLogger.log_game_update_failure(app_id, "steam", f"Error fetching {app_type} data: {e}")
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
