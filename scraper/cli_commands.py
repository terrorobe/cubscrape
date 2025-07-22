"""
CLI Command Handlers

Handles argument parsing and command dispatch for the scraper application.
Each command is implemented as a separate function for better organization.
"""

import argparse
import logging
import sys
from pathlib import Path

from .config_manager import ConfigManager
from .database_manager import DatabaseManager
from .game_unifier import load_all_unified_games
from .other_games_updater import OtherGamesUpdater
from .scraper import YouTubeSteamScraper
from .steam_updater import SteamDataUpdater


class CLICommands:
    """Handles CLI command parsing and execution"""

    def __init__(self) -> None:
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser with all command options"""
        parser = argparse.ArgumentParser(description="YouTube to Steam game scraper")
        parser.add_argument(
            'mode',
            choices=['backfill', 'cron', 'reprocess', 'fetch-steam-apps', 'data-quality', 'resolve-games', 'build-db', 'fetch-videos', 'refresh-steam', 'refresh-other'],
            help='Processing mode: backfill (single channel), cron (all channels), reprocess (reprocess existing videos), fetch-steam-apps (fetch specific Steam apps), data-quality, resolve-games (find games for videos with missing/broken/stub game data), build-db, fetch-videos (only fetch new videos), refresh-steam (only refresh Steam data), or refresh-other (only refresh other games data)'
        )
        parser.add_argument(
            '--channel',
            type=str,
            help='Channel ID for backfill/reprocess mode (optional for backfill - processes all channels if not specified)'
        )
        parser.add_argument(
            '--max-new',
            type=int,
            help='Maximum number of new videos to process'
        )
        parser.add_argument(
            '--max-steam-updates',
            type=int,
            help='Maximum number of Steam games to update'
        )
        parser.add_argument(
            '--max-other-updates',
            type=int,
            help='Maximum number of other platform games to update'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update all games regardless of refresh intervals'
        )
        parser.add_argument(
            '--app-id',
            type=str,
            help='Steam app ID(s) to fetch (required for fetch-steam-apps mode). Can be a single ID or comma-separated list'
        )
        parser.add_argument(
            '--cutoff-date',
            type=str,
            help='Date cutoff for backfill mode (YYYY-MM-DD format) - only process videos after this date'
        )
        return parser

    def parse_and_execute(self, args: list[str] | None = None) -> None:
        """Parse command line arguments and execute the appropriate command"""
        parsed_args = self.parser.parse_args(args)

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
            'refresh-other': self._handle_refresh_other
        }

        handler = command_map.get(parsed_args.mode)
        if handler:
            handler(parsed_args)
        else:
            print(f"Unknown mode: {parsed_args.mode}")
            sys.exit(1)

    def _get_project_root(self) -> Path:
        """Get the project root directory"""
        script_dir = Path(__file__).resolve().parent
        return script_dir.parent

    def _handle_reprocess(self, args: argparse.Namespace) -> None:
        """Handle reprocess command"""
        if not args.channel:
            print("Error: --channel is required for reprocess mode")
            sys.exit(1)

        scraper = YouTubeSteamScraper(args.channel)

        if not scraper.config_manager.validate_channel_exists(args.channel):
            print(f"Error: Channel '{args.channel}' not found in config.json")
            sys.exit(1)

        logging.info(f"Reprocess mode: reprocessing channel {args.channel}")
        scraper.reprocess_video_descriptions()

    def _handle_backfill(self, args: argparse.Namespace) -> None:
        """Handle backfill command"""
        project_root = self._get_project_root()
        config_manager = ConfigManager(project_root)
        channels = config_manager.get_channels()

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

        # Process each channel
        for channel_id in channels_to_process:
            logging.info(f"Processing channel: {channel_id}")
            scraper = YouTubeSteamScraper(channel_id)
            channel_url = config_manager.get_channel_url(channel_id)

            scraper.process_videos(
                channel_url,
                max_new_videos=args.max_new,
                cutoff_date=args.cutoff_date
            )

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
            max_updates=args.max_steam_updates
        )

    def _handle_cron(self, args: argparse.Namespace) -> None:
        """Handle cron command"""
        project_root = self._get_project_root()
        config_manager = ConfigManager(project_root)
        channels = config_manager.get_channels()

        # Process each enabled channel
        enabled_channels = []
        for channel_id in channels:
            if not config_manager.is_channel_enabled(channel_id):
                logging.info(f"Skipping disabled channel: {channel_id}")
                continue

            enabled_channels.append(channel_id)
            logging.info(f"Cron mode: processing channel {channel_id}")
            scraper = YouTubeSteamScraper(channel_id)

            # Process recent videos only (smaller batch for cron) - fetch newest first
            channel_url = config_manager.get_channel_url(channel_id)
            scraper.process_videos(channel_url, max_new_videos=10, fetch_newest_first=True)

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
                max_updates=args.max_steam_updates
            )

            # Run cross-platform auto-linking after all updates
            logging.info("Running cross-platform auto-linking")
            from .cross_platform_matcher import run_cross_platform_matching
            stats = run_cross_platform_matching(project_root)
            if 'error' not in stats:
                logging.info(f"Auto-linking results: {stats['approved_links']} new links, "
                           f"{stats['conflicting_links_removed']} conflicts resolved")

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


def main() -> None:
    """Main entry point for CLI"""
    cli = CLICommands()
    cli.parse_and_execute()


if __name__ == "__main__":
    main()

