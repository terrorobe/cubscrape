#!/usr/bin/env python3
"""
YouTube Channel Video Scraper with Steam Game Data Integration - Refactored Version
"""

import json
import re
import os
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
import yt_dlp

# Import our new modular components
from .models import GameLinks
from .utils import (
    extract_game_links, 
    calculate_name_similarity,
    load_json, 
    save_data,
    extract_steam_app_id
)
from .steam_fetcher import SteamDataFetcher
from .itch_fetcher import ItchDataFetcher
from .crazygames_fetcher import CrazyGamesDataFetcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class YouTubeSteamScraperRefactored:
    """Refactored YouTube to Steam scraper with modular components"""
    
    def __init__(self, channel_id: str):
        # File paths setup
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        
        self.config = self._load_config(project_root)
        self.channel_id = channel_id
        
        # Data file paths
        self.videos_file = os.path.join(project_root, 'data', f'videos-{channel_id}.json')
        self.steam_file = os.path.join(project_root, 'data', 'steam_games.json')
        self.other_games_file = os.path.join(project_root, 'data', 'other_games.json')
        
        # Load existing data
        self.videos_data = load_json(self.videos_file, {'videos': {}, 'last_updated': None})
        self.steam_data = load_json(self.steam_file, {'games': {}, 'last_updated': None})
        self.other_games_data = load_json(self.other_games_file, {'games': {}, 'last_updated': None})
        
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
    
    def _load_config(self, project_root: str) -> Dict:
        """Load configuration from config.json"""
        config_path = os.path.join(project_root, 'config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        return {'channels': {}}
    
    def save_videos(self):
        """Save video data to JSON file"""
        save_data(self.videos_data, self.videos_file)
    
    def save_steam(self):
        """Save Steam data to JSON file"""
        save_data(self.steam_data, self.steam_file)
    
    def save_other_games(self):
        """Save other games data to JSON file"""
        save_data(self.other_games_data, self.other_games_file)
    
    def process_videos(self, channel_url: str, max_new_videos: Optional[int] = None):
        """Process YouTube videos with game data fetching"""
        logging.info(f"Processing videos from channel: {channel_url}")
        
        if not max_new_videos:
            max_new_videos = 50
        
        known_video_ids = set(self.videos_data['videos'].keys())
        new_videos_processed = 0
        batch_size = min(max_new_videos * 2, 50)
        videos_fetched_total = 0
        consecutive_known_batches = 0
        
        # Smart starting position
        smart_start_offset = max(0, len(known_video_ids) - 10) if known_video_ids else 0
        if smart_start_offset > 0:
            logging.info(f"Smart start: skipping to position {smart_start_offset + 1}")
            videos_fetched_total = smart_start_offset
        
        while new_videos_processed < max_new_videos:
            skip_count = videos_fetched_total
            logging.info(f"Fetching {batch_size} video IDs starting from position {skip_count + 1}")
            
            # Fetch lightweight video info
            videos = self._get_channel_videos_lightweight(channel_url, skip_count, batch_size)
            if not videos:
                logging.info("No more videos available from channel")
                break
            
            videos_fetched_total += len(videos)
            
            # Filter to new videos only
            new_videos_in_batch = []
            for video in videos:
                video_id = video['video_id']
                if new_videos_processed >= max_new_videos:
                    break
                if video_id not in known_video_ids:
                    new_videos_in_batch.append(video)
                    if len(new_videos_in_batch) >= max_new_videos - new_videos_processed:
                        break
            
            if not new_videos_in_batch:
                consecutive_known_batches += 1
                logging.info(f"No new videos in this batch, continuing deeper")
                if consecutive_known_batches >= 3:
                    logging.info("Hit 3 consecutive batches with no new videos, stopping")
                    break
                continue
            else:
                consecutive_known_batches = 0
            
            # Process new videos
            logging.info(f"Found {len(new_videos_in_batch)} new videos, fetching metadata")
            batch_new_count = 0
            
            for video in new_videos_in_batch:
                if new_videos_processed >= max_new_videos:
                    break
                
                video_id = video['video_id']
                full_video = self._get_full_video_metadata(video_id)
                if full_video:
                    video_date = full_video.get('published_at', '')[:10] if full_video.get('published_at') else 'Unknown'
                    logging.info(f"Processing: {full_video.get('title', 'Unknown Title')} ({video_date})")
                    
                    # Process video with game link extraction
                    video_data = self._process_video_game_links(full_video)
                    
                    self.videos_data['videos'][video_id] = video_data
                    known_video_ids.add(video_id)
                    new_videos_processed += 1
                    batch_new_count += 1
                else:
                    logging.warning(f"Failed to get full metadata for {video_id}")
            
            logging.info(f"Processed {batch_new_count} new videos in this batch")
        
        # Save all data
        self.save_videos()
        logging.info(f"Video processing complete. Processed {new_videos_processed} new videos.")
        self._show_channel_progress(channel_url)
    
    def _process_video_game_links(self, video: Dict) -> Dict:
        """Extract and process game links from a video"""
        # Extract game links
        game_links = extract_game_links(video['description'])
        
        # Store video data with game links if found
        video_data = {
            **video,
            'steam_app_id': None,
            'itch_url': None,
            'itch_is_demo': False,
            'crazygames_url': None,
            'last_updated': datetime.now().isoformat()
        }
        
        # Priority: Steam > Itch.io > CrazyGames, but store all found links
        if game_links.steam:
            app_id = extract_steam_app_id(game_links.steam)
            video_data['steam_app_id'] = app_id
            # Store other platforms as secondary
            if game_links.itch:
                video_data['itch_url'] = game_links.itch
                video_data['itch_is_demo'] = True
            if game_links.crazygames:
                video_data['crazygames_url'] = game_links.crazygames
            logging.info(f"  Found Steam link: {game_links.steam}" + 
                        (f", Itch.io: {game_links.itch}" if game_links.itch else "") +
                        (f", CrazyGames: {game_links.crazygames}" if game_links.crazygames else ""))
            
        elif game_links.itch:
            video_data['itch_url'] = game_links.itch
            if game_links.crazygames:
                video_data['crazygames_url'] = game_links.crazygames
            logging.info(f"  Found Itch.io link: {game_links.itch}" +
                        (f", CrazyGames: {game_links.crazygames}" if game_links.crazygames else ""))
            
            # Fetch itch.io metadata if not already cached
            if game_links.itch not in self.other_games_data['games']:
                logging.info(f"  Fetching Itch.io metadata...")
                itch_data = self.itch_fetcher.fetch_data(game_links.itch)
                if itch_data:
                    self.other_games_data['games'][game_links.itch] = itch_data.__dict__
                    self.save_other_games()
                    
        elif game_links.crazygames:
            video_data['crazygames_url'] = game_links.crazygames
            logging.info(f"  Found CrazyGames link: {game_links.crazygames}")
            
            # Fetch CrazyGames metadata if not already cached
            if game_links.crazygames not in self.other_games_data['games']:
                logging.info(f"  Fetching CrazyGames metadata...")
                crazygames_data = self.crazygames_fetcher.fetch_data(game_links.crazygames)
                if crazygames_data:
                    self.other_games_data['games'][game_links.crazygames] = crazygames_data.__dict__
                    self.save_other_games()
                    
        else:
            logging.info(f"  No game links found, trying YouTube detection...")
            
            # Last resort: try YouTube's detected game
            detected_game = self.extract_youtube_detected_game(video['video_id'])
            if detected_game:
                logging.info(f"  YouTube detected game: {detected_game}")
                video_data['youtube_detected_game'] = detected_game
                
                # Try to find this game on Steam
                steam_match = self.find_steam_match(detected_game, confidence_threshold=0.6)
                if steam_match:
                    video_data['steam_app_id'] = steam_match['app_id']
                    video_data['youtube_detected_matched'] = True
                    logging.info(f"  Matched to Steam: {steam_match['name']} (App ID: {steam_match['app_id']}, confidence: {steam_match['confidence']:.2f})")
                else:
                    logging.info(f"  No confident Steam matches found for YouTube detected game")
            else:
                logging.info(f"  No YouTube detected game found")
        
        return video_data
    
    def update_steam_data(self, days_stale: int = 7, max_updates: Optional[int] = None):
        """Update Steam data for games that haven't been updated recently"""
        logging.info(f"Updating Steam data (stale after {days_stale} days)")
        
        # Collect all Steam app IDs from videos
        steam_app_ids = set()
        for video in self.videos_data['videos'].values():
            if video.get('steam_app_id'):
                steam_app_ids.add(video['steam_app_id'])
        
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
                last_updated = self.steam_data['games'][app_id].get('last_updated')
                if last_updated:
                    last_updated_date = datetime.fromisoformat(last_updated)
                    if last_updated_date > stale_date:
                        game_name = self.steam_data['games'][app_id].get('name', 'Unknown Game')
                        days_ago = (datetime.now() - last_updated_date).days
                        logging.info(f"Skipping app {app_id} ({game_name}) - updated {days_ago} days ago")
                        continue
            
            # Fetch/update Steam data
            steam_url = f"https://store.steampowered.com/app/{app_id}"
            logging.info(f"Updating Steam data for app {app_id}")
            
            try:
                steam_data = self.steam_fetcher.fetch_data(steam_url)
                if steam_data:
                    self.steam_data['games'][app_id] = steam_data.__dict__
                    logging.info(f"  Updated: {steam_data.name}")
                    updates_done += 1
                else:
                    logging.warning(f"  Failed to fetch data for app {app_id}")
            except Exception as e:
                logging.error(f"  Error fetching Steam data: {e}")
        
        self.save_steam()
        logging.info(f"Steam data update complete. Updated {updates_done} games.")
    
    def extract_youtube_detected_game(self, video_id: str) -> Optional[str]:
        """Extract YouTube's detected game from video page"""
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
                
                confidence = calculate_name_similarity(search_name, steam_game_name)
                
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
    
    def _get_channel_videos_lightweight(self, channel_url: str, skip_count: int, batch_size: int) -> List[Dict]:
        """Fetch lightweight video info from YouTube channel"""
        videos = []
        
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
                
                entries = info.get('entries', [info] if info else [])
                
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
    
    def _get_full_video_metadata(self, video_id: str) -> Optional[Dict]:
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
    
    def _show_channel_progress(self, channel_url: str):
        """Show channel scraping progress summary"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(channel_url, download=False)
                total_videos = info.get('playlist_count', 0)
                channel_name = info.get('channel', self.channel_id)
            
            scraped_videos = len(self.videos_data.get('videos', {}))
            
            if total_videos > 0:
                coverage = (scraped_videos / total_videos) * 100
                summary = f"\n{'='*60}\n"
                summary += f"CHANNEL PROGRESS SUMMARY: {channel_name}\n"
                summary += f"{'='*60}\n"
                summary += f"Total videos on channel: {total_videos:,}\n"
                summary += f"Videos in database: {scraped_videos:,}\n"
                summary += f"Coverage: {coverage:.1f}%\n"
                
                videos_with_games = sum(1 for v in self.videos_data['videos'].values() 
                                      if any([v.get('steam_app_id'), v.get('itch_url'), v.get('crazygames_url')]))
                game_coverage = (videos_with_games / scraped_videos * 100) if scraped_videos > 0 else 0
                summary += f"Videos with game data: {videos_with_games:,} ({game_coverage:.1f}% of scraped)\n"
                summary += f"{'='*60}"
                
                logging.info(summary)
                print(summary)
            else:
                logging.info(f"Could not get total video count for {channel_name}")
                
        except Exception as e:
            logging.debug(f"Error showing channel progress: {e}")


# Keep the same command-line interface as the original
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube to Steam game scraper - Refactored")
    parser.add_argument('mode', choices=['backfill', 'cron', 'reprocess', 'single-app', 'data-quality', 'infer-games'], 
                        help='Processing mode')
    parser.add_argument('--channel', type=str, help='Channel ID for backfill mode')
    parser.add_argument('--max-new', type=int, help='Maximum number of new videos to process')
    parser.add_argument('--max-steam-updates', type=int, help='Maximum number of Steam games to update')
    parser.add_argument('--steam-stale-days', type=int, default=7,
                        help='Consider Steam data stale after this many days (default: 7)')
    parser.add_argument('--app-id', type=str, help='Steam app ID to fetch (required for single-app mode)')
    args = parser.parse_args()
    
    # Implementation would follow the same pattern as the original script
    # but using the refactored scraper class
    print("Refactored scraper ready - implementation of CLI modes would follow original pattern")