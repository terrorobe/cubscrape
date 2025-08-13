"""
Steam Data Updater - Orchestrates Steam game updates across multiple channels
"""
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dateutil.parser import parse as dateutil_parse

if TYPE_CHECKING:
    from .scraper import YouTubeSteamScraper

from .data_manager import DataManager, OtherGamesDataDict, SteamDataDict
from .models import SteamGameData
from .steam_fetcher import SteamDataFetcher
from .unified_data_collector import UnifiedDataCollector
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
        self.data_collector = UnifiedDataCollector(self.data_manager)

        # Deferred save support
        self.has_pending_updates = False

    def _save_steam_data(self, force: bool = False) -> None:
        """Save Steam data to file"""
        if self.has_pending_updates and not force:
            logging.debug("Deferring Steam save until other games data is saved")
            return

        self.data_manager.save_steam_data(self.steam_data)
        self.has_pending_updates = False

    def enable_deferred_save(self) -> None:
        """Enable deferred save mode - updates will be accumulated but not saved until save_pending_updates() is called"""
        self.has_pending_updates = True
        logging.debug("Enabled deferred save mode for Steam updates")

    def save_pending_updates(self) -> None:
        """Save any pending updates that were deferred"""
        if self.has_pending_updates:
            self._save_steam_data(force=True)
            self.has_pending_updates = False
            logging.debug("Saved pending Steam updates")

    def discard_pending_updates(self) -> None:
        """Discard any pending updates and reload from disk"""
        if self.has_pending_updates:
            self.steam_data = self.data_manager.load_steam_data()
            self.has_pending_updates = False
            logging.info("Discarded pending Steam updates and reloaded from disk")


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
        Applies deterministic skew to weekly (20%) and monthly (10%) refreshes to distribute load.

        For stub entries: Always return 30 days (monthly) to avoid frequent retries
        For released games: Based on age since release
        For unreleased games: Based on days until earliest possible release

        Skew applied:
        - Weekly games (7 days): ±20% (5-8 days)
        - Monthly games (30 days): ±10% (27-33 days)
        """
        # For stub entries, use monthly refresh interval to avoid frequent retries
        if game_data.is_stub:
            return 30

        release_info = game_data.planned_release_date or game_data.release_date
        if not release_info:
            base_interval = 30 if game_data.coming_soon else 7  # Monthly for unknown unreleased, weekly for unknown released
            return self._apply_refresh_skew(base_interval, game_data.last_updated)

        if game_data.coming_soon:
            days_until_release = self._get_days_until_release(release_info)
            base_interval = self._interval_for_days_until_release(days_until_release, release_info)
            return self._apply_refresh_skew(base_interval, game_data.last_updated)
        else:
            # For released games, use flexible parsing
            parsed_date, _ = self._parse_steam_date(release_info)
            if parsed_date:
                age_days = (datetime.now() - parsed_date).days
                base_interval = self._interval_for_age(age_days)
                return self._apply_refresh_skew(base_interval, game_data.last_updated)
            else:
                base_interval = 7  # Default to weekly if unparseable
                return self._apply_refresh_skew(base_interval, game_data.last_updated)

    def _get_days_until_release(self, release_info: str) -> int:
        """
        Calculate days until the earliest possible release date using flexible parsing.
        Returns the number of days until the start of the release window.
        """
        now = datetime.now()

        # Use new flexible parsing with granularity detection
        parsed_date, _ = self._parse_steam_date(release_info)

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

    def _apply_refresh_skew(self, base_interval_days: int, last_updated: str | None) -> int:
        """
        Apply deterministic skew to refresh intervals to distribute load over time.

        Uses last_updated timestamp as input to ensure fair rotation - each time a game
        updates, it gets a new timestamp and thus a new skew position for its next refresh.

        Args:
            base_interval_days: Base refresh interval in days
            last_updated: ISO timestamp string of last update

        Returns:
            Adjusted interval with skew applied (minimum 1 day)
        """
        # Apply different skew percentages based on interval type
        if not last_updated:
            return base_interval_days

        skew_range = None
        if base_interval_days == 7:
            # Weekly games: ±20% skew (±1.4 days)
            skew_range = 1.4
        elif base_interval_days == 30:
            # Monthly games: ±10% skew (±3 days)
            skew_range = 3.0
        else:
            # No skew for other intervals (daily, immediate, etc.)
            return base_interval_days

        # Hash the timestamp to get a consistent but varied number
        timestamp_hash = hash(last_updated) % 1000

        # Apply skew
        skew_factor = (timestamp_hash / 1000) * 2 - 1  # -1 to +1
        skew_days = skew_factor * skew_range

        skewed_interval = base_interval_days + skew_days
        return max(1, int(skewed_interval))

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

    def _collect_steam_app_ids_from_unified_data(self, all_videos_data: dict[str, Any], steam_app_ids: set[str],
                                               latest_video_dates: dict[str, datetime]) -> None:
        """Helper method to collect Steam app IDs from unified video data"""
        total_videos = 0
        for channel_data in all_videos_data.values():
            videos = channel_data.get('videos', {})
            total_videos += len(videos)

            # All video data is guaranteed to be VideoData objects by UnifiedDataCollector
            for video in videos.values():
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

        logging.info(f"Collected Steam app IDs from {total_videos} videos across {len(all_videos_data)} channels")

    def update_all_games_from_channels(self, channels: list[str], max_updates: int | None = None,
                                     pending_scrapers: list['YouTubeSteamScraper'] | None = None,
                                     pending_other_games_data: 'OtherGamesDataDict | None' = None) -> None:
        """
        Update Steam data for all games referenced in the specified channels.

        Args:
            channels: List of channel names to process
            max_updates: Maximum number of games to update (None for all)
            pending_scrapers: List of scrapers with in-memory video data to include
            pending_other_games_data: In-memory other games data to use instead of loading from disk
        """
        logging.info("Updating Steam data using age-based refresh intervals")

        # First: Process pending removals from removal detection
        self._process_pending_removals()

        # Collect all Steam app IDs from unified data source and build latest video date cache
        steam_app_ids: set[str] = set()
        latest_video_dates: dict[str, datetime] = {}  # app_id -> latest datetime

        # Use unified data collector to get all video data in consistent format
        all_videos_data = self.data_collector.collect_all_videos_data(channels, pending_scrapers)
        self._collect_steam_app_ids_from_unified_data(all_videos_data, steam_app_ids, latest_video_dates)

        # Also collect Steam app IDs from other games data (Itch.io with Steam links)
        # Track mapping of Steam app IDs to their Itch URLs
        steam_to_itch_urls = {}  # app_id -> itch_url

        # Use pending other games data if provided, otherwise load from disk
        if pending_other_games_data:
            other_games_data = pending_other_games_data
            logging.info(f"Using pending other games data with {len(other_games_data.get('games', {}))} games for Steam link collection")
        else:
            other_games_data = self.data_manager.load_other_games_data()
            logging.debug("Loading other games data from disk")

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

                # Check for needs_full_refresh flag
                if hasattr(steam_game_data, 'needs_full_refresh') and steam_game_data.needs_full_refresh:
                    should_update = True
                    update_reason = "needs full refresh"

                # Check for missing cross-platform reference
                else:
                    related_itch_url = steam_to_itch_urls.get(app_id)
                    if related_itch_url and not steam_game_data.itch_url:
                        should_update = True
                        update_reason = "missing itch_url cross-reference"

                    # Check for overdue release trigger
                    elif self._is_overdue_release(steam_game_data):
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

            # Skip removal_pending games in age-based refresh
            if app_id in self.steam_data['games'] and self.steam_data['games'][app_id].removal_pending:
                logging.debug(f"Skipping removal_pending game {app_id} in age-based refresh")
                should_update = False

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
                        steam_data.original_price_usd = steam_data_with_usd.original_price_usd
                else:
                    # EUR price hasn't changed, preserve existing USD price and original price
                    steam_data.price_usd = existing_data.price_usd
                    steam_data.original_price_usd = existing_data.original_price_usd

            # Save old data before updating (needed for demo removal detection)
            old_data = self.steam_data['games'].get(app_id)

            # Update with timestamp, clear needs_full_refresh flag, and add Itch URL if provided
            update_data = {
                'last_updated': datetime.now().isoformat(),
                'needs_full_refresh': False,  # Clear the flag after successful refresh
                'itch_url': itch_url
            }
            steam_data = steam_data.model_copy(update=update_data)
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

                # Check if we need to establish/fix bidirectional relationship
                needs_relationship_fix = self._needs_bidirectional_relationship_fix(app_id, full_game_id, "demo_to_full")
                if needs_relationship_fix:
                    logging.info(f"  Full game {full_game_id} doesn't reference demo {app_id}, forcing fetch to establish relationship")

                if needs_relationship_fix or self._should_update_related_app(full_game_id):
                    logging.info(f"  Found full game {full_game_id}, fetching data")
                    self._fetch_related_app(full_game_id, "full game", known_demo_id=app_id)

            # Handle main game -> demo relationship
            # Check both current data and old data for demo_app_id
            demo_id = None
            demo_was_removed = False

            if steam_data.has_demo and steam_data.demo_app_id:
                demo_id = steam_data.demo_app_id
            elif old_data and old_data.demo_app_id:
                demo_id = old_data.demo_app_id
                # Force immediate check when demo was removed from main game
                demo_was_removed = True
                logging.info(f"  Game no longer has demo, forcing check of previous demo {demo_id}")

            if demo_id:
                # Check if we need to establish/fix bidirectional relationship
                needs_relationship_fix = self._needs_bidirectional_relationship_fix(app_id, demo_id, "full_to_demo")
                if needs_relationship_fix:
                    logging.info(f"  Demo {demo_id} doesn't reference full game {app_id}, forcing fetch to establish relationship")

                if needs_relationship_fix or demo_was_removed or self._should_update_related_app(demo_id):
                    logging.info(f"  Fetching demo {demo_id}")
                    demo_fetched = self._fetch_related_app(demo_id, "demo", known_full_game_id=app_id)

                    # If we force-fetched a demo that was removed from sale but still exists,
                    # restore the bidirectional relationship
                    if demo_fetched and demo_was_removed and demo_id in self.steam_data['games']:
                        demo_data = self.steam_data['games'][demo_id]
                        if demo_data.full_game_app_id == app_id:
                            # Demo still points to this full game, restore the relationship
                            logging.info(f"  Restoring demo relationship for game {app_id} -> demo {demo_id}")
                            updated_game = steam_data.model_copy(update={
                                'demo_app_id': demo_id,
                                'has_demo': True
                            })
                            self.steam_data['games'][app_id] = updated_game

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

    def _needs_bidirectional_relationship_fix(self, source_id: str, target_id: str, relationship_type: str) -> bool:
        """
        Check if we need to force fetch to establish bidirectional relationship.

        Args:
            source_id: The app we're currently processing (demo or full game)
            target_id: The related app (full game or demo)
            relationship_type: Either "demo_to_full" or "full_to_demo"

        Returns:
            True if the target needs to be fetched to fix the relationship
        """
        if target_id not in self.steam_data['games']:
            return False  # Target doesn't exist, will be fetched anyway

        target_game = self.steam_data['games'][target_id]

        if relationship_type == "demo_to_full":
            # Check if full game knows about this demo
            if target_game.demo_app_id != source_id:
                if target_game.demo_app_id:
                    logging.warning(f"  Full game {target_id} references different demo {target_game.demo_app_id}, will update to {source_id}")
                return True
        elif relationship_type == "full_to_demo" and target_game.full_game_app_id != source_id:
            # Check if demo knows about this full game
            if target_game.full_game_app_id:
                logging.warning(f"  Demo {target_id} references different full game {target_game.full_game_app_id}, will update to {source_id}")
            return True

        return False

    def _fetch_related_app(self, app_id: str, app_type: str, known_full_game_id: str | None = None, known_demo_id: str | None = None) -> bool:
        """
        Fetch related app (demo or full game).

        Args:
            app_id: Steam app ID to fetch
            app_type: Type description for logging ("demo" or "full game")
            known_full_game_id: If fetching a demo, the known full game ID that references it
            known_demo_id: If fetching a full game, the known demo ID that references it

        Returns:
            True if successfully fetched, False otherwise
        """
        try:
            app_url = f"https://store.steampowered.com/app/{app_id}"
            # Always fetch both prices for related apps
            existing_app_data = self.steam_data['games'].get(app_id)
            app_data = self.steam_fetcher.fetch_data(app_url, fetch_usd=True, existing_data=existing_app_data, known_full_game_id=known_full_game_id)
            if app_data:
                update_fields = {
                    'last_updated': datetime.now().isoformat(),
                    'needs_full_refresh': False  # Clear the flag after successful refresh
                }

                # If this is a full game being fetched because a demo references it,
                # establish the bidirectional relationship
                if known_demo_id and app_type == "full game":
                    # Check if we're overwriting an existing demo reference
                    if app_data.demo_app_id and app_data.demo_app_id != known_demo_id:
                        logging.warning(f"  Overwriting existing demo reference on full game {app_id}: {app_data.demo_app_id} -> {known_demo_id}")

                    update_fields['demo_app_id'] = known_demo_id
                    update_fields['has_demo'] = True
                    logging.info(f"  Establishing bidirectional relationship: full game {app_id} <- demo {known_demo_id}")

                app_data = app_data.model_copy(update=update_fields)
                self.steam_data['games'][app_id] = app_data
                GameUpdateLogger.log_game_update_success(app_data.name, additional_info=app_type)
                return True
            else:
                # Handle removed apps - clean up broken relationships
                if app_type == "demo" and existing_app_data and existing_app_data.full_game_app_id:
                    # Clear the demo reference from the full game
                    full_game_id = existing_app_data.full_game_app_id
                    if full_game_id in self.steam_data['games']:
                        full_game = self.steam_data['games'][full_game_id]
                        if full_game.demo_app_id == app_id:
                            logging.info(f"  Clearing demo reference from full game {full_game_id}")
                            updated_full_game = full_game.model_copy(update={
                                'demo_app_id': None,
                                'has_demo': False,
                                'last_updated': datetime.now().isoformat()
                            })
                            self.steam_data['games'][full_game_id] = updated_full_game
                        else:
                            logging.warning(f"  Full game {full_game_id} doesn't reference demo {app_id} - possible data inconsistency")

                elif app_type == "full game" and existing_app_data:
                    # Find and clean up any demos that reference this removed full game
                    demos_to_clean = []
                    for demo_id, demo_data in self.steam_data['games'].items():
                        if demo_data.is_demo and demo_data.full_game_app_id == app_id:
                            demos_to_clean.append(demo_id)

                    # Clean up demo references
                    for demo_id in demos_to_clean:
                        demo_data = self.steam_data['games'][demo_id]
                        updated_demo = demo_data.model_copy(update={
                            'full_game_app_id': None,
                            'last_updated': datetime.now().isoformat()
                        })
                        self.steam_data['games'][demo_id] = updated_demo
                        logging.info(f"  Cleared full game reference from demo {demo_id}")

                # Mark the app as removed if it's still referenced by videos and we had existing data
                if existing_app_data and self.data_manager.is_game_referenced_by_videos('steam', app_id):
                    logging.info(f"  Marking {app_type} {app_id} as removed (referenced by videos)")
                    removed_data = existing_app_data.model_copy(update={
                        'name': existing_app_data.name + " [REMOVED]",
                        'error': "Removed from Steam",
                        'last_updated': datetime.now().isoformat()
                    })
                    self.steam_data['games'][app_id] = removed_data
                else:
                    # Remove the app entirely if not referenced
                    logging.info(f"  Removing {app_type} {app_id} (not referenced by videos)")
                    if app_id in self.steam_data['games']:
                        del self.steam_data['games'][app_id]

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

    def _process_pending_removals(self) -> None:
        """
        Process games with removal_pending: true.
        - Re-validates each game by fetching from Steam API
        - If game is available: Clear removal flags (false positive)
        - If game is still unavailable and referenced by videos: Convert to stub
        - If game is still unavailable and not referenced: Delete + break demo/full game references
        """
        removal_pending_games = []
        for app_id, game_data in self.steam_data['games'].items():
            if game_data.removal_pending:
                removal_pending_games.append((app_id, game_data))

        if not removal_pending_games:
            logging.debug("No removal pending games to process")
            return

        logging.info(f"Processing {len(removal_pending_games)} removal pending games with re-validation...")

        validated_removals = 0
        false_positives = 0

        for app_id, game_data in removal_pending_games:
            # Re-validate by attempting to fetch current Steam data
            logging.info(f"Re-validating removal for {app_id} ({game_data.name})...")

            is_still_available = self._revalidate_game_availability(app_id)

            if is_still_available:
                # False positive - game is actually available
                logging.info(f"Game {app_id} ({game_data.name}) is still available - clearing removal flags")
                restored_data = game_data.model_copy(update={
                    'removal_detected': None,
                    'removal_pending': False,
                    'last_updated': datetime.now().isoformat()
                })
                self.steam_data['games'][app_id] = restored_data
                false_positives += 1
                continue

            # Game is confirmed to be unavailable - proceed with removal processing
            validated_removals += 1
            is_referenced = self.data_manager.is_game_referenced_by_videos('steam', app_id)

            if is_referenced:
                # Convert to stub
                logging.info(f"Confirmed removal: Converting {app_id} ({game_data.name}) to stub (referenced by videos)")
                stub_data = game_data.model_copy(update={
                    'name': game_data.name + " [REMOVED]",
                    'is_stub': True,
                    'stub_reason': "Removed from Steam",
                    'removal_pending': False,
                    'last_updated': datetime.now().isoformat()
                })
                self.steam_data['games'][app_id] = stub_data
            else:
                # Delete and break relationships
                logging.info(f"Confirmed removal: Deleting {app_id} ({game_data.name}) (not referenced by videos)")

                # Break demo/full game relationships before deletion
                self._break_game_relationships(app_id, game_data)

                # Delete the game
                del self.steam_data['games'][app_id]

        # Save updated data
        self._save_steam_data()
        logging.info(f"Completed processing {len(removal_pending_games)} removal candidates: "
                    f"{validated_removals} confirmed removals, {false_positives} false positives restored")

    def _revalidate_game_availability(self, app_id: str) -> bool:
        """
        Re-validate if a game is available on Steam by attempting to fetch it with retries.

        Args:
            app_id: Steam app ID to validate

        Returns:
            bool: True if game is available, False if confirmed unavailable
        """
        steam_url = f"https://store.steampowered.com/app/{app_id}/"

        # Use the existing Steam fetcher with its built-in retry logic
        # Try with minimal data fetch (no USD price to be faster)
        try:
            logging.debug(f"Re-validating availability for Steam app {app_id}")
            steam_data = self.steam_fetcher.fetch_data(steam_url, fetch_usd=False)

            if steam_data and not steam_data.is_stub:
                # Game was successfully fetched and is not a stub
                logging.debug(f"Game {app_id} is confirmed available")
                return True
            else:
                # Failed to fetch or returned stub data
                logging.debug(f"Game {app_id} is confirmed unavailable")
                return False

        except Exception as e:
            # Any exception during fetch means the game is likely unavailable
            logging.warning(f"Re-validation failed for app {app_id}: {e}")
            return False

    def _break_game_relationships(self, app_id: str, game_data: SteamGameData) -> None:
        """Break demo/full game relationships when deleting a game"""
        if game_data.is_demo and game_data.full_game_app_id:
            # This is a demo, clean up the main game's demo reference
            full_game_id = game_data.full_game_app_id
            if full_game_id in self.steam_data['games']:
                full_game = self.steam_data['games'][full_game_id]
                if full_game.demo_app_id == app_id:
                    updated_full_game = full_game.model_copy(update={
                        'demo_app_id': None,
                        'has_demo': False,
                        'last_updated': datetime.now().isoformat()
                    })
                    self.steam_data['games'][full_game_id] = updated_full_game
                    logging.info(f"  Cleared demo reference {app_id} from full game {full_game_id}")

        elif game_data.has_demo and game_data.demo_app_id:
            # This is a full game with a demo, clean up the demo's full game reference
            demo_id = game_data.demo_app_id
            if demo_id in self.steam_data['games']:
                demo_game = self.steam_data['games'][demo_id]
                if demo_game.full_game_app_id == app_id:
                    updated_demo = demo_game.model_copy(update={
                        'full_game_app_id': None,
                        'last_updated': datetime.now().isoformat()
                    })
                    self.steam_data['games'][demo_id] = updated_demo
                    logging.info(f"  Cleared full game reference {app_id} from demo {demo_id}")
