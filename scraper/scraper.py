#!/usr/bin/env python3
"""
YouTube Channel Video Scraper with Steam Game Data Integration
"""

import argparse
import json
import logging
import sys
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config_manager import ConfigManager
from crazygames_fetcher import CrazyGamesDataFetcher
from data_manager import DataManager
from data_quality import DataQualityChecker
from game_inference import GameInferenceEngine
from itch_fetcher import ItchDataFetcher
from models import OtherGameData, SteamGameData, VideoData
from steam_fetcher import SteamDataFetcher
from steam_updater import SteamDataUpdater
from utils import extract_game_links, extract_steam_app_id
from youtube_extractor import YouTubeExtractor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class YouTubeSteamScraper:
    def __init__(self, channel_id: str):
        # Get the directory of this script, then build paths relative to project root
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent

        # Initialize managers and utilities
        self.config_manager = ConfigManager(project_root)
        self.data_manager = DataManager(project_root)
        self.youtube_extractor = YouTubeExtractor()
        self.game_inference = GameInferenceEngine()

        # Load data
        self.videos_data = self.data_manager.load_videos_data(channel_id)
        self.steam_data = self.data_manager.load_steam_data()
        self.other_games_data = self.data_manager.load_other_games_data()

        # Store channel info
        self.channel_id = channel_id

        # Initialize fetchers
        self.steam_fetcher = SteamDataFetcher()
        self.itch_fetcher = ItchDataFetcher()
        self.crazygames_fetcher = CrazyGamesDataFetcher()



    def save_videos(self):
        """Save video data to JSON file"""
        self.data_manager.save_videos_data(self.videos_data, self.channel_id)

    def save_steam(self):
        """Save Steam data to JSON file"""
        self.data_manager.save_steam_data(self.steam_data)

    def save_other_games(self):
        """Save other games data to JSON file"""
        self.data_manager.save_other_games_data(self.other_games_data)


    def extract_youtube_detected_game(self, video_id: str) -> Optional[str]:
        """Extract YouTube's detected game from JSON data as last resort"""
        return self.youtube_extractor.extract_youtube_detected_game(video_id)

    def fetch_itch_data(self, itch_url: str) -> Optional[OtherGameData]:
        """Fetch game data from Itch.io using the modular fetcher"""
        return self.itch_fetcher.fetch_data(itch_url)

    def fetch_crazygames_data(self, crazygames_url: str) -> Optional[OtherGameData]:
        """Fetch game data from CrazyGames using the modular fetcher"""
        return self.crazygames_fetcher.fetch_data(crazygames_url)

    def fetch_steam_data(self, steam_url: str) -> Optional[SteamGameData]:
        """Fetch game data from Steam using the modular fetcher"""
        return self.steam_fetcher.fetch_data(steam_url)

    def process_videos(self, channel_url: str, max_new_videos: Optional[int] = None, fetch_newest_first: bool = False, cutoff_date: Optional[str] = None):
        """Process YouTube videos only"""
        logging.info(f"Processing videos from channel: {channel_url}")

        if not max_new_videos:
            max_new_videos = 50

        # Parse cutoff date if provided
        cutoff_datetime = None
        if cutoff_date:
            try:
                from datetime import datetime
                cutoff_datetime = datetime.strptime(cutoff_date, '%Y-%m-%d')
                logging.info(f"Using cutoff date: {cutoff_date}")
            except ValueError:
                logging.error(f"Invalid cutoff date format: {cutoff_date}. Use YYYY-MM-DD format.")
                return

        known_video_ids = set(self.videos_data['videos'].keys())
        new_videos_processed = 0
        batch_size = min(max_new_videos * 2, 50)  # Fetch more IDs to account for known videos
        videos_fetched_total = 0
        consecutive_known_batches = 0
        cutoff_reached = False

        # Smart starting position: if we have videos and not fetching newest first, start from a reasonable offset
        if fetch_newest_first:
            smart_start_offset = 0  # Start from beginning (newest videos)
            logging.info("Fetching newest videos first (cron mode)")
        else:
            smart_start_offset = max(0, len(known_video_ids) - 10) if known_video_ids else 0
            if smart_start_offset > 0:
                logging.info(f"Smart start: skipping to position {smart_start_offset + 1} (have {len(known_video_ids)} videos)")

        videos_fetched_total = smart_start_offset

        while new_videos_processed < max_new_videos and not cutoff_reached:
            # Calculate how many videos to skip (based on total fetched so far)
            skip_count = videos_fetched_total

            logging.info(f"Fetching {batch_size} video IDs starting from position {skip_count + 1}")

            # Fetch videos with offset (lightweight - just IDs and basic info)
            videos = self.get_channel_videos_lightweight(channel_url, skip_count, batch_size)

            if not videos:
                logging.info("No more videos available from channel")
                break

            videos_fetched_total += len(videos)
            batch_new_count = 0
            new_videos_in_batch = []

            # First pass: identify new videos without fetching full metadata
            for video in videos:
                video_id = video['video_id']

                # Check if we've hit the max new videos limit
                if new_videos_processed >= max_new_videos:
                    break

                # Skip if we already have this video
                if video_id in known_video_ids:
                    continue

                new_videos_in_batch.append(video)
                if len(new_videos_in_batch) >= max_new_videos - new_videos_processed:
                    break

            if not new_videos_in_batch:
                consecutive_known_batches += 1
                logging.info("No new videos in this batch, continuing deeper into channel history")
                # If we've had 3 consecutive batches with no new videos, we're likely caught up
                if consecutive_known_batches >= 3:
                    logging.info("Hit 3 consecutive batches with no new videos, stopping search")
                    break
                continue

            # Second pass: fetch full metadata only for new videos
            logging.info(f"Found {len(new_videos_in_batch)} new videos, fetching full metadata")
            batch_new_count = 0
            for video in new_videos_in_batch:
                video_id = video['video_id']

                if new_videos_processed >= max_new_videos:
                    break

                # Get full video metadata
                try:
                    full_video = self.get_full_video_metadata(video_id)
                    if full_video:
                        video_date = full_video.get('published_at', '')[:10] if full_video.get('published_at') else 'Unknown'

                        # Check cutoff date if provided
                        if cutoff_datetime and video_date != 'Unknown':
                            try:
                                video_datetime = datetime.strptime(video_date, '%Y-%m-%d')
                                if video_datetime < cutoff_datetime:
                                    logging.info(f"Reached cutoff date. Stopping processing at video: {full_video.get('title', 'Unknown Title')} ({video_date})")
                                    cutoff_reached = True
                                    break
                            except ValueError:
                                logging.warning(f"Could not parse video date: {video_date}")

                        logging.info(f"Processing: {full_video.get('title', 'Unknown Title')} ({video_date})")
                        # Process video with game link extraction
                        video_data = self._process_video_game_links(full_video)

                        self.videos_data['videos'][video_id] = video_data
                        known_video_ids.add(video_id)  # Add to our tracking set
                        new_videos_processed += 1
                        batch_new_count += 1
                    else:
                        logging.warning(f"Failed to get full metadata for {video_id}")
                except Exception as e:
                    logging.error(f"Error processing video {video_id}: {e}")
                    continue

            logging.info(f"Processed {batch_new_count} new videos in this batch")

            # Treat batches with no successfully processed videos the same as empty batches
            if batch_new_count == 0:
                consecutive_known_batches += 1
                logging.info("No videos successfully processed in this batch, treating as empty batch")
                if consecutive_known_batches >= 3:
                    logging.info("Hit 3 consecutive unproductive batches, stopping search")
                    break
            else:
                consecutive_known_batches = 0

        self.save_videos()
        logging.info(f"Video processing complete. Processed {new_videos_processed} new videos.")

    def _process_video_game_links(self, video) -> VideoData:
        """Extract and process game links from a video"""
        # Convert VideoData to dict for processing, or use dict directly
        if isinstance(video, VideoData):
            video_dict = asdict(video)
        else:
            video_dict = video

        # Extract game links
        game_links = extract_game_links(video_dict['description'])

        # Store video data with game links if found
        video_data = VideoData(
            video_id=video_dict['video_id'],
            title=video_dict['title'],
            description=video_dict['description'],
            published_at=video_dict['published_at'],
            thumbnail=video_dict['thumbnail'],
            steam_app_id=None,
            itch_url=None,
            itch_is_demo=False,  # Flag to indicate itch.io is demo/test version
            crazygames_url=None,
            youtube_detected_game=None,
            youtube_detected_matched=None,
            inferred_game=None
        )

        # Priority: Steam > Itch.io > CrazyGames, but store all found links
        if game_links.steam:
            app_id = extract_steam_app_id(game_links.steam)
            video_data = replace(video_data, steam_app_id=app_id)
            # Store other platforms as secondary
            if game_links.itch:
                video_data = replace(video_data, itch_url=game_links.itch, itch_is_demo=True)
            if game_links.crazygames:
                video_data = replace(video_data, crazygames_url=game_links.crazygames)
            logging.info(f"  Found Steam link: {game_links.steam}" +
                        (f", Itch.io: {game_links.itch}" if game_links.itch else "") +
                        (f", CrazyGames: {game_links.crazygames}" if game_links.crazygames else ""))
        elif game_links.itch:
            video_data = replace(video_data, itch_url=game_links.itch)
            if game_links.crazygames:
                video_data = replace(video_data, crazygames_url=game_links.crazygames)
            logging.info(f"  Found Itch.io link: {game_links.itch}" +
                        (f", CrazyGames: {game_links.crazygames}" if game_links.crazygames else ""))

            # Fetch itch.io metadata if not already cached
            if game_links.itch not in self.other_games_data['games']:
                logging.info("  Fetching Itch.io metadata...")
                itch_data = self.fetch_itch_data(game_links.itch)
                if itch_data:
                    # Convert OtherGameData to dict for storage (until we migrate other_games_data structure)
                    itch_dict = asdict(itch_data)
                    itch_dict['last_updated'] = datetime.now().isoformat()
                    self.other_games_data['games'][game_links.itch] = itch_dict
                    self.save_other_games()

        elif game_links.crazygames:
            video_data = replace(video_data, crazygames_url=game_links.crazygames)
            logging.info(f"  Found CrazyGames link: {game_links.crazygames}")

            # Fetch CrazyGames metadata if not already cached
            if game_links.crazygames not in self.other_games_data['games']:
                logging.info("  Fetching CrazyGames metadata...")
                crazygames_data = self.fetch_crazygames_data(game_links.crazygames)
                if crazygames_data:
                    # Convert OtherGameData to dict for storage (until we migrate other_games_data structure)
                    crazygames_dict = asdict(crazygames_data)
                    crazygames_dict['last_updated'] = datetime.now().isoformat()
                    self.other_games_data['games'][game_links.crazygames] = crazygames_dict
                    self.save_other_games()

        else:
            logging.info("  No game links found, trying YouTube detection...")

            # Last resort: try YouTube's detected game
            detected_game = self.extract_youtube_detected_game(video_dict['video_id'])
            if detected_game:
                logging.info(f"  YouTube detected game: {detected_game}")
                video_data = replace(video_data, youtube_detected_game=detected_game)

                # Check if this game should skip Steam matching
                skip_games = self.config_manager.get_skip_steam_matching_games()
                should_skip = any(skip_game.lower() in detected_game.lower() for skip_game in skip_games)

                # Try to find this game on Steam (unless matching is disabled)
                if not should_skip:
                    steam_match = self.find_steam_match(detected_game, confidence_threshold=0.6)
                    if steam_match:
                        video_data = replace(video_data, steam_app_id=steam_match['app_id'], youtube_detected_matched=True)
                        logging.info(f"  Matched to Steam: {steam_match['name']} (App ID: {steam_match['app_id']}, confidence: {steam_match['confidence']:.2f})")
                    else:
                        logging.info("  No confident Steam matches found for YouTube detected game")
                else:
                    logging.info(f"  Steam matching skipped for '{detected_game}' (in config skip list)")
            else:
                logging.info("  No YouTube detected game found")

        return video_data

    def reprocess_video_descriptions(self):
        """Reprocess existing video descriptions to extract game links with current logic"""
        logging.info("Reprocessing existing video descriptions")

        videos_processed = 0
        updated_count = 0

        for video_id, video_data in self.videos_data['videos'].items():
            video_date = video_data.published_at[:10] if video_data.published_at else None
            date_str = video_date if video_date else 'No date'
            logging.info(f"Reprocessing: {video_data.title} ({date_str})")

            # Store original data for comparison
            original_steam_id = video_data.steam_app_id
            original_itch_url = video_data.itch_url
            original_itch_is_demo = video_data.itch_is_demo
            original_crazygames_url = video_data.crazygames_url

            # Reprocess with current logic
            updated_video_data = self._process_video_game_links(video_data)

            # Check if anything changed
            if (updated_video_data.steam_app_id != original_steam_id or
                updated_video_data.itch_url != original_itch_url or
                updated_video_data.itch_is_demo != original_itch_is_demo or
                updated_video_data.crazygames_url != original_crazygames_url):
                updated_count += 1
                logging.info("  Updated game links for video")

            # Update the video data
            self.videos_data['videos'][video_id] = updated_video_data
            videos_processed += 1

        self.save_videos()
        logging.info(f"Reprocessing complete. Processed {videos_processed} videos, updated {updated_count} videos.")

    def get_channel_videos_lightweight(self, channel_url: str, skip_count: int, batch_size: int) -> List[Dict]:
        """Fetch lightweight video info (just IDs and titles) from YouTube channel"""
        return self.youtube_extractor.get_channel_videos_lightweight(channel_url, skip_count, batch_size)

    def get_full_video_metadata(self, video_id: str) -> Optional[Dict]:
        """Fetch full metadata for a specific video"""
        return self.youtube_extractor.get_full_video_metadata(video_id)

    def check_data_quality(self, channels_config: Dict):
        """Check data quality across all channels and games"""
        # Get the directory of this script, then build paths relative to project root
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent

        quality_checker = DataQualityChecker(project_root, self.steam_data, self.other_games_data)
        return quality_checker.check_data_quality(channels_config)

    def search_steam_games(self, query: str) -> List[Dict]:
        """Search Steam for games by name"""
        return self.game_inference.search_steam_games(query)

    def find_steam_match(self, game_name: str, confidence_threshold: float = 0.5) -> Optional[Dict]:
        """Find best Steam match for a game name with confidence scoring"""
        return self.game_inference.find_steam_match(game_name, confidence_threshold)

    def find_steam_match_interactive(self, game_name: str, confidence_threshold: float = 0.5) -> Optional[Dict]:
        """Find Steam match with interactive prompting for low confidence results"""
        return self.game_inference.find_steam_match_interactive(game_name, confidence_threshold)


    def _should_process_video_for_inference(self, video: Dict) -> Optional[str]:
        """Determine if video needs processing for game inference"""
        # Case 1: No game data at all
        if not video.get('steam_app_id') and not video.get('itch_url') and not video.get('crazygames_url'):
            return "no_game_data"

        # Case 2: Has steam_app_id but it's missing from our database
        steam_app_id = video.get('steam_app_id')
        if steam_app_id and steam_app_id not in self.steam_data.get('games', {}):
            return "missing_steam_game"

        return None

    def _check_steam_availability(self, app_id: str) -> str:
        """Check if Steam app is still available"""
        return self.game_inference.check_steam_availability(app_id)

    def infer_games_from_titles(self, channels_config: Dict):
        """Infer games from video titles and resolve missing Steam games"""
        print("\n" + "="*80)
        print("GAME INFERENCE AND MISSING STEAM GAMES RESOLUTION")
        print("="*80)

        total_videos_processed = 0
        games_found = 0
        missing_resolved = 0

        # Load all channel video files
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent

        for channel_id in channels_config:
            videos_file = project_root / 'data' / f'videos-{channel_id}.json'
            if not videos_file.exists():
                print(f"⚠️  Missing video file for channel {channel_id}: {videos_file}")
                continue

            with open(videos_file) as f:
                channel_data = json.load(f)

            print(f"\n📺 Processing channel: {channel_id}")

            # Find videos that need processing
            videos_to_process = []
            for video_id, video in channel_data.get('videos', {}).items():
                process_reason = self._should_process_video_for_inference(video)
                if process_reason:
                    videos_to_process.append((video_id, video, process_reason))

            if not videos_to_process:
                print("   ✅ All videos have valid game data")
                continue

            # Categorize videos
            no_game_data = [v for v in videos_to_process if v[2] == "no_game_data"]
            missing_steam = [v for v in videos_to_process if v[2] == "missing_steam_game"]

            print(f"   🔍 Found {len(no_game_data)} videos without game data")
            print(f"   🔍 Found {len(missing_steam)} videos with missing Steam games")

            channel_games_found = 0
            channel_missing_resolved = 0

            # Process all videos that need inference
            for _video_id, video, reason in videos_to_process:
                total_videos_processed += 1
                title = video.get('title', '')

                if reason == "missing_steam_game":
                    youtube_url = f"https://www.youtube.com/watch?v={video.get('video_id')}"
                    print(f"\n   📹 {title} [MISSING STEAM: {video.get('steam_app_id')}]")
                    print(f"      🔗 {youtube_url}")

                    # First, try to fetch the missing Steam game directly
                    missing_app_id = video.get('steam_app_id')
                    availability = self._check_steam_availability(missing_app_id)

                    if availability == "available":
                        print(f"      🔄 Steam app {missing_app_id} is available, attempting fetch...")
                        try:
                            steam_url = f"https://store.steampowered.com/app/{missing_app_id}"
                            steam_data = self.fetch_steam_data(steam_url)
                            if steam_data:
                                steam_data = replace(steam_data, last_updated=datetime.now().isoformat())
                                self.steam_data['games'][missing_app_id] = steam_data
                                print(f"      ✅ Successfully fetched: {steam_data.name}")
                                missing_resolved += 1
                                channel_missing_resolved += 1
                                continue
                        except Exception as e:
                            print(f"      ⚠️  Failed to fetch {missing_app_id}: {e}")

                    elif availability == "depublished":
                        print(f"      🚫 Steam app {missing_app_id} is depublished, searching for alternatives...")
                        # Mark the original as broken and try to find alternatives
                        video['broken_app_id'] = missing_app_id
                        video['steam_app_id'] = None  # Clear so we can find alternative

                    else:
                        print(f"      ❓ Steam app {missing_app_id} status unknown, searching for alternatives...")

                else:
                    youtube_url = f"https://www.youtube.com/watch?v={video.get('video_id')}"
                    print(f"\n   📹 {title}")
                    print(f"      🔗 {youtube_url}")

                # First try YouTube detection as it's more reliable than title parsing
                potential_names = []

                print("      🔍 Trying YouTube game detection...")
                detected_game = self.extract_youtube_detected_game(video.get('video_id'))
                if detected_game:
                    print(f"      🎮 YouTube detected: {detected_game}")
                    potential_names.append(detected_game)
                else:
                    print("      ❌ No YouTube game detection found")

                # Fallback to extracting game names from title
                title_names = self.game_inference.extract_potential_game_names_from_title(title)
                if title_names:
                    print(f"      📝 Title extracted: {title_names}")
                    potential_names.extend(title_names)

                if not potential_names:
                    print("      ❌ No potential game names found from YouTube or title")
                    continue

                print(f"      🎯 All potential names: {potential_names}")

                # Check if any potential names should skip Steam matching
                skip_games = self.config_manager.get_skip_steam_matching_games()
                should_skip_any = any(
                    any(skip_game.lower() in name.lower() for skip_game in skip_games)
                    for name in potential_names
                )

                if should_skip_any:
                    skipped_names = [name for name in potential_names
                                   if any(skip_game.lower() in name.lower() for skip_game in skip_games)]
                    print(f"      🚫 Steam matching skipped for {skipped_names} (in config skip list)")
                    continue

                # Search Steam for each potential name
                best_match = None

                for name in potential_names:
                    steam_match = self.find_steam_match_interactive(name, confidence_threshold=0.5)
                    if steam_match and (not best_match or steam_match['confidence'] > best_match['confidence']):
                            best_match = steam_match

                if best_match:
                    app_id = best_match['app_id']
                    game_name = best_match['name']
                    print(f"      ✅ Found match: {game_name} (App ID: {app_id}, confidence: {best_match['confidence']:.2f})")

                    # Update video data
                    video['steam_app_id'] = app_id
                    video['inferred_game'] = True  # Mark as inferred for review
                    video['inference_reason'] = reason
                    video['last_updated'] = datetime.now().isoformat()

                    # Store YouTube detection info if it was used
                    if detected_game:
                        video['youtube_detected_game'] = detected_game
                        if detected_game == best_match['name']:
                            video['youtube_detected_matched'] = True

                    # Fetch full game data
                    try:
                        steam_url = f"https://store.steampowered.com/app/{app_id}"
                        steam_data = self.fetch_steam_data(steam_url)
                        if steam_data:
                            steam_data = replace(steam_data, last_updated=datetime.now().isoformat())
                            self.steam_data['games'][app_id] = steam_data
                            print(f"      📊 Fetched game metadata: {steam_data.name}")
                    except Exception as e:
                        logging.error(f"      ❌ Error fetching Steam data for {app_id}: {e}")

                    games_found += 1
                    channel_games_found += 1
                    if reason == "missing_steam_game":
                        missing_resolved += 1
                        channel_missing_resolved += 1
                else:
                    print("      ❌ No confident matches found on Steam")

            # Save updated video data
            if channel_games_found > 0 or channel_missing_resolved > 0:
                with open(videos_file, 'w') as f:
                    json.dump(channel_data, f, indent=2, sort_keys=True)
                print(f"   💾 Saved {channel_games_found} game inferences and {channel_missing_resolved} resolved missing games for {channel_id}")

        # Save updated Steam data
        if games_found > 0 or missing_resolved > 0:
            self.save_steam()

        print("\n" + "="*80)
        print("GAME INFERENCE AND RESOLUTION SUMMARY")
        print("="*80)
        print(f"📊 Videos processed: {total_videos_processed}")
        print(f"🎮 New games found via inference: {games_found}")
        print(f"🔧 Missing Steam games resolved: {missing_resolved}")
        print(f"✅ Total games found/resolved: {games_found + missing_resolved}")
        if total_videos_processed > 0:
            success_rate = ((games_found + missing_resolved) / total_videos_processed) * 100
            print(f"📈 Success rate: {success_rate:.1f}%")
        if games_found > 0:
            print("\n⚠️  Note: Inferred games are marked with 'inferred_game: true' for review")
        if missing_resolved > 0:
            print("⚠️  Note: Some videos may have 'broken_app_id' field for depublished games")
        print("="*80)

        return games_found + missing_resolved


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube to Steam game scraper")
    parser.add_argument('mode', choices=['backfill', 'cron', 'reprocess', 'single-app', 'data-quality', 'infer-games'],
                        help='Processing mode: backfill (single channel), cron (all channels), reprocess (reprocess existing videos), single-app, data-quality, or infer-games')
    parser.add_argument('--channel', type=str, help='Channel ID for backfill/reprocess mode (optional for backfill - processes all channels if not specified)')
    parser.add_argument('--max-new', type=int, help='Maximum number of new videos to process')
    parser.add_argument('--max-steam-updates', type=int, help='Maximum number of Steam games to update')
    parser.add_argument('--app-id', type=str, help='Steam app ID to fetch (required for single-app mode)')
    parser.add_argument('--cutoff-date', type=str, help='Date cutoff for backfill mode (YYYY-MM-DD format) - only process videos after this date')
    args = parser.parse_args()

    if args.mode == 'reprocess':
        if not args.channel:
            print("Error: --channel is required for reprocess mode")
            sys.exit(1)

        scraper = YouTubeSteamScraper(args.channel)

        if not scraper.config_manager.validate_channel_exists(args.channel):
            print(f"Error: Channel '{args.channel}' not found in config.json")
            sys.exit(1)

        logging.info(f"Reprocess mode: reprocessing channel {args.channel}")
        scraper.reprocess_video_descriptions()

    elif args.mode == 'backfill':
        # Load config directly
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent
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

        # Update Steam data using SteamDataUpdater
        steam_updater = SteamDataUpdater()
        steam_updater.update_all_games_from_channels(
            channels_to_process,
            max_updates=args.max_steam_updates
        )

    elif args.mode == 'cron':
        # Load config directly
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent
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

        # Update Steam data once for all enabled channels
        if enabled_channels:
            steam_updater = SteamDataUpdater()
            steam_updater.update_all_games_from_channels(
                enabled_channels,
                max_updates=args.max_steam_updates
            )

    elif args.mode == 'single-app':
        if not args.app_id:
            print("Error: --app-id is required for single-app mode")
            sys.exit(1)

        # Use any channel for single-app mode (just need Steam data access)
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent
        config_manager = ConfigManager(project_root)
        channels = config_manager.get_channels()

        # Get first available channel
        first_channel = next(iter(channels.keys()))
        scraper = YouTubeSteamScraper(first_channel)

        # Use SteamDataUpdater for single app fetching
        steam_updater = SteamDataUpdater()
        if steam_updater.fetch_single_app(args.app_id, force_update=True):
            logging.info(f"Successfully fetched data for app {args.app_id}")
        else:
            logging.warning(f"Failed to fetch data for app {args.app_id}")

    elif args.mode == 'data-quality':
        # Load config directly
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent
        config_manager = ConfigManager(project_root)
        channels = config_manager.get_channels()

        # Use first available channel to access data files
        first_channel = next(iter(channels.keys()))
        scraper = YouTubeSteamScraper(first_channel)

        logging.info("Data quality check: analyzing all channels and games")
        scraper.check_data_quality(channels)

    elif args.mode == 'infer-games':
        # Load config directly
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent
        config_manager = ConfigManager(project_root)
        channels = config_manager.get_channels()

        # Use first available channel to access data files
        first_channel = next(iter(channels.keys()))
        scraper = YouTubeSteamScraper(first_channel)

        logging.info("Game inference: searching for games in video titles")
        scraper.infer_games_from_titles(channels)
