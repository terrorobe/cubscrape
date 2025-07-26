"""
CLI Command Handlers

Handles argument parsing and command dispatch for the scraper application.
Each command is implemented as a separate function for better organization.
"""

import argparse
import atexit
import logging
import os
import signal
import sys
from pathlib import Path

from .config_manager import ConfigManager
from .database_manager import DatabaseManager
from .game_unifier import load_all_unified_games
from .other_games_updater import OtherGamesUpdater
from .reference_validator import ReferenceValidator
from .scraper import YouTubeSteamScraper
from .steam_updater import SteamDataUpdater


class CLICommands:
    """Handles CLI command parsing and execution"""

    def __init__(self) -> None:
        self.parser = self._create_parser()
        self.lock_file_path: Path | None = None

    def _create_lock_file(self) -> None:
        """Create a lock file in the data directory"""
        project_root = self._get_project_root()
        self.lock_file_path = project_root / "data" / ".cubscrape.lock"

        # Check if lock file already exists
        if self.lock_file_path.exists():
            # Read the PID from the lock file
            try:
                with self.lock_file_path.open() as f:
                    pid = int(f.read().strip())

                # Check if process is still running
                try:
                    # On Unix, sending signal 0 checks if process exists
                    os.kill(pid, 0)
                    logging.error(f"Another cubscrape instance is already running (PID: {pid})")
                    sys.exit(1)
                except ProcessLookupError:
                    # Process no longer exists, remove stale lock file
                    logging.warning(f"Removing stale lock file from PID {pid}")
                    self.lock_file_path.unlink()
            except (OSError, ValueError):
                # Invalid lock file content, remove it
                logging.warning("Removing invalid lock file")
                self.lock_file_path.unlink()

        # Create the lock file with current PID
        with self.lock_file_path.open('w') as f:
            f.write(str(os.getpid()))

        # Register cleanup function for normal exit
        atexit.register(self._remove_lock_file)

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        logging.info(f"Created lock file: {self.lock_file_path}")

    def _signal_handler(self, signum: int, _frame: object) -> None:
        """Handle termination signals gracefully"""
        signal_name = signal.Signals(signum).name
        logging.info(f"Received {signal_name}, cleaning up...")
        self._remove_lock_file()
        sys.exit(0)

    def _remove_lock_file(self) -> None:
        """Remove the lock file"""
        if self.lock_file_path and self.lock_file_path.exists():
            try:
                self.lock_file_path.unlink()
                logging.info(f"Removed lock file: {self.lock_file_path}")
            except Exception as e:
                logging.error(f"Failed to remove lock file: {e}")

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser with all command options"""
        parser = argparse.ArgumentParser(
            prog='cubscrape',
            description='YouTube gaming channel scraper with Steam integration',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog='''
Processing Modes:
  backfill          Process historical videos for channels
  cron              Daily run - process recent videos from all enabled channels
  reprocess         Reprocess existing videos with current game detection logic
  fetch-steam-apps  Fetch specific Steam app data by ID
  data-quality      Analyze and report data quality issues
  resolve-games     Find games for videos with missing/broken game data
  build-db          Build SQLite database from JSON data
  fetch-videos      Fetch new YouTube videos only (no game processing)
  refresh-steam     Update Steam game data only
  refresh-other     Update other platform games (Itch.io, CrazyGames) only
  steam-changes     Analyze changes in steam_games.json over git history
  validate          Validate cross-references and data integrity across all data

Examples:
  cubscrape cron                              # Process all channels (daily run)
  cubscrape cron --enable-cron-backfill      # Include backfill in cron run
  cubscrape backfill --channel dextag         # Backfill specific channel
  cubscrape backfill --max-new 50             # Backfill all channels, max 50 videos each
  cubscrape refresh-steam --max-steam-updates 100  # Update Steam data only
  cubscrape fetch-steam-apps --app-id 12345   # Fetch specific Steam app
  cubscrape data-quality                      # Run data quality checks
  cubscrape steam-changes --since "3 days ago" # Show Steam game changes
  cubscrape validate                          # Validate all data references
            '''
        )

        # Simplified mode help that works better with argparse formatting
        mode_help = 'Processing mode. Most common: cron (daily), backfill (historical), data-quality (analysis)'

        parser.add_argument(
            'mode',
            choices=['backfill', 'cron', 'reprocess', 'fetch-steam-apps', 'data-quality', 'resolve-games', 'build-db', 'fetch-videos', 'refresh-steam', 'refresh-other', 'steam-changes', 'validate'],
            help=mode_help
        )
        # Channel selection options
        channel_group = parser.add_argument_group('Channel Selection')
        channel_group.add_argument(
            '--channel',
            type=str,
            metavar='ID',
            help='Channel ID (e.g., dextag, nookrium). If not specified, processes all enabled channels'
        )
        channel_group.add_argument(
            '--all-channels',
            action='store_true',
            help='Explicitly process all channels (for reprocess mode)'
        )

        # Processing limits
        limits_group = parser.add_argument_group('Processing Limits')
        limits_group.add_argument(
            '--max-new',
            type=int,
            metavar='N',
            help='Maximum number of new videos to process per channel'
        )
        limits_group.add_argument(
            '--max-steam-updates',
            type=int,
            metavar='N',
            help='Maximum number of Steam games to update'
        )
        limits_group.add_argument(
            '--max-other-updates',
            type=int,
            metavar='N',
            help='Maximum number of other platform games to update'
        )

        # Special options
        special_group = parser.add_argument_group('Special Options')
        special_group.add_argument(
            '--force',
            action='store_true',
            help='Force update all games regardless of refresh intervals'
        )
        special_group.add_argument(
            '--app-id',
            type=str,
            metavar='ID[,ID...]',
            help='Steam app ID(s) to fetch (required for fetch-steam-apps mode)'
        )
        special_group.add_argument(
            '--cutoff-date',
            type=str,
            metavar='YYYY-MM-DD',
            help='Only process videos published after this date (backfill mode)'
        )
        special_group.add_argument(
            '--enable-cron-backfill',
            action='store_true',
            help='Enable backfill processing during cron run (overrides config setting)'
        )
        special_group.add_argument(
            '--disable-cron-backfill',
            action='store_true',
            help='Disable backfill processing during cron run (overrides config setting)'
        )
        special_group.add_argument(
            '--since',
            type=str,
            metavar='DATE',
            help='Date cutoff for steam-changes (e.g., "3 days ago", "2024-01-01", "1 week ago")'
        )
        return parser

    def parse_and_execute(self, args: list[str] | None = None) -> None:
        """Parse command line arguments and execute the appropriate command"""
        parsed_args = self.parser.parse_args(args)

        # Create lock file before executing any command
        self._create_lock_file()

        command_map = {
            'reprocess': self._handle_reprocess,
            'backfill': self._handle_backfill,
            'cron': self._handle_cron,
            'fetch-steam-apps': self._handle_fetch_steam_apps,
            'data-quality': self._handle_data_quality,
            'resolve-games': self._handle_resolve_games,
            'build-db': self._handle_build_db,
            'fetch-videos': self._handle_fetch_videos,
            'refresh-steam': self._handle_refresh_steam,
            'refresh-other': self._handle_refresh_other,
            'steam-changes': self._handle_steam_changes,
            'validate': self._handle_validate
        }

        handler = command_map.get(parsed_args.mode)
        if handler:
            try:
                handler(parsed_args)
            finally:
                # Always clean up lock file
                self._remove_lock_file()
        else:
            print(f"Unknown mode: {parsed_args.mode}")
            sys.exit(1)

    def _get_project_root(self) -> Path:
        """Get the project root directory"""
        script_dir = Path(__file__).resolve().parent
        return script_dir.parent

    def _calculate_backfill_allocation(self, enabled_channels: list[str], total_budget: int) -> dict[str, int]:
        """
        Calculate video allocation per channel for cron backfill.

        Distributes the total video budget across all channels with a minimum of 10 videos per channel.
        If the budget can't provide 10 videos per channel, allocates what's available equally.

        Args:
            enabled_channels: List of enabled channel IDs
            total_budget: Total number of videos to process across all channels

        Returns:
            Dictionary mapping channel_id -> number of videos to process
        """
        if not enabled_channels or total_budget <= 0:
            return {}

        num_channels = len(enabled_channels)
        min_per_channel = 10

        # If budget allows minimum allocation for all channels
        if total_budget >= num_channels * min_per_channel:
            # Distribute remaining budget after guaranteeing minimum
            remaining_budget = total_budget - (num_channels * min_per_channel)
            extra_per_channel = remaining_budget // num_channels
            leftover = remaining_budget % num_channels

            allocation = {}
            for i, channel in enumerate(enabled_channels):
                # Give minimum + equal share of extra + 1 more for first 'leftover' channels
                videos = min_per_channel + extra_per_channel + (1 if i < leftover else 0)
                allocation[channel] = videos
        else:
            # Not enough budget for minimum allocation, distribute equally
            base_per_channel = total_budget // num_channels
            leftover = total_budget % num_channels

            allocation = {}
            for i, channel in enumerate(enabled_channels):
                # Give equal share + 1 more for first 'leftover' channels
                videos = base_per_channel + (1 if i < leftover else 0)
                allocation[channel] = videos

        return allocation

    def _get_channels_eligible_for_backfill(self, channels: list[str], cutoff_date: str | None) -> list[str]:
        """
        Filter channels to only include those that still have videos to backfill before the cutoff date.

        Args:
            channels: List of channel IDs to check
            cutoff_date: Cutoff date in YYYY-MM-DD format, or None to include all channels

        Returns:
            List of channel IDs that have videos eligible for backfill (oldest video is after cutoff)
        """
        if not cutoff_date:
            return channels

        from datetime import datetime

        from .data_manager import DataManager

        cutoff_datetime = datetime.fromisoformat(cutoff_date + "T00:00:00")
        eligible_channels = []

        project_root = self._get_project_root()
        data_manager = DataManager(project_root)

        for channel_id in channels:
            try:
                videos_data = data_manager.load_videos_data(channel_id)
                videos = videos_data.get('videos', {})

                if not videos:
                    # No videos means we can potentially backfill everything
                    eligible_channels.append(channel_id)
                    logging.info(f"Channel {channel_id} eligible for backfill (no videos yet)")
                    continue

                # Find the oldest video's publish date
                oldest_date = None
                for video in videos.values():
                    try:
                        video_date = datetime.fromisoformat(video.published_at.replace('Z', '+00:00'))
                        if oldest_date is None or video_date < oldest_date:
                            oldest_date = video_date
                    except (ValueError, AttributeError):
                        # Skip videos with invalid dates
                        continue

                # If oldest video is AFTER cutoff, we can still backfill more
                if oldest_date and oldest_date >= cutoff_datetime:
                    eligible_channels.append(channel_id)
                    logging.info(f"Channel {channel_id} eligible for backfill (oldest video: {oldest_date.date()}, cutoff: {cutoff_date})")
                else:
                    logging.info(f"Channel {channel_id} not eligible for backfill (already scraped to {oldest_date.date() if oldest_date else 'unknown'}, cutoff: {cutoff_date})")

            except Exception as e:
                logging.warning(f"Error checking backfill eligibility for channel {channel_id}: {e}")
                # Include channel if we can't determine eligibility
                eligible_channels.append(channel_id)

        return eligible_channels

    def _handle_reprocess(self, args: argparse.Namespace) -> None:
        """Handle reprocess command"""
        if args.channel:
            # Single channel reprocess mode
            scraper = YouTubeSteamScraper(args.channel)

            if not scraper.config_manager.validate_channel_exists(args.channel):
                print(f"Error: Channel '{args.channel}' not found in config.json")
                sys.exit(1)

            logging.info(f"Reprocess mode: reprocessing channel {args.channel}")
            scraper.reprocess_video_descriptions()
        else:
            print("Error: Either --channel or --all-channels is required for reprocess mode")
            sys.exit(1)

    def _handle_backfill(self, args: argparse.Namespace) -> None:
        """Handle backfill command"""
        project_root = self._get_project_root()
        config_manager = ConfigManager(project_root)
        channels = config_manager.get_channels()

        # Use global defaults if not specified via command line
        max_new_videos = args.max_new or config_manager.get_backfill_max_videos()
        cutoff_date = args.cutoff_date or config_manager.get_backfill_cutoff_date()

        if args.channel:
            # Single channel mode
            if not config_manager.validate_channel_exists(args.channel):
                print(f"Error: Channel '{args.channel}' not found in config.json")
                sys.exit(1)

            channels_to_process = [args.channel]
            logging.info(f"Backfill mode: processing single channel {args.channel}")
        else:
            # All channels mode
            channels_to_process = [ch for ch in channels if config_manager.is_channel_enabled(ch)]
            logging.info(f"Backfill mode: processing all enabled channels ({len(channels_to_process)} channels)")

        # Log the settings being used
        if max_new_videos:
            logging.info(f"Using max videos per channel: {max_new_videos}")
        if cutoff_date:
            logging.info(f"Using cutoff date: {cutoff_date}")

        # Process each channel (collect without saving)
        scrapers_to_save = []
        for channel_id in channels_to_process:
            logging.info(f"Processing channel: {channel_id}")
            scraper = YouTubeSteamScraper(channel_id)
            channel_url = config_manager.get_channel_url(channel_id)

            # Process videos without saving
            new_videos_processed = scraper.video_processor.process_videos(
                scraper.videos_data, channel_url, max_new_videos=max_new_videos,
                fetch_newest_first=False, cutoff_date=cutoff_date
            )
            logging.info(f"Completed: {new_videos_processed} new videos processed")

            # Collect scraper for later saving
            scrapers_to_save.append(scraper)

        # Update other platform games first (may contain Steam links)
        other_games_updater = OtherGamesUpdater()
        other_games_updater.update_games_from_channels(
            channels_to_process,
            max_updates=args.max_other_updates
        )

        # Update Steam data using SteamDataUpdater
        steam_updater = SteamDataUpdater()
        steam_updater.update_all_games_from_channels(
            channels_to_process,
            max_updates=args.max_steam_updates,
            pending_scrapers=scrapers_to_save
        )

        # Save all video data after Steam updates are complete
        for scraper in scrapers_to_save:
            scraper.save_videos()

    def _handle_cron(self, args: argparse.Namespace) -> None:
        """Handle cron command"""
        project_root = self._get_project_root()
        config_manager = ConfigManager(project_root)
        channels = config_manager.get_channels()

        # Process each enabled channel for recent videos (collect without saving)
        enabled_channels = []
        scrapers_to_save = []
        for channel_id in channels:
            if not config_manager.is_channel_enabled(channel_id):
                logging.info(f"Skipping disabled channel: {channel_id}")
                continue

            enabled_channels.append(channel_id)
            logging.info(f"Processing channel @{channel_id} (cron mode)")
            scraper = YouTubeSteamScraper(channel_id)

            # Process recent videos only (smaller batch for cron) - fetch newest first
            # Use process_videos_no_save to avoid saving before Steam updates
            channel_url = config_manager.get_channel_url(channel_id)
            new_videos_processed = scraper.video_processor.process_videos(
                scraper.videos_data, channel_url, max_new_videos=10,
                fetch_newest_first=True, cutoff_date=None
            )
            logging.info(f"Completed: {new_videos_processed} new videos processed")

            # Collect scraper for later saving
            scrapers_to_save.append(scraper)

        # Determine if backfill should run (command line overrides config)
        enable_backfill = config_manager.get_cron_enable_backfill()
        if args.enable_cron_backfill:
            enable_backfill = True
            logging.info("Backfill enabled via command line override")
        elif args.disable_cron_backfill:
            enable_backfill = False
            logging.info("Backfill disabled via command line override")

        # Optional backfill processing
        if enable_backfill:
            logging.info("Cron backfill is enabled - processing historical videos")

            # Get backfill settings and filter eligible channels
            cutoff_date = config_manager.get_backfill_cutoff_date()
            eligible_channels = self._get_channels_eligible_for_backfill(enabled_channels, cutoff_date)

            if not eligible_channels:
                logging.info("No channels eligible for backfill (all have reached cutoff date)")
            else:
                logging.info(f"Found {len(eligible_channels)} channels eligible for backfill: {', '.join(eligible_channels)}")

                total_budget = config_manager.get_cron_backfill_total_videos()
                allocation = self._calculate_backfill_allocation(eligible_channels, total_budget)

                if allocation:
                    total_allocated = sum(allocation.values())
                    logging.info(f"Backfill budget: {total_allocated} videos across {len(allocation)} channels")

                    for channel_id, videos_to_process in allocation.items():
                        logging.info(f"Cron backfill: processing {videos_to_process} videos for {channel_id}")
                        scraper = YouTubeSteamScraper(channel_id)
                        channel_url = config_manager.get_channel_url(channel_id)

                        # Process backfill videos without saving
                        new_videos_processed = scraper.video_processor.process_videos(
                            scraper.videos_data, channel_url, max_new_videos=videos_to_process,
                            fetch_newest_first=False, cutoff_date=cutoff_date
                        )
                        logging.info(f"Completed: {new_videos_processed} new videos processed")

                        # Add to scrapers to save later
                        scrapers_to_save.append(scraper)
                else:
                    logging.info("No videos allocated for backfill this run")
        else:
            logging.info("Cron backfill disabled")

        # Update other platform games first (may contain Steam links)
        if enabled_channels:
            other_games_updater = OtherGamesUpdater()
            other_games_updater.update_games_from_channels(
                enabled_channels,
                max_updates=args.max_other_updates
            )

            # Update Steam data once for all enabled channels
            steam_updater = SteamDataUpdater()
            steam_updater.update_all_games_from_channels(
                enabled_channels,
                max_updates=args.max_steam_updates,
                pending_scrapers=scrapers_to_save
            )

            # Run cross-platform auto-linking after all updates
            logging.info("Running cross-platform auto-linking")
            from .cross_platform_matcher import run_cross_platform_matching
            stats = run_cross_platform_matching(project_root)
            if 'error' not in stats:
                logging.info(f"Auto-linking results: {stats['approved_links']} new links, "
                           f"{stats['conflicting_links_removed']} conflicts resolved")

        # Save all video data after Steam updates are complete
        for scraper in scrapers_to_save:
            scraper.save_videos()

    def _handle_fetch_steam_apps(self, args: argparse.Namespace) -> None:
        """Handle fetch-steam-apps command"""
        if not args.app_id:
            print("Error: --app-id is required for fetch-steam-apps mode")
            sys.exit(1)

        # Parse app IDs (support comma-separated list)
        app_ids = [app_id.strip() for app_id in args.app_id.split(',')]

        # Use SteamDataUpdater for app fetching
        steam_updater = SteamDataUpdater()

        success_count = 0
        failed_count = 0

        for app_id in app_ids:
            if steam_updater.fetch_single_app(app_id):
                logging.info(f"Successfully fetched data for app {app_id}")
                success_count += 1
            else:
                logging.warning(f"Failed to fetch data for app {app_id}")
                failed_count += 1

        # Summary
        total = len(app_ids)
        if total > 1:
            logging.info(f"Fetched {success_count}/{total} apps successfully")
            if failed_count > 0:
                logging.warning(f"{failed_count} apps failed to fetch")

    def _handle_data_quality(self, _args: argparse.Namespace) -> None:
        """Handle data-quality command"""
        project_root = self._get_project_root()
        config_manager = ConfigManager(project_root)
        channels = config_manager.get_channels()

        # Use first available channel to access data files
        first_channel = next(iter(channels.keys()))
        scraper = YouTubeSteamScraper(first_channel)

        logging.info("Data quality check: analyzing all channels and games")
        scraper.check_data_quality(channels)

    def _handle_resolve_games(self, _args: argparse.Namespace) -> None:
        """Handle resolve-games command"""
        project_root = self._get_project_root()
        config_manager = ConfigManager(project_root)
        channels = config_manager.get_channels()

        # Use first available channel to access data files
        first_channel = next(iter(channels.keys()))
        scraper = YouTubeSteamScraper(first_channel)

        logging.info("Resolving games: finding games for videos with missing, broken, or stub game data")
        scraper.resolve_games(channels)

    def _handle_build_db(self, _args: argparse.Namespace) -> None:
        """Handle build-db command"""
        logging.info("Building SQLite database from existing JSON data")
        project_root = self._get_project_root()
        unified_games = load_all_unified_games(project_root)
        db_manager = DatabaseManager()
        db_manager.create_database(unified_games)

    def _handle_fetch_videos(self, args: argparse.Namespace) -> None:
        """Handle fetch-videos command - only fetch new YouTube videos without processing game data"""
        project_root = self._get_project_root()
        config_manager = ConfigManager(project_root)
        channels = config_manager.get_channels()

        if args.channel:
            if not config_manager.validate_channel_exists(args.channel):
                print(f"Error: Channel '{args.channel}' not found in config.json")
                sys.exit(1)
            channels_to_process = [args.channel]
            logging.info(f"Fetch videos mode: processing channel {args.channel}")
        else:
            channels_to_process = [ch for ch in channels if config_manager.is_channel_enabled(ch)]
            logging.info(f"Fetch videos mode: processing all enabled channels ({len(channels_to_process)} channels)")

        total_new_videos = 0
        for channel_id in channels_to_process:
            logging.info(f"Fetching videos for channel: {channel_id}")
            scraper = YouTubeSteamScraper(channel_id)
            channel_url = config_manager.get_channel_url(channel_id)

            new_videos = scraper.process_videos(
                channel_url,
                max_new_videos=args.max_new,
                fetch_newest_first=True,
                cutoff_date=args.cutoff_date
            )
            total_new_videos += new_videos
            logging.info(f"Fetched {new_videos} new videos for {channel_id}")

        logging.info(f"Fetch videos completed. Total new videos: {total_new_videos}")


    def _handle_refresh_steam(self, args: argparse.Namespace) -> None:
        """Handle refresh-steam command - only refresh Steam game data"""
        project_root = self._get_project_root()
        config_manager = ConfigManager(project_root)
        channels = config_manager.get_channels()

        # Get all enabled channels for Steam updates
        enabled_channels = [ch for ch in channels if config_manager.is_channel_enabled(ch)]

        if not enabled_channels:
            logging.warning("No enabled channels found")
            return

        logging.info("Refreshing Steam game data")
        steam_updater = SteamDataUpdater()
        steam_updater.update_all_games_from_channels(
            enabled_channels,
            max_updates=args.max_steam_updates
        )

    def _handle_refresh_other(self, args: argparse.Namespace) -> None:
        """Handle refresh-other command - only refresh other games (Itch.io, CrazyGames) data"""
        logging.info("Refreshing other games data (Itch.io, CrazyGames)")
        other_games_updater = OtherGamesUpdater()
        other_games_updater.update_all_other_games(force_update=args.force)

    def _handle_steam_changes(self, args: argparse.Namespace) -> None:
        """Handle steam-changes command - analyze changes in steam_games.json"""
        from .steam_changes import SteamChangesAnalyzer

        project_root = self._get_project_root()
        analyzer = SteamChangesAnalyzer(project_root)

        # Use default of "1 week ago" if not specified
        since_date = args.since or "1 week ago"
        analyzer.analyze_changes(since_date)

    def _handle_validate(self, _args: argparse.Namespace) -> None:
        """Handle validate command - validate cross-references and data integrity"""
        from .data_manager import DataManager

        logging.info("Running comprehensive data validation...")

        # Initialize data manager and validator
        project_root = self._get_project_root()
        data_manager = DataManager(project_root)
        validator = ReferenceValidator(data_manager)

        # Get all channel IDs from config
        config_manager = ConfigManager(project_root)
        all_channels = config_manager.get_channels()
        channel_ids = list(all_channels.keys())

        # Run validation
        validation_errors = validator.validate_all(channel_ids)

        # Print report
        validator.print_validation_report()

        # Exit with error code if there are validation errors
        errors = [e for e in validation_errors if e.severity == "error"]
        if errors:
            logging.error(f"Validation failed with {len(errors)} errors")
            sys.exit(1)
        else:
            logging.info("All validation checks passed!")


def main() -> None:
    """Main entry point for CLI"""
    cli = CLICommands()
    cli.parse_and_execute()


if __name__ == "__main__":
    main()

