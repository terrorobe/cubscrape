#!/usr/bin/env python3
"""
YouTube Channel Video Scraper with Steam Game Data Integration
"""

import argparse
import json
import logging
import sys
from dataclasses import asdict, replace
from datetime import datetime, timedelta
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

    def process_videos(self, channel_url: str, max_new_videos: Optional[int] = None, fetch_newest_first: bool = False):
        """Process YouTube videos only"""
        logging.info(f"Processing videos from channel: {channel_url}")

        if not max_new_videos:
            max_new_videos = 50

        known_video_ids = set(self.videos_data['videos'].keys())
        new_videos_processed = 0
        batch_size = min(max_new_videos * 2, 50)  # Fetch more IDs to account for known videos
        videos_fetched_total = 0
        consecutive_known_batches = 0

        # Smart starting position: if we have videos and not fetching newest first, start from a reasonable offset
        if fetch_newest_first:
            smart_start_offset = 0  # Start from beginning (newest videos)
            logging.info("Fetching newest videos first (cron mode)")
        else:
            smart_start_offset = max(0, len(known_video_ids) - 10) if known_video_ids else 0
            if smart_start_offset > 0:
                logging.info(f"Smart start: skipping to position {smart_start_offset + 1} (have {len(known_video_ids)} videos)")

        videos_fetched_total = smart_start_offset

        while new_videos_processed < max_new_videos:
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
            else:
                consecutive_known_batches = 0

            # Second pass: fetch full metadata only for new videos
            logging.info(f"Found {len(new_videos_in_batch)} new videos, fetching full metadata")
            for video in new_videos_in_batch:
                video_id = video['video_id']

                if new_videos_processed >= max_new_videos:
                    break

                # Get full video metadata
                try:
                    full_video = self.get_full_video_metadata(video_id)
                    if full_video:
                        video_date = full_video.get('published_at', '')[:10] if full_video.get('published_at') else 'Unknown'
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

                # Try to find this game on Steam
                steam_match = self.find_steam_match(detected_game, confidence_threshold=0.6)
                if steam_match:
                    video_data = replace(video_data, steam_app_id=steam_match['app_id'], youtube_detected_matched=True)
                    logging.info(f"  Matched to Steam: {steam_match['name']} (App ID: {steam_match['app_id']}, confidence: {steam_match['confidence']:.2f})")
                else:
                    logging.info("  No confident Steam matches found for YouTube detected game")
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

    def _get_refresh_interval_days(self, game_data: SteamGameData) -> int:
        """Determine refresh interval based on game release age"""
        # Default to weekly if no release date available
        if not game_data.release_date or game_data.coming_soon:
            return 7  # Weekly for upcoming/unknown games

        try:
            # Parse the release date - Steam uses various formats
            release_date_str = game_data.release_date.strip()

            # Try to parse different date formats Steam uses
            release_date = None
            date_formats = [
                "%b %d, %Y",      # "Jan 1, 2023"
                "%B %d, %Y",      # "January 1, 2023"
                "%d %b, %Y",      # "1 Jan, 2023"
                "%d %B, %Y",      # "1 January, 2023"
                "%b %Y",          # "Jan 2023"
                "%B %Y",          # "January 2023"
                "%Y",             # "2023"
            ]

            for date_format in date_formats:
                try:
                    release_date = datetime.strptime(release_date_str, date_format)
                    break
                except ValueError:
                    continue

            if not release_date:
                logging.debug(f"Could not parse release date '{release_date_str}', using weekly refresh")
                return 7  # Weekly as fallback

            # Calculate age in days since release
            days_since_release = (datetime.now() - release_date).days

            # Apply refresh intervals based on age:
            # Less than a month old (30 days): daily
            # Less than a year old (365 days): weekly
            # Otherwise: monthly
            if days_since_release < 30:
                return 1  # Daily
            elif days_since_release < 365:
                return 7  # Weekly
            else:
                return 30  # Monthly

        except Exception as e:
            logging.debug(f"Error parsing release date '{game_data.release_date}': {e}, using weekly refresh")
            return 7  # Weekly as fallback

    def _should_update_related_app(self, app_id: str, force_update: bool) -> bool:
        """Check if a related app should be updated based on staleness."""
        if force_update:
            return True

        if app_id not in self.steam_data['games']:
            return True

        existing_data = self.steam_data['games'][app_id]
        if not existing_data.last_updated:
            return True

        last_updated_date = datetime.fromisoformat(existing_data.last_updated)
        refresh_interval = self._get_refresh_interval_days(existing_data)
        stale_date = datetime.now() - timedelta(days=refresh_interval)

        if last_updated_date > stale_date:
            days_ago = (datetime.now() - last_updated_date).days
            interval_name = "daily" if refresh_interval == 1 else "weekly" if refresh_interval == 7 else "monthly"
            logging.info(f"  Skipping {app_id} ({existing_data.name}) - updated {days_ago} days ago, {interval_name} refresh")
            return False

        return True

    def _fetch_related_app(self, app_id: str, app_type: str) -> bool:
        """
        Fetch data for a related app (demo or full game).
        
        Args:
            app_id: Steam app ID to fetch
            app_type: Type description for logging ("demo" or "full game")
            
        Returns:
            True if app was successfully fetched, False otherwise
        """
        try:
            app_url = f"https://store.steampowered.com/app/{app_id}"
            app_data = self.fetch_steam_data(app_url)
            if app_data:
                app_data = replace(app_data, last_updated=datetime.now().isoformat())
                self.steam_data['games'][app_id] = app_data
                logging.info(f"  Updated {app_type}: {app_data.name}")
                return True
            return False
        except Exception as e:
            logging.error(f"  Error fetching {app_type} data: {e}")
            return False

    def _fetch_steam_app_with_related(self, app_id: str, force_update: bool = False) -> bool:
        """
        Fetch Steam app data and automatically fetch related demo/full game data.
        
        Args:
            app_id: Steam app ID to fetch
            force_update: If True, skip staleness checks and always fetch
            
        Returns:
            True if any data was updated, False otherwise
        """
        steam_url = f"https://store.steampowered.com/app/{app_id}"
        if force_update:
            logging.info(f"Fetching single app: {app_id}")
        else:
            logging.info(f"Updating Steam data for app {app_id}")

        try:
            # Fetch the main app
            steam_data = self.fetch_steam_data(steam_url)
            if not steam_data:
                logging.warning(f"  Failed to fetch data for app {app_id}")
                return False

            # Update the main app data
            steam_data = replace(steam_data, last_updated=datetime.now().isoformat())
            self.steam_data['games'][app_id] = steam_data
            logging.info(f"  Updated: {steam_data.name}")
            updated = True

            # Handle demo -> full game relationship
            if steam_data.is_demo and steam_data.full_game_app_id:
                full_game_id = steam_data.full_game_app_id
                logging.info(f"  Found full game {full_game_id}, fetching data")

                if self._should_update_related_app(full_game_id, force_update):
                    self._fetch_related_app(full_game_id, "full game")

            # Handle main game -> demo relationship
            if steam_data.has_demo and steam_data.demo_app_id:
                demo_id = steam_data.demo_app_id
                logging.info(f"  Found demo {demo_id}, fetching data")

                if self._should_update_related_app(demo_id, force_update):
                    self._fetch_related_app(demo_id, "demo")

            return updated

        except Exception as e:
            logging.error(f"  Error fetching Steam data for {app_id}: {e}")
            return False

    def update_steam_data(self, max_updates: Optional[int] = None):
        """Update Steam data using age-based refresh intervals"""
        logging.info("Updating Steam data using age-based refresh intervals")

        # Collect all Steam app IDs from videos
        steam_app_ids = set()
        for video in self.videos_data['videos'].values():
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
            if app_id in self.steam_data['games']:
                game_data = self.steam_data['games'][app_id]
                if game_data.last_updated:
                    last_updated_date = datetime.fromisoformat(game_data.last_updated)
                    refresh_interval_days = self._get_refresh_interval_days(game_data)
                    stale_date = datetime.now() - timedelta(days=refresh_interval_days)

                    if last_updated_date > stale_date:
                        days_ago = (datetime.now() - last_updated_date).days
                        interval_name = "daily" if refresh_interval_days == 1 else "weekly" if refresh_interval_days == 7 else "monthly"
                        logging.info(f"Skipping app {app_id} ({game_data.name}) - updated {days_ago} days ago, {interval_name} refresh")
                        continue

            # Use the consolidated fetch method (force_update=False for staleness checking)
            if self._fetch_steam_app_with_related(app_id, force_update=False):
                updates_done += 1

        self.save_steam()
        logging.info(f"Steam data update complete. Updated {updates_done} games.")

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
                    json.dump(channel_data, f, indent=2)
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
    parser.add_argument('--channel', type=str, help='Channel ID for backfill mode')
    parser.add_argument('--max-new', type=int, help='Maximum number of new videos to process')
    parser.add_argument('--max-steam-updates', type=int, help='Maximum number of Steam games to update')
    parser.add_argument('--app-id', type=str, help='Steam app ID to fetch (required for single-app mode)')
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
        if not args.channel:
            print("Error: --channel is required for backfill mode")
            sys.exit(1)

        scraper = YouTubeSteamScraper(args.channel)

        if not scraper.config_manager.validate_channel_exists(args.channel):
            print(f"Error: Channel '{args.channel}' not found in config.json")
            sys.exit(1)

        channel_url = scraper.config_manager.get_channel_url(args.channel)
        logging.info(f"Backfill mode: processing channel {args.channel}")

        scraper.process_videos(channel_url, max_new_videos=args.max_new)
        scraper.update_steam_data(
            max_updates=args.max_steam_updates
        )

    elif args.mode == 'cron':
        # Load config directly
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent
        config_manager = ConfigManager(project_root)
        channels = config_manager.get_channels()

        # Process each enabled channel
        steam_scraper = None
        for channel_id in channels:
            if not config_manager.is_channel_enabled(channel_id):
                logging.info(f"Skipping disabled channel: {channel_id}")
                continue

            logging.info(f"Cron mode: processing channel {channel_id}")
            scraper = YouTubeSteamScraper(channel_id)

            # Process recent videos only (smaller batch for cron) - fetch newest first
            channel_url = config_manager.get_channel_url(channel_id)
            scraper.process_videos(channel_url, max_new_videos=10, fetch_newest_first=True)

            # Keep one scraper for Steam updates
            if steam_scraper is None:
                steam_scraper = scraper

        # Update Steam data once for all channels
        if steam_scraper:
            steam_scraper.update_steam_data(
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

        # Use the consolidated fetch method with force_update=True for single-app mode
        if scraper._fetch_steam_app_with_related(args.app_id, force_update=True):
            scraper.save_steam()
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
