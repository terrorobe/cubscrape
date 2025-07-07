#!/usr/bin/env python3
"""
YouTube Channel Video Scraper with Steam Game Data Integration
"""

import json
import re
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import subprocess
import logging
import argparse

import requests
from bs4 import BeautifulSoup
import yt_dlp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class YouTubeSteamScraper:
    def __init__(self):
        # Get the directory of this script, then build paths relative to project root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        self.videos_file = os.path.join(project_root, 'data', 'videos.json')
        self.steam_file = os.path.join(project_root, 'data', 'steam_games.json')
        self.videos_data = self.load_json(self.videos_file, {'videos': {}, 'last_updated': None})
        self.steam_data = self.load_json(self.steam_file, {'games': {}, 'last_updated': None})
        
        # yt-dlp options
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'force_generic_extractor': False,
        }
        
    def load_json(self, filepath: str, default: Dict) -> Dict:
        """Load JSON file or return default"""
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return default
    
    def save_videos(self):
        """Save video data to JSON file"""
        self.videos_data['last_updated'] = datetime.now().isoformat()
        os.makedirs(os.path.dirname(self.videos_file), exist_ok=True)
        with open(self.videos_file, 'w') as f:
            json.dump(self.videos_data, f, indent=2)
    
    def save_steam(self):
        """Save Steam data to JSON file"""
        self.steam_data['last_updated'] = datetime.now().isoformat()
        os.makedirs(os.path.dirname(self.steam_file), exist_ok=True)
        with open(self.steam_file, 'w') as f:
            json.dump(self.steam_data, f, indent=2)
    
    def get_channel_videos(self, channel_url: str, max_results: int = 50) -> List[Dict]:
        """Fetch videos from YouTube channel using yt-dlp"""
        videos = []
        
        # For channel videos, we need to extract the full playlist
        ydl_opts_videos = self.ydl_opts.copy()
        ydl_opts_videos['playlistend'] = max_results
        
        with yt_dlp.YoutubeDL(ydl_opts_videos) as ydl:
            try:
                # Extract channel videos
                logging.info(f"Fetching videos from {channel_url}")
                info = ydl.extract_info(channel_url, download=False)
                
                if 'entries' in info:
                    # Channel or playlist
                    entries = info['entries'][:max_results]
                else:
                    # Single video
                    entries = [info]
                
                # Now get detailed info for each video
                for entry in entries:
                    if not entry:
                        continue
                        
                    video_id = entry.get('id')
                    if not video_id:
                        continue
                    
                    # Stop if we have enough videos
                    if len(videos) >= max_results:
                        logging.info(f"Reached max_results limit ({max_results}), stopping fetch")
                        break
                    
                    # Get full video info
                    try:
                        logging.info(f"Fetching details for video {video_id}")
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        video_info = ydl.extract_info(video_url, download=False)
                        
                        videos.append({
                            'video_id': video_id,
                            'title': video_info.get('title', ''),
                            'description': video_info.get('description', ''),
                            'published_at': datetime.fromtimestamp(
                                video_info.get('timestamp', 0)
                            ).isoformat() if video_info.get('timestamp') else '',
                            'thumbnail': video_info.get('thumbnail', '')
                        })
                        
                    except Exception as e:
                        logging.error(f"Error fetching video {video_id}: {e}")
                        continue
                        
            except Exception as e:
                logging.error(f"Error fetching channel videos: {e}")
                
        return videos
    
    def extract_game_links(self, description: str) -> Dict[str, str]:
        """Extract game store links from video description"""
        links = {}
        
        # Steam patterns
        steam_patterns = [
            r'https?://store\.steampowered\.com/app/(\d+)',
            r'https?://steam\.com/app/(\d+)',
            r'https?://s\.team/a/(\d+)'
        ]
        
        for pattern in steam_patterns:
            match = re.search(pattern, description)
            if match:
                app_id = match.group(1)
                links['steam'] = f"https://store.steampowered.com/app/{app_id}"
                break
        
        # Itch.io patterns
        itch_patterns = [
            r'https?://([^.]+)\.itch\.io/([^/\s]+)',
            r'https?://itch\.io/games/([^/\s]+)'
        ]
        
        for pattern in itch_patterns:
            match = re.search(pattern, description)
            if match:
                links['itch'] = match.group(0)
                break
        
        return links
    
    def fetch_steam_data(self, steam_url: str) -> Dict:
        """Fetch game data from Steam"""
        app_id = re.search(r'/app/(\d+)', steam_url).group(1)
        
        # First, get basic data from Steam API
        api_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
        response = requests.get(api_url)
        
        if response.status_code != 200:
            return {}
            
        data = response.json()
        if not data.get(app_id, {}).get('success'):
            return {}
            
        app_data = data[app_id]['data']
        
        # Parse the data we need
        result = {
            'steam_app_id': app_id,
            'steam_url': steam_url,
            'name': app_data.get('name', ''),
            'is_free': app_data.get('is_free', False),
            'release_date': app_data.get('release_date', {}).get('date', ''),
            'coming_soon': app_data.get('release_date', {}).get('coming_soon', False),
            'genres': [g['description'] for g in app_data.get('genres', [])],
            'categories': [c['description'] for c in app_data.get('categories', [])],
            'developers': app_data.get('developers', []),
            'publishers': app_data.get('publishers', []),
            'price': self._get_price(app_data),
            'header_image': app_data.get('header_image', '')
        }
        
        # Fetch additional data from store page (tags, reviews)
        store_data = self._fetch_store_page_data(steam_url, app_data)
        result.update(store_data)
        
        return result
    
    def _get_price(self, app_data: Dict) -> Optional[str]:
        """Extract price information"""
        if app_data.get('is_free'):
            return "Free"
        
        price_data = app_data.get('price_overview', {})
        if price_data:
            return price_data.get('final_formatted', '')
        
        return None
    
    def _fetch_store_page_data(self, steam_url: str, app_data: Dict = None) -> Dict:
        """Scrape additional data from Steam store page"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Need to set cookie to get age-gated content
        cookies = {'birthtime': '0', 'mature_content': '1'}
        
        response = requests.get(steam_url, headers=headers, cookies=cookies)
        if response.status_code != 200:
            return {}
            
        soup = BeautifulSoup(response.content, 'lxml')
        html_content = response.text  # Keep raw HTML for demo detection
        
        result = {}
        
        # Get page text early for demo detection
        page_text = soup.get_text()
        
        # Get tags
        tags = []
        tag_elements = soup.select('a.app_tag')
        for tag in tag_elements[:10]:  # Top 10 tags
            tag_text = tag.text.strip()
            if tag_text:
                tags.append(tag_text)
        result['tags'] = tags
        
        # Check for demo - look for multiple indicators
        demo_button = soup.find('a', class_='game_area_demo_above_purchase')
        demo_text_found = 'download' in page_text.lower() and 'demo' in page_text.lower()
        demo_link_found = 'store.steampowered.com/app/' in page_text and 'demo' in page_text.lower()
        
        result['has_demo'] = demo_button is not None or demo_text_found or demo_link_found
        
        # If this main game has a demo, try to find the demo app ID
        if result['has_demo']:
            demo_app_id = self._find_demo_app_id(soup, page_text, html_content)
            if demo_app_id:
                result['demo_app_id'] = demo_app_id
        
        # Check if this IS a demo (look for "demo" in categories or name)
        name_from_api = app_data.get('name', '') if app_data else ''
        categories_from_api = [c.get('description', '') for c in app_data.get('categories', [])] if app_data else []
        
        is_demo = any('demo' in cat.lower() for cat in categories_from_api)
        if not is_demo:
            # Also check the name and page content for demo indicators
            name = name_from_api.lower()
            is_demo = 'demo' in name or 'Demo' in page_text[:2000]
        result['is_demo'] = is_demo
        
        # If this is a demo, try to find the full game
        if is_demo:
            full_game_id = self._find_full_game_id(soup, page_text)
            if full_game_id:
                result['full_game_app_id'] = full_game_id
        
        # Check for early access
        early_access = soup.find('div', class_='early_access_header')
        result['is_early_access'] = early_access is not None
        
        # Look for Overall Reviews data - try both "All Reviews" and "Overall Reviews"
        overall_match = re.search(r'All Reviews:\s*([^\n\(]+)\s*\((\d{1,3}(?:,\d{3})*)\s*\).*?(\d+)%.*?(\d{1,3}(?:,\d{3})*)', page_text, re.IGNORECASE | re.DOTALL)
        if not overall_match:
            overall_match = re.search(r'Overall Reviews:\s*([^\n\(]+)\s*\((\d{1,3}(?:,\d{3})*)\s*reviews?\).*?(\d+)%.*?(\d{1,3}(?:,\d{3})*)', page_text, re.IGNORECASE | re.DOTALL)
        
        # Look for Recent Reviews data  
        recent_match = re.search(r'Recent Reviews:\s*([^\n\(]+)\s*\((\d{1,3}(?:,\d{3})*)\s*\).*?(\d+)%.*?(\d{1,3}(?:,\d{3})*)', page_text, re.IGNORECASE | re.DOTALL)
        
        # Prefer Overall Reviews if available
        if overall_match:
            summary = overall_match.group(1).strip()
            count = int(overall_match.group(2).replace(',', ''))
            percentage = int(overall_match.group(3))
            
            result['positive_review_percentage'] = percentage
            result['review_count'] = count
            result['review_summary'] = summary
            
            # Also store recent data if available
            if recent_match:
                recent_summary = recent_match.group(1).strip()
                recent_count = int(recent_match.group(2).replace(',', ''))
                recent_percentage = int(recent_match.group(3))
                result['recent_review_percentage'] = recent_percentage
                result['recent_review_count'] = recent_count
                result['recent_review_summary'] = recent_summary
                
        elif recent_match:
            # Only recent data available
            summary = recent_match.group(1).strip()
            count = int(recent_match.group(2).replace(',', ''))
            percentage = int(recent_match.group(3))
            
            result['positive_review_percentage'] = percentage
            result['review_count'] = count
            result['review_summary'] = summary
        
        # Extract more specific planned release date for coming soon games
        if app_data and app_data.get('release_date', {}).get('coming_soon'):
            planned_date = self._extract_planned_release_date(soup, page_text)
            if planned_date:
                result['planned_release_date'] = planned_date
        
        return result
    
    def _find_full_game_id(self, soup: BeautifulSoup, page_text: str) -> Optional[str]:
        """Try to find the full game app ID from a demo page"""
        # Method 1: Look for Community Hub link
        community_links = soup.find_all('a', href=re.compile(r'steamcommunity\.com/app/(\d+)'))
        for link in community_links:
            match = re.search(r'/app/(\d+)', link.get('href', ''))
            if match:
                return match.group(1)
        
        # Method 2: Look for "Visit the main game page" or similar text patterns
        main_game_patterns = [
            r'main game.*?app/(\d+)',
            r'full game.*?app/(\d+)',
            r'full version.*?app/(\d+)',
            r'complete game.*?app/(\d+)',
        ]
        
        for pattern in main_game_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Method 3: Look for Steam store links that aren't the current demo
        store_links = soup.find_all('a', href=re.compile(r'store\.steampowered\.com/app/(\d+)'))
        current_app_id = re.search(r'/app/(\d+)', soup.find('link', {'rel': 'canonical'}).get('href', '')) if soup.find('link', {'rel': 'canonical'}) else None
        current_id = current_app_id.group(1) if current_app_id else None
        
        for link in store_links:
            match = re.search(r'/app/(\d+)', link.get('href', ''))
            if match and match.group(1) != current_id:
                # Additional check: make sure it's not another demo
                link_text = link.get_text().lower()
                if 'demo' not in link_text:
                    return match.group(1)
        
        return None
    
    def _find_demo_app_id(self, soup: BeautifulSoup, page_text: str, html_content: str = None) -> Optional[str]:
        """Try to find the demo app ID from a main game page"""
        # Get current game app ID for comparison
        current_app_id = re.search(r'/app/(\d+)', soup.find('link', {'rel': 'canonical'}).get('href', '')) if soup.find('link', {'rel': 'canonical'}) else None
        current_id = current_app_id.group(1) if current_app_id else None
        
        # Method 1: Search raw HTML content for Steam app URLs containing 'demo'
        if html_content:
            # Look for patterns like: store.steampowered.com/app/1234567/Game_Demo/
            demo_url_pattern = r'store\.steampowered\.com/app/(\d+)/[^"\']*[Dd]emo[^"\'/]*/?'
            matches = re.findall(demo_url_pattern, html_content)
            for demo_id in matches:
                if demo_id != current_id:
                    return demo_id
            
            # Look for any Steam app ID that appears near 'demo' text
            demo_context_pattern = r'(?:demo|Demo|DEMO).{0,200}?store\.steampowered\.com/app/(\d+)|store\.steampowered\.com/app/(\d+).{0,200}?(?:demo|Demo|DEMO)'
            matches = re.findall(demo_context_pattern, html_content)
            for match in matches:
                demo_id = match[0] or match[1]  # One of the groups will match
                if demo_id and demo_id != current_id:
                    return demo_id
        
        # Method 2: Look for demo download button/link patterns in page text
        demo_patterns = [
            r'store\.steampowered\.com/app/(\d+).*demo',
            r'demo.*store\.steampowered\.com/app/(\d+)',
            r'/app/(\d+)/.*demo',
            r'Download.*Demo.*app/(\d+)',
        ]
        
        for pattern in demo_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                demo_id = match.group(1)
                if demo_id != current_id:
                    return demo_id
        
        # Method 2: Look for demo links in the HTML
        demo_links = soup.find_all('a', href=re.compile(r'store\.steampowered\.com/app/(\d+)'))
        for link in demo_links:
            href = link.get('href', '')
            link_text = link.get_text().lower()
            if 'demo' in link_text or 'demo' in href.lower():
                match = re.search(r'/app/(\d+)', href)
                if match:
                    demo_id = match.group(1)
                    # Make sure it's different from current game
                    current_app_id = re.search(r'/app/(\d+)', soup.find('link', {'rel': 'canonical'}).get('href', '')) if soup.find('link', {'rel': 'canonical'}) else None
                    current_id = current_app_id.group(1) if current_app_id else None
                    if demo_id != current_id:
                        return demo_id
        
        # Method 3: Look for specific demo button classes/IDs
        demo_elements = soup.find_all(['a', 'div'], class_=re.compile(r'demo', re.IGNORECASE))
        for element in demo_elements:
            href = element.get('href', '')
            if 'store.steampowered.com/app/' in href:
                match = re.search(r'/app/(\d+)', href)
                if match:
                    return match.group(1)
        
        return None
    
    def _extract_planned_release_date(self, soup: BeautifulSoup, page_text: str) -> Optional[str]:
        """Extract more specific planned release date for coming soon games"""
        # Method 1: Look for specific date patterns in Coming Soon section
        coming_soon_patterns = [
            r'Coming Soon.*?(\w+ \d{1,2},? \d{4})',  # "Coming Soon - January 15, 2025"
            r'Coming Soon.*?(\w+ \d{4})',            # "Coming Soon - March 2025"  
            r'Coming Soon.*?(Q[1-4] \d{4})',         # "Coming Soon - Q2 2025"
            r'Coming Soon.*?(\d{4})',                # "Coming Soon - 2025"
            r'Release Date.*?(\w+ \d{1,2},? \d{4})', # "Release Date: January 15, 2025"
            r'Release Date.*?(\w+ \d{4})',           # "Release Date: March 2025"
            r'Release Date.*?(Q[1-4] \d{4})',        # "Release Date: Q2 2025"
            r'Available.*?(\w+ \d{1,2},? \d{4})',    # "Available January 15, 2025"
            r'Available.*?(\w+ \d{4})',              # "Available March 2025"
            r'Available.*?(Q[1-4] \d{4})',           # "Available Q2 2025"
        ]
        
        # Look for date patterns in page text
        for pattern in coming_soon_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                # Return the most specific date found
                return date_str
        
        # Method 2: Look for release date in structured elements
        release_date_element = soup.find('div', class_='release_date')
        if release_date_element:
            date_text = release_date_element.get_text(strip=True)
            # Extract date from "Release Date: DATE" format
            date_match = re.search(r'Release Date:?\s*(.+)', date_text, re.IGNORECASE)
            if date_match:
                return date_match.group(1).strip()
        
        # Method 3: Look for coming soon date in meta description or other elements
        coming_soon_element = soup.find('div', string=re.compile(r'Coming Soon', re.IGNORECASE))
        if coming_soon_element:
            # Look for dates in the vicinity of "Coming Soon" text
            context = coming_soon_element.get_text() if coming_soon_element else ''
            for pattern in [r'(\w+ \d{1,2},? \d{4})', r'(\w+ \d{4})', r'(Q[1-4] \d{4})']:
                match = re.search(pattern, context)
                if match:
                    return match.group(1).strip()
        
        return None
    
    def process_videos(self, channel_url: str, max_new_videos: Optional[int] = None):
        """Process YouTube videos only"""
        logging.info(f"Processing videos from channel: {channel_url}")
        
        if not max_new_videos:
            max_new_videos = 50
        
        known_video_ids = set(self.videos_data['videos'].keys())
        new_videos_processed = 0
        batch_size = max_new_videos  # Fetch exactly what we need per batch
        videos_fetched_total = 0
        
        while new_videos_processed < max_new_videos:
            # Calculate how many videos to skip (based on total fetched so far)
            skip_count = videos_fetched_total
            
            logging.info(f"Fetching {batch_size} videos starting from position {skip_count + 1}")
            
            # Fetch videos with offset
            videos = self.get_channel_videos_with_offset(channel_url, skip_count, batch_size)
            
            if not videos:
                logging.info("No more videos available from channel")
                break
            
            videos_fetched_total += len(videos)
            batch_new_count = 0
            
            for video in videos:
                video_id = video['video_id']
                
                # Check if we've hit the max new videos limit
                if new_videos_processed >= max_new_videos:
                    break
                
                # Skip if we already have this video
                if video_id in known_video_ids:
                    continue
                
                logging.info(f"Processing: {video['title']}")
                
                # Process video with game link extraction
                video_data = self._process_video_game_links(video)
                
                self.videos_data['videos'][video_id] = video_data
                known_video_ids.add(video_id)  # Add to our tracking set
                new_videos_processed += 1
                batch_new_count += 1
            
            # If we found new videos, great! Continue if we need more
            if batch_new_count > 0:
                logging.info(f"Found {batch_new_count} new videos in this batch")
            else:
                # No new videos in this batch - we've likely caught up to known videos
                logging.info(f"No new videos in this batch, continuing deeper into channel history")
        
        self.save_videos()
        logging.info(f"Video processing complete. Processed {new_videos_processed} new videos.")
    
    def _process_video_game_links(self, video: Dict) -> Dict:
        """Extract and process game links from a video"""
        # Extract game links
        game_links = self.extract_game_links(video['description'])
        
        # Store video data with game links if found
        video_data = {
            **video,
            'steam_app_id': None,
            'itch_url': None,
            'itch_is_demo': False,  # Flag to indicate itch.io is demo/test version
            'last_updated': datetime.now().isoformat()
        }
        
        # Prioritize Steam when both platforms exist
        if game_links.get('steam') and game_links.get('itch'):
            # Both Steam and itch.io found - prioritize Steam, mark itch as demo
            app_id = re.search(r'/app/(\d+)', game_links['steam']).group(1)
            video_data['steam_app_id'] = app_id
            video_data['itch_url'] = game_links['itch']
            video_data['itch_is_demo'] = True
            logging.info(f"  Found both platforms - Steam (primary): {game_links['steam']}, Itch.io (demo): {game_links['itch']}")
        elif game_links.get('steam'):
            app_id = re.search(r'/app/(\d+)', game_links['steam']).group(1)
            video_data['steam_app_id'] = app_id
            logging.info(f"  Found Steam link: {game_links['steam']}")
        elif game_links.get('itch'):
            video_data['itch_url'] = game_links['itch']
            logging.info(f"  Found Itch.io link: {game_links['itch']}")
        else:
            logging.info(f"  No game links found")
        
        return video_data
    
    def reprocess_video_descriptions(self):
        """Reprocess existing video descriptions to extract game links with current logic"""
        logging.info("Reprocessing existing video descriptions")
        
        videos_processed = 0
        updated_count = 0
        
        for video_id, video_data in self.videos_data['videos'].items():
            logging.info(f"Reprocessing: {video_data.get('title', 'Unknown Title')}")
            
            # Store original data for comparison
            original_steam_id = video_data.get('steam_app_id')
            original_itch_url = video_data.get('itch_url')
            original_itch_is_demo = video_data.get('itch_is_demo', False)
            
            # Reprocess with current logic
            updated_video_data = self._process_video_game_links(video_data)
            
            # Check if anything changed
            if (updated_video_data['steam_app_id'] != original_steam_id or
                updated_video_data['itch_url'] != original_itch_url or
                updated_video_data['itch_is_demo'] != original_itch_is_demo):
                updated_count += 1
                logging.info(f"  Updated game links for video")
            
            # Update the video data
            self.videos_data['videos'][video_id] = updated_video_data
            videos_processed += 1
        
        self.save_videos()
        logging.info(f"Reprocessing complete. Processed {videos_processed} videos, updated {updated_count} videos.")
    
    def get_channel_videos_with_offset(self, channel_url: str, skip_count: int, batch_size: int) -> List[Dict]:
        """Fetch videos from YouTube channel with offset support"""
        videos = []
        
        # Use playlist start/end to simulate offset
        ydl_opts_videos = self.ydl_opts.copy()
        ydl_opts_videos['playliststart'] = skip_count + 1
        ydl_opts_videos['playlistend'] = skip_count + batch_size
        
        with yt_dlp.YoutubeDL(ydl_opts_videos) as ydl:
            try:
                logging.info(f"Fetching videos from {channel_url}")
                info = ydl.extract_info(channel_url, download=False)
                
                if 'entries' in info:
                    entries = info['entries']
                else:
                    entries = [info] if info else []
                
                # Process entries
                for entry in entries:
                    if not entry:
                        continue
                        
                    video_id = entry.get('id')
                    if not video_id:
                        continue
                    
                    # Stop if we have enough videos for this batch
                    if len(videos) >= batch_size:
                        break
                    
                    try:
                        logging.info(f"Fetching details for video {video_id}")
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        video_info = ydl.extract_info(video_url, download=False)
                        
                        videos.append({
                            'video_id': video_id,
                            'title': video_info.get('title', ''),
                            'description': video_info.get('description', ''),
                            'published_at': datetime.fromtimestamp(
                                video_info.get('timestamp', 0)
                            ).isoformat() if video_info.get('timestamp') else '',
                            'thumbnail': video_info.get('thumbnail', '')
                        })
                        
                    except Exception as e:
                        logging.error(f"Error fetching video {video_id}: {e}")
                        continue
                        
            except Exception as e:
                logging.error(f"Error fetching channel videos: {e}")
                
        return videos
    
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
                        logging.info(f"Skipping app {app_id} - recently updated")
                        continue
            
            # Fetch/update Steam data
            steam_url = f"https://store.steampowered.com/app/{app_id}"
            logging.info(f"Updating Steam data for app {app_id}")
            
            try:
                steam_data = self.fetch_steam_data(steam_url)
                if steam_data:
                    steam_data['last_updated'] = datetime.now().isoformat()
                    self.steam_data['games'][app_id] = steam_data
                    logging.info(f"  Updated: {steam_data.get('name', 'Unknown')}")
                    updates_done += 1
                    
                    # If this is a demo and we found a full game, fetch that too
                    if steam_data.get('is_demo') and steam_data.get('full_game_app_id'):
                        full_game_id = steam_data['full_game_app_id']
                        logging.info(f"  Found full game {full_game_id}, fetching data")
                        
                        # Check if we need to update the full game (same staleness logic)
                        should_update_full = True
                        if full_game_id in self.steam_data['games']:
                            last_updated = self.steam_data['games'][full_game_id].get('last_updated')
                            if last_updated:
                                last_updated_date = datetime.fromisoformat(last_updated)
                                if last_updated_date > stale_date:
                                    should_update_full = False
                                    logging.info(f"  Skipping full game {full_game_id} - recently updated")
                        
                        if should_update_full:
                            try:
                                full_game_url = f"https://store.steampowered.com/app/{full_game_id}"
                                full_game_data = self.fetch_steam_data(full_game_url)
                                if full_game_data:
                                    full_game_data['last_updated'] = datetime.now().isoformat()
                                    self.steam_data['games'][full_game_id] = full_game_data
                                    logging.info(f"  Updated full game: {full_game_data.get('name', 'Unknown')}")
                            except Exception as e:
                                logging.error(f"  Error fetching full game data: {e}")
                    
                    # If this is a main game and we found a demo, fetch that too
                    if steam_data.get('has_demo') and steam_data.get('demo_app_id'):
                        demo_id = steam_data['demo_app_id']
                        logging.info(f"  Found demo {demo_id}, fetching data")
                        
                        # Check if we need to update the demo (same staleness logic)
                        should_update_demo = True
                        if demo_id in self.steam_data['games']:
                            last_updated = self.steam_data['games'][demo_id].get('last_updated')
                            if last_updated:
                                last_updated_date = datetime.fromisoformat(last_updated)
                                if last_updated_date > stale_date:
                                    should_update_demo = False
                                    logging.info(f"  Skipping demo {demo_id} - recently updated")
                        
                        if should_update_demo:
                            try:
                                demo_url = f"https://store.steampowered.com/app/{demo_id}"
                                demo_data = self.fetch_steam_data(demo_url)
                                if demo_data:
                                    demo_data['last_updated'] = datetime.now().isoformat()
                                    self.steam_data['games'][demo_id] = demo_data
                                    logging.info(f"  Updated demo: {demo_data.get('name', 'Unknown')}")
                            except Exception as e:
                                logging.error(f"  Error fetching demo data: {e}")
                else:
                    logging.warning(f"  Failed to fetch data for app {app_id}")
            except Exception as e:
                logging.error(f"  Error fetching Steam data: {e}")
        
        self.save_steam()
        logging.info(f"Steam data update complete. Updated {updates_done} games.")
    


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube to Steam game scraper")
    parser.add_argument('--mode', choices=['videos', 'steam', 'both', 'reprocess'], default='both',
                        help='What to update: videos, steam data, both, or reprocess existing video descriptions')
    parser.add_argument('--max-new', type=int, help='Maximum number of new videos to process')
    parser.add_argument('--max-steam-updates', type=int, help='Maximum number of Steam games to update')
    parser.add_argument('--steam-stale-days', type=int, default=7,
                        help='Consider Steam data stale after this many days (default: 7)')
    args = parser.parse_args()
    
    scraper = YouTubeSteamScraper()
    
    channel_url = os.getenv('YOUTUBE_CHANNEL_URL')
    
    if not channel_url and args.mode in ['videos', 'both']:
        print("Error: YOUTUBE_CHANNEL_URL environment variable not set")
        print("Please set it in your .env file or environment")
        sys.exit(1)
    
    # Process based on mode
    if args.mode == 'reprocess':
        scraper.reprocess_video_descriptions()
    elif args.mode in ['videos', 'both']:
        scraper.process_videos(channel_url, max_new_videos=args.max_new)
    
    if args.mode in ['steam', 'both']:
        scraper.update_steam_data(
            days_stale=args.steam_stale_days,
            max_updates=args.max_steam_updates
        )