#!/usr/bin/env python3
"""
YouTube Channel Video Scraper with Steam Game Data Integration
"""

import argparse
import json
import logging
import re
import sys
from dataclasses import asdict, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests
import yt_dlp
from crazygames_fetcher import CrazyGamesDataFetcher
from itch_fetcher import ItchDataFetcher
from models import OtherGameData, SteamGameData, VideoData
from steam_fetcher import SteamDataFetcher
from utils import extract_game_links, extract_potential_game_names, extract_steam_app_id, load_json, save_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class YouTubeSteamScraper:
    def __init__(self, channel_id: str):
        # Get the directory of this script, then build paths relative to project root
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent

        # Load config
        self.config = self.load_config()

        # Set up file paths
        self.videos_file = project_root / 'data' / f'videos-{channel_id}.json'
        self.steam_file = project_root / 'data' / 'steam_games.json'
        self.other_games_file = project_root / 'data' / 'other_games.json'

        videos_raw = load_json(self.videos_file, {'videos': {}, 'last_updated': None})
        # Convert loaded dictionaries to VideoData objects
        self.videos_data = {
            'videos': {vid: self._dict_to_video_data(vdata) if isinstance(vdata, dict) else vdata
                      for vid, vdata in videos_raw['videos'].items()},
            'last_updated': videos_raw.get('last_updated')
        }
        steam_raw = load_json(self.steam_file, {'games': {}, 'last_updated': None})
        # Convert loaded dictionaries to SteamGameData objects
        self.steam_data = {
            'games': {app_id: self._dict_to_steam_data(sdata) if isinstance(sdata, dict) else sdata
                     for app_id, sdata in steam_raw['games'].items()},
            'last_updated': steam_raw.get('last_updated')
        }
        other_games_raw = load_json(self.other_games_file, {'games': {}, 'last_updated': None})
        # Convert loaded dictionaries to OtherGameData objects
        self.other_games_data = {
            'games': {game_id: self._dict_to_other_game_data(gdata) if isinstance(gdata, dict) else gdata
                     for game_id, gdata in other_games_raw['games'].items()},
            'last_updated': other_games_raw.get('last_updated')
        }

        # Store channel info
        self.channel_id = channel_id

        # Initialize fetchers
        self.steam_fetcher = SteamDataFetcher()
        self.itch_fetcher = ItchDataFetcher()
        self.crazygames_fetcher = CrazyGamesDataFetcher()

        # yt-dlp options
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'force_generic_extractor': False,
        }

    def load_config(self) -> Dict:
        """Load configuration from config.json"""
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent
        config_path = project_root / 'config.json'

        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
        return {'channels': {}}

    def _dict_to_video_data(self, video_dict: Dict) -> VideoData:
        """Convert dictionary to VideoData object"""
        return VideoData(**video_dict)

    def _dict_to_steam_data(self, steam_dict: Dict) -> SteamGameData:
        """Convert dictionary to SteamGameData object"""
        return SteamGameData(**steam_dict)

    def _dict_to_other_game_data(self, game_dict: Dict) -> OtherGameData:
        """Convert dictionary to OtherGameData object"""
        return OtherGameData(**game_dict)

    def _clean_dict_for_json(self, data_dict: Dict) -> Dict:
        """Remove None values and False boolean values to keep JSON clean"""
        return {k: v for k, v in data_dict.items() if v is not None and v is not False}

    def save_videos(self):
        """Save video data to JSON file"""
        # Convert VideoData objects to dictionaries for JSON serialization
        videos_dict = {}
        for video_id, video_data in self.videos_data['videos'].items():
            if isinstance(video_data, VideoData):
                video_dict = asdict(video_data)
                # Remove None values and False boolean values to keep JSON clean
                video_dict = self._clean_dict_for_json(video_dict)
                videos_dict[video_id] = video_dict
            else:
                videos_dict[video_id] = video_data

        data_to_save = {
            'videos': videos_dict,
            'last_updated': self.videos_data.get('last_updated')
        }
        save_data(data_to_save, self.videos_file)

    def save_steam(self):
        """Save Steam data to JSON file"""
        # Convert SteamGameData objects to dictionaries for JSON serialization
        games_dict = {}
        for app_id, game_data in self.steam_data['games'].items():
            if isinstance(game_data, SteamGameData):
                game_dict = asdict(game_data)
                # Remove None values and False boolean values to keep JSON clean
                game_dict = self._clean_dict_for_json(game_dict)
                games_dict[app_id] = game_dict
            else:
                games_dict[app_id] = game_data

        data_to_save = {
            'games': games_dict,
            'last_updated': self.steam_data.get('last_updated')
        }
        save_data(data_to_save, self.steam_file)

    def save_other_games(self):
        """Save other games data to JSON file"""
        # Convert OtherGameData objects to dictionaries for JSON serialization
        games_dict = {}
        for game_id, game_data in self.other_games_data['games'].items():
            if isinstance(game_data, OtherGameData):
                game_dict = asdict(game_data)
                # Remove None values and False boolean values to keep JSON clean
                game_dict = self._clean_dict_for_json(game_dict)
                games_dict[game_id] = game_dict
            else:
                games_dict[game_id] = game_data

        data_to_save = {
            'games': games_dict,
            'last_updated': self.other_games_data.get('last_updated')
        }
        save_data(data_to_save, self.other_games_file)


    def extract_youtube_detected_game(self, video_id: str) -> Optional[str]:
        """Extract YouTube's detected game from JSON data as last resort"""
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                return None

            page_content = response.text

            # Look for YouTube's initial data JSON
            pattern = r'var ytInitialData = ({.*?});'
            match = re.search(pattern, page_content)
            if not match:
                return None

            data = json.loads(match.group(1))

            # Navigate to the rich metadata renderer
            try:
                contents = data['contents']['twoColumnWatchNextResults']['results']['results']['contents']
                for content in contents:
                    if 'videoSecondaryInfoRenderer' in content:
                        metadata_container = content['videoSecondaryInfoRenderer'].get('metadataRowContainer', {})
                        rows = metadata_container.get('metadataRowContainerRenderer', {}).get('rows', [])

                        for row in rows:
                            if 'richMetadataRowRenderer' in row:
                                rich_contents = row['richMetadataRowRenderer'].get('contents', [])
                                for rich_content in rich_contents:
                                    if 'richMetadataRenderer' in rich_content:
                                        title = rich_content['richMetadataRenderer'].get('title', {})
                                        if 'simpleText' in title:
                                            game_title = title['simpleText'].strip()
                                            if game_title and len(game_title) > 3:
                                                return game_title
            except (KeyError, TypeError):
                pass

            return None

        except Exception as e:
            logging.debug(f"Error extracting YouTube detected game for {video_id}: {e}")
            return None

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
        videos = []

        # Use playlist start/end to simulate offset
        ydl_opts_lightweight = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'force_generic_extractor': False,
            'playliststart': skip_count + 1,
            'playlistend': skip_count + batch_size
        }

        with yt_dlp.YoutubeDL(ydl_opts_lightweight) as ydl:
            try:
                logging.info(f"Fetching lightweight data from {channel_url}")
                info = ydl.extract_info(channel_url, download=False)

                if 'entries' in info:
                    entries = info['entries']
                else:
                    entries = [info] if info else []

                # Process entries - just extract basic info
                for entry in entries:
                    if not entry:
                        continue

                    video_id = entry.get('id')
                    if not video_id:
                        continue

                    videos.append({
                        'video_id': video_id,
                        'title': entry.get('title', ''),
                        'published_at': datetime.fromtimestamp(
                            entry.get('timestamp', 0)
                        ).isoformat() if entry.get('timestamp') and entry.get('timestamp') > 0 else None,
                        'thumbnail': entry.get('thumbnail', '')
                    })

            except Exception as e:
                logging.error(f"Error fetching lightweight channel videos: {e}")

        return videos

    def get_full_video_metadata(self, video_id: str) -> Optional[Dict]:
        """Fetch full metadata for a specific video"""
        try:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                video_info = ydl.extract_info(video_url, download=False)

                return {
                    'video_id': video_id,
                    'title': video_info.get('title', ''),
                    'description': video_info.get('description', ''),
                    'published_at': datetime.fromtimestamp(
                        video_info.get('timestamp', 0)
                    ).isoformat() if video_info.get('timestamp') else '',
                    'thumbnail': video_info.get('thumbnail', '')
                }
        except Exception as e:
            error_msg = str(e)
            if "This video is available to this channel's members" in error_msg:
                logging.info(f"Skipping member-only video {video_id}")
            elif "Private video" in error_msg or "Video unavailable" in error_msg:
                logging.info(f"Skipping unavailable video {video_id}")
            else:
                logging.error(f"Error fetching full metadata for video {video_id}: {e}")
            return None

    def update_steam_data(self, days_stale: int = 7, max_updates: Optional[int] = None):
        """Update Steam data for games that haven't been updated recently"""
        logging.info(f"Updating Steam data (stale after {days_stale} days)")

        # Collect all Steam app IDs from videos
        steam_app_ids = set()
        for video in self.videos_data['videos'].values():
            if video.steam_app_id:
                steam_app_ids.add(video.steam_app_id)

        logging.info(f"Found {len(steam_app_ids)} unique Steam games")

        updates_done = 0
        stale_date = datetime.now() - timedelta(days=days_stale)

        for app_id in steam_app_ids:
            # Check if we've hit the max updates limit
            if max_updates and updates_done >= max_updates:
                logging.info(f"Reached max_updates limit ({max_updates})")
                break

            # Check if data is stale
            if app_id in self.steam_data['games']:
                game_data = self.steam_data['games'][app_id]
                if game_data.last_updated:
                    last_updated_date = datetime.fromisoformat(game_data.last_updated)
                    if last_updated_date > stale_date:
                        days_ago = (datetime.now() - last_updated_date).days
                        logging.info(f"Skipping app {app_id} ({game_data.name}) - updated {days_ago} days ago")
                        continue

            # Fetch/update Steam data
            steam_url = f"https://store.steampowered.com/app/{app_id}"
            logging.info(f"Updating Steam data for app {app_id}")

            try:
                steam_data = self.fetch_steam_data(steam_url)
                if steam_data:
                    # Update the last_updated timestamp
                    steam_data = replace(steam_data, last_updated=datetime.now().isoformat())
                    self.steam_data['games'][app_id] = steam_data
                    logging.info(f"  Updated: {steam_data.name}")
                    updates_done += 1

                    # If this is a demo and we found a full game, fetch that too
                    if steam_data.is_demo and steam_data.full_game_app_id:
                        full_game_id = steam_data.full_game_app_id
                        logging.info(f"  Found full game {full_game_id}, fetching data")

                        # Check if we need to update the full game (same staleness logic)
                        should_update_full = True
                        if full_game_id in self.steam_data['games']:
                            existing_data = self.steam_data['games'][full_game_id]
                            if existing_data.last_updated:
                                last_updated_date = datetime.fromisoformat(existing_data.last_updated)
                                if last_updated_date > stale_date:
                                    should_update_full = False
                                    days_ago = (datetime.now() - last_updated_date).days
                                    logging.info(f"  Skipping full game {full_game_id} ({existing_data.name}) - updated {days_ago} days ago")

                        if should_update_full:
                            try:
                                full_game_url = f"https://store.steampowered.com/app/{full_game_id}"
                                full_game_data = self.fetch_steam_data(full_game_url)
                                if full_game_data:
                                    full_game_data = replace(full_game_data, last_updated=datetime.now().isoformat())
                                    self.steam_data['games'][full_game_id] = full_game_data
                                    logging.info(f"  Updated full game: {full_game_data.name}")
                            except Exception as e:
                                logging.error(f"  Error fetching full game data: {e}")

                    # If this is a main game and we found a demo, fetch that too
                    if steam_data.has_demo and steam_data.demo_app_id:
                        demo_id = steam_data.demo_app_id
                        logging.info(f"  Found demo {demo_id}, fetching data")

                        # Check if we need to update the demo (same staleness logic)
                        should_update_demo = True
                        if demo_id in self.steam_data['games']:
                            existing_demo = self.steam_data['games'][demo_id]
                            if existing_demo.last_updated:
                                last_updated_date = datetime.fromisoformat(existing_demo.last_updated)
                                if last_updated_date > stale_date:
                                    should_update_demo = False
                                    days_ago = (datetime.now() - last_updated_date).days
                                    logging.info(f"  Skipping demo {demo_id} ({existing_demo.name}) - updated {days_ago} days ago")

                        if should_update_demo:
                            try:
                                demo_url = f"https://store.steampowered.com/app/{demo_id}"
                                demo_data = self.fetch_steam_data(demo_url)
                                if demo_data:
                                    demo_data = replace(demo_data, last_updated=datetime.now().isoformat())
                                    self.steam_data['games'][demo_id] = demo_data
                                    logging.info(f"  Updated demo: {demo_data.name}")
                            except Exception as e:
                                logging.error(f"  Error fetching demo data: {e}")
                else:
                    logging.warning(f"  Failed to fetch data for app {app_id}")
            except Exception as e:
                logging.error(f"  Error fetching Steam data: {e}")

        self.save_steam()
        logging.info(f"Steam data update complete. Updated {updates_done} games.")

    def check_data_quality(self, channels_config: Dict):
        """Check data quality across all channels and games"""
        print("\n" + "="*80)
        print("DATA QUALITY REPORT")
        print("="*80)

        total_issues = 0

        # 1. Check for videos with missing game data
        print("\n1. CHECKING VIDEOS WITH MISSING GAME DATA")
        print("-" * 50)

        videos_missing_games = 0
        videos_with_games = 0

        # Load all channel video files
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent

        for channel_id in channels_config:
            videos_file = project_root / 'data' / f'videos-{channel_id}.json'
            if not videos_file.exists():
                print(f"⚠️  Missing video file for channel {channel_id}: {videos_file}")
                total_issues += 1
                continue

            with open(videos_file) as f:
                channel_data = json.load(f)

            channel_videos_missing = 0
            channel_videos_with_games = 0

            for video_id, video in channel_data.get('videos', {}).items():
                has_game = bool(video.get('steam_app_id') or video.get('itch_url') or video.get('crazygames_url'))

                if has_game:
                    videos_with_games += 1
                    channel_videos_with_games += 1
                else:
                    videos_missing_games += 1
                    channel_videos_missing += 1
                    if channel_videos_missing <= 5:  # Show first 5 examples
                        print(f"   📺 {channel_id}: '{video.get('title', 'Unknown')}' (ID: {video_id})")

            if channel_videos_missing > 5:
                print(f"   ... and {channel_videos_missing - 5} more videos in {channel_id}")

            print(f"Channel {channel_id}: {channel_videos_with_games} with games, {channel_videos_missing} without")

        print(f"\nSUMMARY: {videos_with_games} videos with games, {videos_missing_games} videos without games")
        if videos_missing_games > 0:
            percentage = (videos_missing_games / (videos_with_games + videos_missing_games)) * 100
            print(f"📊 {percentage:.1f}% of videos are missing game data")
            total_issues += videos_missing_games

        # 2. Check for missing Steam games referenced in videos
        print("\n\n2. CHECKING FOR MISSING STEAM GAMES")
        print("-" * 50)

        # Collect all Steam app IDs referenced in videos
        referenced_steam_apps = set()
        for channel_id in channels_config:
            videos_file = project_root / 'data' / f'videos-{channel_id}.json'
            if videos_file.exists():
                with open(videos_file) as f:
                    channel_data = json.load(f)

                for _video_id, video in channel_data.get('videos', {}).items():
                    steam_app_id = video.get('steam_app_id')
                    if steam_app_id:
                        referenced_steam_apps.add(steam_app_id)

        # Check which referenced Steam games are missing from our database
        missing_steam_games = []
        for app_id in referenced_steam_apps:
            if app_id not in self.steam_data.get('games', {}):
                missing_steam_games.append(app_id)

        if missing_steam_games:
            print(f"❌ Found {len(missing_steam_games)} Steam games referenced in videos but missing from database:")
            for _i, app_id in enumerate(missing_steam_games[:10]):  # Show first 10
                print(f"   🎮 Steam App ID: {app_id} (https://store.steampowered.com/app/{app_id})")

            if len(missing_steam_games) > 10:
                print(f"   ... and {len(missing_steam_games) - 10} more missing Steam games")

            total_issues += len(missing_steam_games)
            print(f"\n📊 {len(missing_steam_games)} out of {len(referenced_steam_apps)} referenced Steam games are missing ({(len(missing_steam_games)/len(referenced_steam_apps)*100):.1f}%)")
        else:
            print("✅ All referenced Steam games have metadata in database")

        print(f"Total referenced Steam games: {len(referenced_steam_apps)}")
        print(f"Steam games in database: {len(self.steam_data.get('games', {}))}")

        # 3. Check Steam games for missing metadata
        print("\n\n3. CHECKING STEAM GAMES METADATA")
        print("-" * 50)

        steam_issues = 0
        required_steam_fields = ['name', 'steam_app_id', 'tags', 'positive_review_percentage']
        optional_steam_fields = ['header_image', 'review_summary', 'price']

        for app_id, game in self.steam_data.get('games', {}).items():
            missing_required = []
            missing_optional = []

            # Check required fields, but skip positive_review_percentage for coming soon games
            for field in required_steam_fields:
                if not getattr(game, field, None):
                    # Coming soon games legitimately don't have review data
                    if field == 'positive_review_percentage' and game.coming_soon:
                        continue
                    # Games with insufficient reviews also legitimately don't have percentage scores
                    if field == 'positive_review_percentage' and game.insufficient_reviews:
                        continue
                    # Games with no reviews also legitimately don't have percentage scores
                    if field == 'positive_review_percentage' and game.review_count == 0:
                        continue
                    missing_required.append(field)

            for field in optional_steam_fields:
                if not getattr(game, field, None):
                    # Coming soon games legitimately don't have price or review data
                    if game.coming_soon and field in ['review_summary', 'price']:
                        continue
                    missing_optional.append(field)

            if missing_required:
                print(f"❌ Steam game {app_id} ({game.name}) missing required: {', '.join(missing_required)}")
                steam_issues += 1
                total_issues += 1
            elif missing_optional:
                print(f"⚠️  Steam game {app_id} ({game.name}) missing optional: {', '.join(missing_optional)}")

        # Count coming soon games and insufficient reviews for informational purposes
        coming_soon_count = sum(1 for game in self.steam_data.get('games', {}).values() if game.coming_soon)
        insufficient_reviews_count = sum(1 for game in self.steam_data.get('games', {}).values() if game.insufficient_reviews)
        no_reviews_count = sum(1 for game in self.steam_data.get('games', {}).values() if game.review_count == 0)

        print(f"\nSteam games checked: {len(self.steam_data.get('games', {}))}")
        print(f"Coming soon games (no reviews expected): {coming_soon_count}")
        if insufficient_reviews_count > 0:
            print(f"Games with insufficient reviews for score: {insufficient_reviews_count}")
        if no_reviews_count > 0:
            print(f"Games with no reviews yet: {no_reviews_count}")
        if steam_issues == 0:
            print("✅ All Steam games have required metadata")
        else:
            print(f"❌ {steam_issues} Steam games have missing required metadata")

        # 4. Check other games (Itch.io, CrazyGames) for missing metadata
        print("\n\n4. CHECKING OTHER GAMES METADATA")
        print("-" * 50)

        other_issues = 0
        required_other_fields = ['name', 'platform', 'tags']
        optional_other_fields = ['header_image', 'positive_review_percentage', 'review_count']

        for _url, game in self.other_games_data.get('games', {}).items():
            missing_required = []
            missing_optional = []

            for field in required_other_fields:
                value = getattr(game, field, None)
                if not value or (field == 'tags' and len(value) == 0):
                    missing_required.append(field)

            for field in optional_other_fields:
                if not getattr(game, field, None):
                    missing_optional.append(field)

            if missing_required:
                print(f"❌ {game.platform} game '{game.name}' missing required: {', '.join(missing_required)}")
                other_issues += 1
                total_issues += 1
            elif missing_optional:
                print(f"⚠️  {game.platform} game '{game.name}' missing optional: {', '.join(missing_optional)}")

        print(f"\nOther games checked: {len(self.other_games_data.get('games', {}))}")
        if other_issues == 0:
            print("✅ All other games have required metadata")
        else:
            print(f"❌ {other_issues} other games have missing required metadata")

        # 5. Check for stale data
        print("\n\n5. CHECKING FOR STALE DATA")
        print("-" * 50)

        stale_threshold = datetime.now() - timedelta(days=30)  # 30 days
        stale_steam = 0
        stale_other = 0

        for app_id, game in self.steam_data.get('games', {}).items():
            if game.last_updated:
                try:
                    last_updated_date = datetime.fromisoformat(game.last_updated)
                    if last_updated_date < stale_threshold:
                        days_old = (datetime.now() - last_updated_date).days
                        print(f"🕐 Steam game {app_id} ({game.name}) is {days_old} days old")
                        stale_steam += 1
                except ValueError:
                    print(f"❌ Steam game {app_id} has invalid last_updated format: {game.last_updated}")
                    total_issues += 1

        for _url, game in self.other_games_data.get('games', {}).items():
            last_updated = game.last_updated
            if last_updated:
                try:
                    last_updated_date = datetime.fromisoformat(last_updated)
                    if last_updated_date < stale_threshold:
                        days_old = (datetime.now() - last_updated_date).days
                        print(f"🕐 {game.platform} game '{game.name}' is {days_old} days old")
                        stale_other += 1
                except ValueError:
                    print(f"❌ {game.platform} game has invalid last_updated format: {last_updated}")
                    total_issues += 1

        if stale_steam == 0 and stale_other == 0:
            print("✅ No stale game data found")
        else:
            print(f"📊 {stale_steam} Steam games and {stale_other} other games are older than 30 days")

        # 6. Summary
        print("\n\n" + "="*80)
        print("SUMMARY")
        print("="*80)

        print(f"📊 Total videos: {videos_with_games + videos_missing_games}")
        print(f"📊 Videos with games: {videos_with_games}")
        print(f"📊 Videos without games: {videos_missing_games}")
        print(f"📊 Steam games: {len(self.steam_data.get('games', {}))}")
        print(f"📊 Other games: {len(self.other_games_data.get('games', {}))}")
        print(f"📊 Stale Steam games (>30 days): {stale_steam}")
        print(f"📊 Stale other games (>30 days): {stale_other}")

        if total_issues == 0:
            print("\n✅ DATA QUALITY: EXCELLENT - No critical issues found!")
        elif total_issues <= 5:
            print(f"\n⚠️  DATA QUALITY: GOOD - {total_issues} minor issues found")
        elif total_issues <= 20:
            print(f"\n⚠️  DATA QUALITY: FAIR - {total_issues} issues found")
        else:
            print(f"\n❌ DATA QUALITY: POOR - {total_issues} issues found")

        print("="*80)
        return total_issues

    def search_steam_games(self, query: str) -> List[Dict]:
        """Search Steam for games by name"""
        url = "https://store.steampowered.com/api/storesearch/"
        params = {
            'term': query,
            'l': 'english',
            'cc': 'US'
        }

        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get('items', [])
        except Exception as e:
            logging.error(f"Error searching Steam for '{query}': {e}")

        return []

    def find_steam_match(self, game_name: str, confidence_threshold: float = 0.5) -> Optional[Dict]:
        """Find best Steam match for a game name with confidence scoring"""
        try:
            results = self.search_steam_games(game_name)
            if not results:
                return None

            best_match = None
            best_confidence = 0

            for result in results[:3]:  # Check top 3 results
                steam_game_name = result['name'].lower()
                search_name = game_name.lower()

                # Calculate similarity (simple word overlap)
                search_words = set(search_name.split())
                game_words = set(steam_game_name.split())
                overlap = len(search_words & game_words)
                confidence = overlap / max(len(search_words), len(game_words))

                if confidence > best_confidence and confidence > confidence_threshold:
                    best_match = result
                    best_confidence = confidence

            if best_match:
                return {
                    'app_id': str(best_match['id']),
                    'name': best_match['name'],
                    'confidence': best_confidence
                }

            return None

        except Exception as e:
            logging.error(f"Error finding Steam match for '{game_name}': {e}")
            return None

    def find_steam_match_interactive(self, game_name: str, confidence_threshold: float = 0.5) -> Optional[Dict]:
        """Find Steam match with interactive prompting for low confidence results"""
        try:
            results = self.search_steam_games(game_name)
            if not results:
                print(f"      ❌ No Steam search results for '{game_name}'")
                return None

            best_match = None
            best_confidence = 0
            low_confidence_matches = []

            # Check all results
            for result in results[:5]:  # Check top 5 instead of 3
                steam_game_name = result['name']
                search_name = game_name.lower()

                # Calculate similarity (same logic as find_steam_match)
                search_words = set(search_name.split())
                game_words = set(steam_game_name.lower().split())
                overlap = len(search_words & game_words)
                confidence = overlap / max(len(search_words), len(game_words))

                if confidence >= confidence_threshold:
                    if confidence > best_confidence:
                        best_match = result
                        best_confidence = confidence
                elif confidence >= 0.3:  # Low confidence but potentially valid
                    low_confidence_matches.append((result, confidence))

            # If we found a high confidence match, return it
            if best_match:
                return {
                    'app_id': str(best_match['id']),
                    'name': best_match['name'],
                    'confidence': best_confidence
                }

            # If no high confidence matches, prompt for low confidence ones
            if low_confidence_matches:
                print(f"      🤔 Found potential matches for '{game_name}' (low confidence):")
                for i, (result, conf) in enumerate(low_confidence_matches):
                    print(f"         {i+1}. {result['name']} (confidence: {conf:.2f})")

                print("         0. None of these / Skip")

                while True:
                    try:
                        choice = input(f"      Select match (0-{len(low_confidence_matches)}): ").strip()
                        choice_num = int(choice)

                        if choice_num == 0:
                            return None
                        elif 1 <= choice_num <= len(low_confidence_matches):
                            selected = low_confidence_matches[choice_num - 1]
                            return {
                                'app_id': str(selected[0]['id']),
                                'name': selected[0]['name'],
                                'confidence': selected[1]
                            }
                        else:
                            print("      Invalid choice, try again.")
                    except (ValueError, KeyboardInterrupt):
                        print("      Skipping this match...")
                        return None

            return None

        except Exception as e:
            logging.error(f"Error finding Steam match for '{game_name}': {e}")
            return None


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
        url = f"https://store.steampowered.com/app/{app_id}"
        try:
            response = requests.head(url, timeout=5)
            if response.status_code == 404:
                return "depublished"
            elif response.status_code == 200:
                return "available"
            else:
                return "unknown"
        except Exception:
            return "unknown"

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
                    print(f"\n   📹 {title} [MISSING STEAM: {video.get('steam_app_id')}]")

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
                    print(f"\n   📹 {title}")

                # Extract potential game names (for both no_game_data and failed missing_steam_game cases)
                potential_names = extract_potential_game_names(title)
                if not potential_names:
                    print("      ❌ No potential game names found in title")
                    continue

                print(f"      🎯 Potential names: {potential_names}")

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
    parser.add_argument('--steam-stale-days', type=int, default=7,
                        help='Consider Steam data stale after this many days (default: 7)')
    parser.add_argument('--app-id', type=str, help='Steam app ID to fetch (required for single-app mode)')
    args = parser.parse_args()

    if args.mode == 'reprocess':
        if not args.channel:
            print("Error: --channel is required for reprocess mode")
            sys.exit(1)

        scraper = YouTubeSteamScraper(args.channel)

        if args.channel not in scraper.config['channels']:
            print(f"Error: Channel '{args.channel}' not found in config.json")
            sys.exit(1)

        logging.info(f"Reprocess mode: reprocessing channel {args.channel}")
        scraper.reprocess_video_descriptions()

    elif args.mode == 'backfill':
        if not args.channel:
            print("Error: --channel is required for backfill mode")
            sys.exit(1)

        scraper = YouTubeSteamScraper(args.channel)

        if args.channel not in scraper.config['channels']:
            print(f"Error: Channel '{args.channel}' not found in config.json")
            sys.exit(1)

        channel_url = scraper.config['channels'][args.channel]['url']
        logging.info(f"Backfill mode: processing channel {args.channel}")

        scraper.process_videos(channel_url, max_new_videos=args.max_new)
        scraper.update_steam_data(
            days_stale=args.steam_stale_days,
            max_updates=args.max_steam_updates
        )

    elif args.mode == 'cron':
        # Load config directly
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent
        config_path = project_root / 'config.json'

        with open(config_path) as f:
            config = json.load(f)

        # Process each enabled channel
        steam_scraper = None
        for channel_id, channel_config in config['channels'].items():
            if not channel_config.get('enabled', True):
                logging.info(f"Skipping disabled channel: {channel_id}")
                continue

            logging.info(f"Cron mode: processing channel {channel_id}")
            scraper = YouTubeSteamScraper(channel_id)

            # Process recent videos only (smaller batch for cron) - fetch newest first
            scraper.process_videos(channel_config['url'], max_new_videos=10, fetch_newest_first=True)

            # Keep one scraper for Steam updates
            if steam_scraper is None:
                steam_scraper = scraper

        # Update Steam data once for all channels
        if steam_scraper:
            steam_scraper.update_steam_data(
                days_stale=args.steam_stale_days,
                max_updates=args.max_steam_updates
            )

    elif args.mode == 'single-app':
        if not args.app_id:
            print("Error: --app-id is required for single-app mode")
            sys.exit(1)

        # Use any channel for single-app mode (just need Steam data access)
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent
        config_path = project_root / 'config.json'

        with open(config_path) as f:
            config = json.load(f)

        # Get first available channel
        first_channel = next(iter(config['channels'].keys()))
        scraper = YouTubeSteamScraper(first_channel)

        steam_url = f"https://store.steampowered.com/app/{args.app_id}"
        logging.info(f"Fetching single app: {args.app_id}")

        try:
            steam_data = scraper.fetch_steam_data(steam_url)
            if steam_data:
                steam_data = replace(steam_data, last_updated=datetime.now().isoformat())
                scraper.steam_data['games'][args.app_id] = steam_data
                scraper.save_steam()
                logging.info(f"Updated: {steam_data.name}")
            else:
                logging.warning(f"Failed to fetch data for app {args.app_id}")
        except Exception as e:
            logging.error(f"Error fetching app {args.app_id}: {e}")

    elif args.mode == 'data-quality':
        # Load config directly
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent
        config_path = project_root / 'config.json'

        with open(config_path) as f:
            config = json.load(f)

        # Use first available channel to access data files
        first_channel = next(iter(config['channels'].keys()))
        scraper = YouTubeSteamScraper(first_channel)

        logging.info("Data quality check: analyzing all channels and games")
        scraper.check_data_quality(config['channels'])

    elif args.mode == 'infer-games':
        # Load config directly
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent
        config_path = project_root / 'config.json'

        with open(config_path) as f:
            config = json.load(f)

        # Use first available channel to access data files
        first_channel = next(iter(config['channels'].keys()))
        scraper = YouTubeSteamScraper(first_channel)

        logging.info("Game inference: searching for games in video titles")
        scraper.infer_games_from_titles(config['channels'])
