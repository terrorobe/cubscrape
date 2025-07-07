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
    def __init__(self, channel_id: str):
        # Get the directory of this script, then build paths relative to project root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        
        # Load config
        self.config = self.load_config()
        
        # Set up file paths
        self.videos_file = os.path.join(project_root, 'data', f'videos-{channel_id}.json')
        self.steam_file = os.path.join(project_root, 'data', 'steam_games.json')
        self.other_games_file = os.path.join(project_root, 'data', 'other_games.json')
        
        self.videos_data = self.load_json(self.videos_file, {'videos': {}, 'last_updated': None})
        self.steam_data = self.load_json(self.steam_file, {'games': {}, 'last_updated': None})
        self.other_games_data = self.load_json(self.other_games_file, {'games': {}, 'last_updated': None})
        
        # Store channel info
        self.channel_id = channel_id
        
        # yt-dlp options
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'force_generic_extractor': False,
        }
        
    def load_config(self) -> Dict:
        """Load configuration from config.json"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        config_path = os.path.join(project_root, 'config.json')
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        return {'channels': {}}
    
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
    
    def save_other_games(self):
        """Save other games data to JSON file"""
        self.other_games_data['last_updated'] = datetime.now().isoformat()
        os.makedirs(os.path.dirname(self.other_games_file), exist_ok=True)
        with open(self.other_games_file, 'w') as f:
            json.dump(self.other_games_data, f, indent=2)
    
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
        
        # CrazyGames patterns
        crazygames_patterns = [
            r'https?://www\.crazygames\.com/game/([^/\s]+)',
            r'https?://crazygames\.com/game/([^/\s]+)'
        ]
        
        for pattern in crazygames_patterns:
            match = re.search(pattern, description)
            if match:
                links['crazygames'] = match.group(0)
                break
        
        return links
    
    def fetch_itch_data(self, itch_url: str) -> Dict:
        """Fetch game data from Itch.io"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(itch_url, headers=headers)
            if response.status_code != 200:
                return {}
            
            soup = BeautifulSoup(response.content, 'lxml')
            result = {
                'itch_url': itch_url,
                'platform': 'itch',
                'is_free': True,  # Most itch games are free or pay-what-you-want
            }
            
            # Get game name
            title_elem = soup.find('h1', class_='game_title') or soup.find('h1')
            if title_elem:
                result['name'] = title_elem.get_text(strip=True)
            
            # Get preview image from meta tags
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                result['header_image'] = og_image['content']
            
            # Get tags - try multiple selectors
            tags = []
            
            # First try to find tags in the info table (most reliable for Itch.io)
            table_rows = soup.select('table tr')
            for row in table_rows:
                cells = row.find_all('td')
                if len(cells) == 2 and cells[0].get_text(strip=True) == 'Tags':
                    # Found the tags row, extract tags from second cell
                    tag_links = cells[1].find_all('a')
                    for tag_link in tag_links[:10]:
                        tag_text = tag_link.get_text(strip=True)
                        if tag_text and len(tag_text) > 1 and tag_text not in tags:
                            tags.append(tag_text)
                    break
            
            # Fallback selectors if table approach didn't work
            if not tags:
                tag_selectors = [
                    '.game_genre_tag',
                    '.genre_tag', 
                    'a[href*="/genre/"]',
                    'a[href*="/tag/"]',
                    '.tags a',
                    '.game_tags a'
                ]
                
                for selector in tag_selectors:
                    tag_elements = soup.select(selector)
                    for tag in tag_elements[:10]:  # Limit per selector
                        tag_text = tag.get_text(strip=True)
                        if tag_text and len(tag_text) > 1 and tag_text not in tags:
                            tags.append(tag_text)
                    if tags:  # Stop at first working selector
                        break
                    
            result['tags'] = tags[:10]  # Limit to 10 tags total
            
            # Get rating (itch uses 5-star system, convert to 0-100)
            # Itch.io specific selectors
            rating_elem = soup.select_one('.aggregate_rating') or soup.select_one('.star_value')
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                # Extract rating like "Rated 4.7 out of 5 stars"
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    stars = float(rating_match.group(1))
                    # Convert 5-star to 0-100 percentage
                    result['positive_review_percentage'] = int((stars / 5.0) * 100)
                    
                    # Also extract review count if available
                    count_match = re.search(r'\((\d+)\s*total ratings?\)', rating_text)
                    if count_match:
                        result['review_count'] = int(count_match.group(1))
            
            # Get download count as proxy for review count
            count_selectors = [
                'span.download_count',
                '.downloads',
                '.plays_count',
                '[data-downloads]'
            ]
            
            for selector in count_selectors:
                count_elem = soup.select_one(selector)
                if count_elem:
                    count_text = count_elem.get_text(strip=True) or count_elem.get('data-downloads', '')
                    # Extract number from "1,234 downloads" or "1,234 plays"
                    count_match = re.search(r'([\d,]+)', count_text)
                    if count_match:
                        result['review_count'] = int(count_match.group(1).replace(',', ''))
                        break
            
            return result
            
        except Exception as e:
            logging.error(f"Error fetching itch.io data: {e}")
            return {}
    
    def fetch_crazygames_data(self, crazygames_url: str) -> Dict:
        """Fetch game data from CrazyGames"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(crazygames_url, headers=headers)
            if response.status_code != 200:
                return {}
            
            soup = BeautifulSoup(response.content, 'lxml')
            page_text = response.text
            
            result = {
                'crazygames_url': crazygames_url,
                'platform': 'crazygames',
                'is_free': True,  # CrazyGames are free browser games
            }
            
            # Get game name from title or h1
            title_elem = soup.find('h1') or soup.find('title')
            if title_elem:
                title_text = title_elem.get_text(strip=True)
                # Clean up title (remove " - CrazyGames" suffix)
                result['name'] = title_text.split(' - CrazyGames')[0].split(' | CrazyGames')[0]
            
            # Get tags/categories - CrazyGames specific selectors
            tags = []
            # CrazyGames uses specific CSS classes
            tag_elements = soup.select('.GameTags_gameTagChipContainer__F5xPO a')
            
            for tag in tag_elements[:10]:  # Limit to 10 tags
                tag_text = tag.get_text(strip=True)
                if tag_text:
                    # Clean up tag text - remove trailing numbers like "Casual1,157"
                    import re
                    clean_tag = re.sub(r'[\d,]+$', '', tag_text).strip()
                    if clean_tag and len(clean_tag) > 2 and clean_tag not in tags:
                        tags.append(clean_tag)
                        
            result['tags'] = tags
            
            # Look for rating in structured data (JSON-LD)
            script_tags = soup.find_all('script', type='application/ld+json')
            for script in script_tags:
                try:
                    json_data = json.loads(script.string)
                    # Handle both single dict and array of dicts
                    if isinstance(json_data, list):
                        # Find the main game entity
                        for item in json_data:
                            if isinstance(item, dict) and item.get('@type') in ['ItemPage', 'VideoGame']:
                                # Check mainEntity for VideoGame type
                                main_entity = item.get('mainEntity', {})
                                if main_entity.get('aggregateRating'):
                                    aggregate_rating = main_entity['aggregateRating']
                                    rating_value = float(aggregate_rating['ratingValue'])
                                    best_rating = float(aggregate_rating.get('bestRating', 10))
                                    percentage = round((rating_value / best_rating) * 100)
                                    result['positive_review_percentage'] = int(percentage)
                                    result['review_count'] = int(aggregate_rating.get('ratingCount', 0))
                                    logging.info(f"  Found rating in JSON-LD: {rating_value}/{best_rating} = {percentage}%")
                                    break
                    elif isinstance(json_data, dict):
                        # Check for aggregateRating
                        aggregate_rating = json_data.get('aggregateRating', {})
                        if aggregate_rating.get('ratingValue'):
                            rating_value = float(aggregate_rating['ratingValue'])
                            best_rating = float(aggregate_rating.get('bestRating', 10))
                            # Convert to 0-100 scale
                            percentage = round((rating_value / best_rating) * 100)
                            result['positive_review_percentage'] = int(percentage)
                            result['review_count'] = int(aggregate_rating.get('ratingCount', 0))
                            logging.info(f"  Found rating in JSON-LD: {rating_value}/{best_rating} = {percentage}%")
                            break
                except Exception as e:
                    logging.debug(f"  Error parsing JSON-LD: {e}")
            
            # Fallback: Look for rating in page text using regex patterns
            if 'positive_review_percentage' not in result:
                # Pattern for "X.X / 10" or "X.X out of 10" ratings
                rating_patterns = [
                    r'(\d+\.?\d*)\s*(?:/|out of)\s*10\b',
                    r'rating["\s:]+(\d+\.?\d*)',
                    r'"ratingValue"[:\s]+["\']?(\d+\.?\d*)',
                ]
                
                for pattern in rating_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        rating = float(match.group(1))
                        if rating <= 10:  # Out of 10 rating
                            result['positive_review_percentage'] = int((rating / 10.0) * 100)
                        elif rating <= 100:  # Already percentage
                            result['positive_review_percentage'] = int(rating)
                        break
            
            # Look for vote/review count
            if 'review_count' not in result:
                count_patterns = [
                    r'(\d{1,3}(?:,\d{3})*)\s*(?:votes?|ratings?)',
                    r'"ratingCount"[:\s]+["\']?(\d+)',
                    r'Total Votes[:\s]+(\d{1,3}(?:,\d{3})*)',
                ]
                
                for pattern in count_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        count_str = match.group(1).replace(',', '')
                        result['review_count'] = int(count_str)
                        break
            
            # Get preview image from meta tags
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                result['header_image'] = og_image['content']
            
            return result
            
        except Exception as e:
            logging.error(f"Error fetching CrazyGames data: {e}")
            return {}
    
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
        else:
            # Check for cases where there are reviews but not enough for a score
            insufficient_review_patterns = [
                r'Need more user reviews to generate a score.*?(\d+)\s*user review',
                r'(\d+)\s*user review.*?Need more user reviews',
                r'(\d+)\s*review.*?Need more.*?score',
            ]
            
            for pattern in insufficient_review_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE | re.DOTALL)
                if match:
                    review_count = int(match.group(1))
                    result['review_count'] = review_count
                    result['insufficient_reviews'] = True
                    result['review_summary'] = 'Need more reviews for score'
                    break
            
            # Also check for "No user reviews" case
            if 'No user reviews' in page_text:
                result['review_count'] = 0
                result['review_summary'] = 'No user reviews'
        
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
            # Look for steam:// protocol install links
            steam_protocol_pattern = r'steam://install/(\d+)'
            matches = re.findall(steam_protocol_pattern, html_content)
            for demo_id in matches:
                if demo_id != current_id:
                    return demo_id
            
            # Look for JavaScript ShowGotSteamModal calls
            js_modal_pattern = r'ShowGotSteamModal.*?[\'"]steam://install/(\d+)[\'"]'
            matches = re.findall(js_modal_pattern, html_content)
            for demo_id in matches:
                if demo_id != current_id:
                    return demo_id
            
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
        
        def is_valid_date_string(date_str: str) -> bool:
            """Validate that a date string looks like an actual date, not system specs"""
            date_str = date_str.lower().strip()
            
            # Invalid patterns (system requirements, etc.)
            invalid_patterns = [
                r'\b(at|while|during|via|per)\s+\d+',  # "at 1080", "while 60", etc.
                r'\d+p\b',                              # "1080p", "720p", etc.
                r'fps|hz|mhz|ghz',                      # Performance specs
                r'\b\d+\s*(mb|gb|tb)\b',               # Storage specs
            ]
            
            for pattern in invalid_patterns:
                if re.search(pattern, date_str, re.IGNORECASE):
                    return False
            
            # Valid patterns (actual dates)
            valid_patterns = [
                r'^(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}$',
                r'^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2},?\s+\d{4}$',
                r'^(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}$',
                r'^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{4}$',
                r'^q[1-4]\s+\d{4}$',
                r'^\d{4}$',
                r'^(early|mid|late)\s+\d{4}$',
                r'^(spring|summer|fall|autumn|winter)\s+\d{4}$',
                r'^coming soon$',
                r'^tbd$',
                r'^to be announced$',
            ]
            
            for pattern in valid_patterns:
                if re.search(pattern, date_str, re.IGNORECASE):
                    return True
                    
            return False
        
        # Method 1: Look for specific date patterns in Coming Soon section
        coming_soon_patterns = [
            r'Coming Soon.*?(\w+ \d{1,2},? \d{4})',  # "Coming Soon - January 15, 2025"
            r'Coming Soon.*?(\w+ \d{4})',            # "Coming Soon - March 2025"  
            r'Coming Soon.*?(Q[1-4] \d{4})',         # "Coming Soon - Q2 2025"
            r'Coming Soon.*?(\d{4})',                # "Coming Soon - 2025"
            r'Release Date.*?(\w+ \d{1,2},? \d{4})', # "Release Date: January 15, 2025"
            r'Release Date.*?(\w+ \d{4})',           # "Release Date: March 2025"
            r'Release Date.*?(Q[1-4] \d{4})',        # "Release Date: Q2 2025"
            # Removed the problematic "Available" patterns that match system requirements
        ]
        
        # Look for date patterns in page text
        for pattern in coming_soon_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                # Validate the date string before returning it
                if is_valid_date_string(date_str):
                    return date_str
        
        # Method 2: Look for release date in structured elements
        release_date_element = soup.find('div', class_='release_date')
        if release_date_element:
            date_text = release_date_element.get_text(strip=True)
            # Extract date from "Release Date: DATE" format
            date_match = re.search(r'Release Date:?\s*(.+)', date_text, re.IGNORECASE)
            if date_match:
                extracted_date = date_match.group(1).strip()
                if is_valid_date_string(extracted_date):
                    return extracted_date
        
        # Method 3: Look for coming soon date in meta description or other elements
        coming_soon_element = soup.find('div', string=re.compile(r'Coming Soon', re.IGNORECASE))
        if coming_soon_element:
            # Look for dates in the vicinity of "Coming Soon" text
            context = coming_soon_element.get_text() if coming_soon_element else ''
            for pattern in [r'(\w+ \d{1,2},? \d{4})', r'(\w+ \d{4})', r'(Q[1-4] \d{4})']:
                match = re.search(pattern, context)
                if match:
                    extracted_date = match.group(1).strip()
                    if is_valid_date_string(extracted_date):
                        return extracted_date
        
        return None
    
    def process_videos(self, channel_url: str, max_new_videos: Optional[int] = None):
        """Process YouTube videos only"""
        logging.info(f"Processing videos from channel: {channel_url}")
        
        if not max_new_videos:
            max_new_videos = 50
        
        known_video_ids = set(self.videos_data['videos'].keys())
        new_videos_processed = 0
        batch_size = min(max_new_videos * 2, 50)  # Fetch more IDs to account for known videos
        videos_fetched_total = 0
        consecutive_known_batches = 0
        
        # Smart starting position: if we have videos, start from a reasonable offset
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
                logging.info(f"No new videos in this batch, continuing deeper into channel history")
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
                
                video_date = video.get('published_at', '')[:10] if video.get('published_at') else 'Unknown Date'
                logging.info(f"Processing: {video.get('title', 'Unknown Title')} ({video_date})")
                
                # Get full video metadata
                try:
                    full_video = self.get_full_video_metadata(video_id)
                    if full_video:
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
            'crazygames_url': None,
            'last_updated': datetime.now().isoformat()
        }
        
        # Priority: Steam > Itch.io > CrazyGames, but store all found links
        if game_links.get('steam'):
            app_id = re.search(r'/app/(\d+)', game_links['steam']).group(1)
            video_data['steam_app_id'] = app_id
            # Store other platforms as secondary
            if game_links.get('itch'):
                video_data['itch_url'] = game_links['itch']
                video_data['itch_is_demo'] = True
            if game_links.get('crazygames'):
                video_data['crazygames_url'] = game_links['crazygames']
            logging.info(f"  Found Steam link: {game_links['steam']}" + 
                        (f", Itch.io: {game_links['itch']}" if game_links.get('itch') else "") +
                        (f", CrazyGames: {game_links['crazygames']}" if game_links.get('crazygames') else ""))
        elif game_links.get('itch'):
            video_data['itch_url'] = game_links['itch']
            if game_links.get('crazygames'):
                video_data['crazygames_url'] = game_links['crazygames']
            logging.info(f"  Found Itch.io link: {game_links['itch']}" +
                        (f", CrazyGames: {game_links['crazygames']}" if game_links.get('crazygames') else ""))
            
            # Fetch itch.io metadata if not already cached
            if game_links['itch'] not in self.other_games_data['games']:
                logging.info(f"  Fetching Itch.io metadata...")
                itch_data = self.fetch_itch_data(game_links['itch'])
                if itch_data:
                    itch_data['last_updated'] = datetime.now().isoformat()
                    self.other_games_data['games'][game_links['itch']] = itch_data
                    self.save_other_games()
                    
        elif game_links.get('crazygames'):
            video_data['crazygames_url'] = game_links['crazygames']
            logging.info(f"  Found CrazyGames link: {game_links['crazygames']}")
            
            # Fetch CrazyGames metadata if not already cached
            if game_links['crazygames'] not in self.other_games_data['games']:
                logging.info(f"  Fetching CrazyGames metadata...")
                crazygames_data = self.fetch_crazygames_data(game_links['crazygames'])
                if crazygames_data:
                    crazygames_data['last_updated'] = datetime.now().isoformat()
                    self.other_games_data['games'][game_links['crazygames']] = crazygames_data
                    self.save_other_games()
                    
        else:
            logging.info(f"  No game links found")
        
        return video_data
    
    def reprocess_video_descriptions(self):
        """Reprocess existing video descriptions to extract game links with current logic"""
        logging.info("Reprocessing existing video descriptions")
        
        videos_processed = 0
        updated_count = 0
        
        for video_id, video_data in self.videos_data['videos'].items():
            video_date = video_data.get('published_at', '')[:10] if video_data.get('published_at') else 'Unknown Date'
            logging.info(f"Reprocessing: {video_data.get('title', 'Unknown Title')} ({video_date})")
            
            # Store original data for comparison
            original_steam_id = video_data.get('steam_app_id')
            original_itch_url = video_data.get('itch_url')
            original_itch_is_demo = video_data.get('itch_is_demo', False)
            original_crazygames_url = video_data.get('crazygames_url')
            
            # Reprocess with current logic
            updated_video_data = self._process_video_game_links(video_data)
            
            # Check if anything changed
            if (updated_video_data['steam_app_id'] != original_steam_id or
                updated_video_data['itch_url'] != original_itch_url or
                updated_video_data['itch_is_demo'] != original_itch_is_demo or
                updated_video_data['crazygames_url'] != original_crazygames_url):
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
                        ).isoformat() if entry.get('timestamp') else '',
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
                                    full_game_name = self.steam_data['games'][full_game_id].get('name', 'Unknown Game')
                                    days_ago = (datetime.now() - last_updated_date).days
                                    logging.info(f"  Skipping full game {full_game_id} ({full_game_name}) - updated {days_ago} days ago")
                        
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
                                    demo_name = self.steam_data['games'][demo_id].get('name', 'Unknown Game')
                                    days_ago = (datetime.now() - last_updated_date).days
                                    logging.info(f"  Skipping demo {demo_id} ({demo_name}) - updated {days_ago} days ago")
                        
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
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        
        for channel_id in channels_config.keys():
            videos_file = os.path.join(project_root, 'data', f'videos-{channel_id}.json')
            if not os.path.exists(videos_file):
                print(f"⚠️  Missing video file for channel {channel_id}: {videos_file}")
                total_issues += 1
                continue
                
            with open(videos_file, 'r') as f:
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
        
        # 2. Check Steam games for missing metadata
        print("\n\n2. CHECKING STEAM GAMES METADATA")
        print("-" * 50)
        
        steam_issues = 0
        required_steam_fields = ['name', 'steam_app_id', 'tags', 'positive_review_percentage']
        optional_steam_fields = ['header_image', 'review_summary', 'price']
        
        for app_id, game in self.steam_data.get('games', {}).items():
            missing_required = []
            missing_optional = []
            
            # Check required fields, but skip positive_review_percentage for coming soon games
            for field in required_steam_fields:
                if not game.get(field):
                    # Coming soon games legitimately don't have review data
                    if field == 'positive_review_percentage' and game.get('coming_soon'):
                        continue
                    # Games with insufficient reviews also legitimately don't have percentage scores
                    if field == 'positive_review_percentage' and game.get('insufficient_reviews'):
                        continue
                    # Games with no reviews also legitimately don't have percentage scores
                    if field == 'positive_review_percentage' and game.get('review_count') == 0:
                        continue
                    missing_required.append(field)
            
            for field in optional_steam_fields:
                if not game.get(field):
                    # Coming soon games legitimately don't have price or review data
                    if game.get('coming_soon') and field in ['review_summary', 'price']:
                        continue
                    missing_optional.append(field)
            
            if missing_required:
                print(f"❌ Steam game {app_id} ({game.get('name', 'Unknown')}) missing required: {', '.join(missing_required)}")
                steam_issues += 1
                total_issues += 1
            elif missing_optional:
                print(f"⚠️  Steam game {app_id} ({game.get('name', 'Unknown')}) missing optional: {', '.join(missing_optional)}")
        
        # Count coming soon games and insufficient reviews for informational purposes
        coming_soon_count = sum(1 for game in self.steam_data.get('games', {}).values() if game.get('coming_soon'))
        insufficient_reviews_count = sum(1 for game in self.steam_data.get('games', {}).values() if game.get('insufficient_reviews'))
        no_reviews_count = sum(1 for game in self.steam_data.get('games', {}).values() if game.get('review_count') == 0)
        
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
        
        # 3. Check other games (Itch.io, CrazyGames) for missing metadata
        print("\n\n3. CHECKING OTHER GAMES METADATA")
        print("-" * 50)
        
        other_issues = 0
        required_other_fields = ['name', 'platform', 'tags']
        optional_other_fields = ['header_image', 'positive_review_percentage', 'review_count']
        
        for url, game in self.other_games_data.get('games', {}).items():
            missing_required = []
            missing_optional = []
            
            for field in required_other_fields:
                if not game.get(field) or (field == 'tags' and len(game.get(field, [])) == 0):
                    missing_required.append(field)
            
            for field in optional_other_fields:
                if not game.get(field):
                    missing_optional.append(field)
            
            if missing_required:
                print(f"❌ {game.get('platform', 'Unknown')} game '{game.get('name', 'Unknown')}' missing required: {', '.join(missing_required)}")
                other_issues += 1
                total_issues += 1
            elif missing_optional:
                print(f"⚠️  {game.get('platform', 'Unknown')} game '{game.get('name', 'Unknown')}' missing optional: {', '.join(missing_optional)}")
        
        print(f"\nOther games checked: {len(self.other_games_data.get('games', {}))}")
        if other_issues == 0:
            print("✅ All other games have required metadata")
        else:
            print(f"❌ {other_issues} other games have missing required metadata")
        
        # 4. Check for stale data
        print("\n\n4. CHECKING FOR STALE DATA")
        print("-" * 50)
        
        stale_threshold = datetime.now() - timedelta(days=30)  # 30 days
        stale_steam = 0
        stale_other = 0
        
        for app_id, game in self.steam_data.get('games', {}).items():
            last_updated = game.get('last_updated')
            if last_updated:
                try:
                    last_updated_date = datetime.fromisoformat(last_updated)
                    if last_updated_date < stale_threshold:
                        days_old = (datetime.now() - last_updated_date).days
                        print(f"🕐 Steam game {app_id} ({game.get('name', 'Unknown')}) is {days_old} days old")
                        stale_steam += 1
                except ValueError:
                    print(f"❌ Steam game {app_id} has invalid last_updated format: {last_updated}")
                    total_issues += 1
        
        for url, game in self.other_games_data.get('games', {}).items():
            last_updated = game.get('last_updated')
            if last_updated:
                try:
                    last_updated_date = datetime.fromisoformat(last_updated)
                    if last_updated_date < stale_threshold:
                        days_old = (datetime.now() - last_updated_date).days
                        print(f"🕐 {game.get('platform', 'Unknown')} game '{game.get('name', 'Unknown')}' is {days_old} days old")
                        stale_other += 1
                except ValueError:
                    print(f"❌ {game.get('platform', 'Unknown')} game has invalid last_updated format: {last_updated}")
                    total_issues += 1
        
        if stale_steam == 0 and stale_other == 0:
            print("✅ No stale game data found")
        else:
            print(f"📊 {stale_steam} Steam games and {stale_other} other games are older than 30 days")
        
        # 5. Summary
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
    
    def extract_potential_game_names(self, title: str) -> List[str]:
        """Extract potential game names from video titles"""
        # Common patterns in gaming videos
        patterns = [
            r'\|\s*([^|]+?)\s*$',                                    # "Something | Game Name"
            r'^([^!|]+?)(?:\s+is\s+|\s+Review|\s+Gameplay|\s*\|)',  # "Game Name is Amazing!" or "Game Name | Channel"
            r'^\s*(.+?)\s+(?:Review|Gameplay|First Impression)',     # "Game Name Review"
            r'^(?:Playing|I Played|This)\s+(.+?)\s+(?:for|and|is)', # "I Played Game Name for..."
            r'^(.+?)\s+(?:Has|Will|Can|Gets)',                      # "Game Name Has Amazing Features"
        ]
        
        potential_names = []
        
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Clean up common words and punctuation
                name = re.sub(r'\b(the|a|an|this|new|amazing|incredible|insane|crazy)\b', '', name, flags=re.IGNORECASE)
                name = re.sub(r'[!?]+$', '', name)  # Remove trailing exclamation/question marks
                name = re.sub(r'\s+', ' ', name).strip()
                if len(name) > 3 and name not in potential_names:  # Avoid very short matches and duplicates
                    potential_names.append(name)
        
        return potential_names
    
    def infer_games_from_titles(self, channels_config: Dict):
        """Infer games from video titles using Steam search"""
        print("\n" + "="*80)
        print("GAME INFERENCE FROM VIDEO TITLES")
        print("="*80)
        
        total_videos_processed = 0
        games_found = 0
        
        # Load all channel video files
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        
        for channel_id in channels_config.keys():
            videos_file = os.path.join(project_root, 'data', f'videos-{channel_id}.json')
            if not os.path.exists(videos_file):
                print(f"⚠️  Missing video file for channel {channel_id}: {videos_file}")
                continue
                
            with open(videos_file, 'r') as f:
                channel_data = json.load(f)
            
            print(f"\n📺 Processing channel: {channel_id}")
            
            videos_without_games = []
            for video_id, video in channel_data.get('videos', {}).items():
                has_game = bool(video.get('steam_app_id') or video.get('itch_url') or video.get('crazygames_url'))
                if not has_game:
                    videos_without_games.append((video_id, video))
            
            if not videos_without_games:
                print("   ✅ All videos already have game data")
                continue
            
            print(f"   🔍 Found {len(videos_without_games)} videos without game data")
            
            channel_games_found = 0
            for video_id, video in videos_without_games:
                total_videos_processed += 1
                title = video.get('title', '')
                
                print(f"\n   📹 {title}")
                
                # Extract potential game names
                potential_names = self.extract_potential_game_names(title)
                if not potential_names:
                    print("      ❌ No potential game names found in title")
                    continue
                
                print(f"      🎯 Potential names: {potential_names}")
                
                # Search Steam for each potential name
                best_match = None
                best_confidence = 0
                
                for name in potential_names:
                    results = self.search_steam_games(name)
                    if results:
                        # Simple confidence scoring based on name similarity
                        for result in results[:3]:  # Check top 3 results
                            game_name = result['name'].lower()
                            search_name = name.lower()
                            
                            # Calculate similarity (simple word overlap)
                            search_words = set(search_name.split())
                            game_words = set(game_name.split())
                            overlap = len(search_words & game_words)
                            confidence = overlap / max(len(search_words), len(game_words))
                            
                            if confidence > best_confidence and confidence > 0.5:  # At least 50% word overlap
                                best_match = result
                                best_confidence = confidence
                
                if best_match:
                    app_id = str(best_match['id'])
                    game_name = best_match['name']
                    print(f"      ✅ Found match: {game_name} (App ID: {app_id}, confidence: {best_confidence:.2f})")
                    
                    # Update video data
                    video['steam_app_id'] = app_id
                    video['inferred_game'] = True  # Mark as inferred for review
                    video['last_updated'] = datetime.now().isoformat()
                    
                    # Fetch full game data
                    try:
                        steam_url = f"https://store.steampowered.com/app/{app_id}"
                        steam_data = self.fetch_steam_data(steam_url)
                        if steam_data:
                            steam_data['last_updated'] = datetime.now().isoformat()
                            self.steam_data['games'][app_id] = steam_data
                            print(f"      📊 Fetched game metadata: {steam_data.get('name', 'Unknown')}")
                    except Exception as e:
                        logging.error(f"      ❌ Error fetching Steam data for {app_id}: {e}")
                    
                    games_found += 1
                    channel_games_found += 1
                else:
                    print("      ❌ No confident matches found on Steam")
            
            # Save updated video data
            if channel_games_found > 0:
                with open(videos_file, 'w') as f:
                    json.dump(channel_data, f, indent=2)
                print(f"   💾 Saved {channel_games_found} game inferences for {channel_id}")
        
        # Save updated Steam data
        if games_found > 0:
            self.save_steam()
        
        print(f"\n" + "="*80)
        print("GAME INFERENCE SUMMARY")
        print("="*80)
        print(f"📊 Videos processed: {total_videos_processed}")
        print(f"🎮 Games found: {games_found}")
        if games_found > 0:
            print(f"✅ Success rate: {(games_found/total_videos_processed)*100:.1f}%")
            print("\n⚠️  Note: Inferred games are marked with 'inferred_game: true' for review")
        print("="*80)
        
        return games_found


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
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        config_path = os.path.join(project_root, 'config.json')
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Process each enabled channel
        steam_scraper = None
        for channel_id, channel_config in config['channels'].items():
            if not channel_config.get('enabled', True):
                logging.info(f"Skipping disabled channel: {channel_id}")
                continue
            
            logging.info(f"Cron mode: processing channel {channel_id}")
            scraper = YouTubeSteamScraper(channel_id)
            
            # Process recent videos only (smaller batch for cron)
            scraper.process_videos(channel_config['url'], max_new_videos=10)
            
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
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        config_path = os.path.join(project_root, 'config.json')
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Get first available channel
        first_channel = next(iter(config['channels'].keys()))
        scraper = YouTubeSteamScraper(first_channel)
        
        steam_url = f"https://store.steampowered.com/app/{args.app_id}"
        logging.info(f"Fetching single app: {args.app_id}")
        
        try:
            steam_data = scraper.fetch_steam_data(steam_url)
            if steam_data:
                steam_data['last_updated'] = datetime.now().isoformat()
                scraper.steam_data['games'][args.app_id] = steam_data
                scraper.save_steam()
                logging.info(f"Updated: {steam_data.get('name', 'Unknown')}")
            else:
                logging.warning(f"Failed to fetch data for app {args.app_id}")
        except Exception as e:
            logging.error(f"Error fetching app {args.app_id}: {e}")
    
    elif args.mode == 'data-quality':
        # Load config directly
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        config_path = os.path.join(project_root, 'config.json')
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Use first available channel to access data files
        first_channel = next(iter(config['channels'].keys()))
        scraper = YouTubeSteamScraper(first_channel)
        
        logging.info("Data quality check: analyzing all channels and games")
        scraper.check_data_quality(config['channels'])
    
    elif args.mode == 'infer-games':
        # Load config directly
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        config_path = os.path.join(project_root, 'config.json')
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Use first available channel to access data files
        first_channel = next(iter(config['channels'].keys()))
        scraper = YouTubeSteamScraper(first_channel)
        
        logging.info("Game inference: searching for games in video titles")
        scraper.infer_games_from_titles(config['channels'])