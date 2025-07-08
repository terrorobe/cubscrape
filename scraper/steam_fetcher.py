"""
Steam data fetching and parsing functionality
"""

import re
import json
import logging
from typing import Dict, Optional
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from models import SteamGameData
from utils import is_valid_date_string, extract_steam_app_id


class SteamDataFetcher:
    """Handles fetching and parsing Steam game data"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.cookies = {'birthtime': '0', 'mature_content': '1'}
    
    def fetch_data(self, steam_url: str) -> Optional[SteamGameData]:
        """Fetch complete game data from Steam"""
        try:
            app_id = extract_steam_app_id(steam_url)
            
            # First, get basic data from Steam API
            api_data = self._fetch_api_data(app_id)
            if not api_data:
                return None
            
            # Create initial game data from API
            game_data = self._parse_api_data(api_data, app_id, steam_url)
            
            # Fetch additional data from store page
            store_data = self._fetch_store_page_data(steam_url, api_data)
            
            # Merge store page data into game data
            self._merge_store_data(game_data, store_data)
            
            return game_data
            
        except Exception as e:
            logging.error(f"Error fetching Steam data for {steam_url}: {e}")
            return None
    
    def _fetch_api_data(self, app_id: str) -> Optional[Dict]:
        """Fetch basic data from Steam API"""
        api_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
        response = requests.get(api_url)
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        if not data.get(app_id, {}).get('success'):
            return None
            
        return data[app_id]['data']
    
    def _parse_api_data(self, app_data: Dict, app_id: str, steam_url: str) -> SteamGameData:
        """Parse API data into SteamGameData object"""
        return SteamGameData(
            steam_app_id=app_id,
            steam_url=steam_url,
            name=app_data.get('name', ''),
            is_free=app_data.get('is_free', False),
            release_date=app_data.get('release_date', {}).get('date', ''),
            coming_soon=app_data.get('release_date', {}).get('coming_soon', False),
            genres=[g['description'] for g in app_data.get('genres', [])],
            categories=[c['description'] for c in app_data.get('categories', [])],
            developers=app_data.get('developers', []),
            publishers=app_data.get('publishers', []),
            price=self._get_price(app_data),
            header_image=app_data.get('header_image', '')
        )
    
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
        response = requests.get(steam_url, headers=self.headers, cookies=self.cookies)
        if response.status_code != 200:
            return {}
            
        soup = BeautifulSoup(response.content, 'lxml')
        html_content = response.text
        page_text = soup.get_text()
        
        result = {}
        
        # Extract various data types
        result.update(self._extract_tags(soup))
        result.update(self._extract_demo_info(soup, page_text, html_content, app_data))
        result.update(self._extract_early_access(soup))
        result.update(self._extract_review_data(page_text))
        result.update(self._extract_release_info(soup, page_text, app_data))
        
        return result
    
    def _extract_tags(self, soup: BeautifulSoup) -> Dict:
        """Extract Steam tags"""
        tags = []
        tag_elements = soup.select('a.app_tag')
        for tag in tag_elements[:10]:  # Top 10 tags
            tag_text = tag.text.strip()
            if tag_text:
                tags.append(tag_text)
        return {'tags': tags}
    
    def _extract_demo_info(self, soup: BeautifulSoup, page_text: str, html_content: str, app_data: Dict = None) -> Dict:
        """Extract demo-related information"""
        result = {}
        
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
        
        # Check if this IS a demo
        name_from_api = app_data.get('name', '') if app_data else ''
        categories_from_api = [c.get('description', '') for c in app_data.get('categories', [])] if app_data else []
        
        is_demo = any('demo' in cat.lower() for cat in categories_from_api)
        if not is_demo:
            name = name_from_api.lower()
            is_demo = 'demo' in name or 'Demo' in page_text[:2000]
        result['is_demo'] = is_demo
        
        # If this is a demo, try to find the full game
        if is_demo:
            full_game_id = self._find_full_game_id(soup, page_text)
            if full_game_id:
                result['full_game_app_id'] = full_game_id
        
        return result
    
    def _extract_early_access(self, soup: BeautifulSoup) -> Dict:
        """Extract early access information"""
        early_access = soup.find('div', class_='early_access_header')
        return {'is_early_access': early_access is not None}
    
    def _extract_review_data(self, page_text: str) -> Dict:
        """Extract review data from page text"""
        result = {}
        
        # Look for Overall Reviews data
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
            
            result.update({
                'positive_review_percentage': percentage,
                'review_count': count,
                'review_summary': summary
            })
            
            # Also store recent data if available
            if recent_match:
                recent_summary = recent_match.group(1).strip()
                recent_count = int(recent_match.group(2).replace(',', ''))
                recent_percentage = int(recent_match.group(3))
                result.update({
                    'recent_review_percentage': recent_percentage,
                    'recent_review_count': recent_count,
                    'recent_review_summary': recent_summary
                })
                
        elif recent_match:
            # Only recent data available
            summary = recent_match.group(1).strip()
            count = int(recent_match.group(2).replace(',', ''))
            percentage = int(recent_match.group(3))
            
            result.update({
                'positive_review_percentage': percentage,
                'review_count': count,
                'review_summary': summary
            })
        else:
            # Check for insufficient reviews or no reviews
            self._extract_insufficient_reviews(page_text, result)
        
        return result
    
    def _extract_insufficient_reviews(self, page_text: str, result: Dict):
        """Extract information about insufficient or missing reviews"""
        insufficient_review_patterns = [
            r'Need more user reviews to generate a score.*?(\d+)\s*user review',
            r'(\d+)\s*user review.*?Need more user reviews',
            r'(\d+)\s*review.*?Need more.*?score',
        ]
        
        for pattern in insufficient_review_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE | re.DOTALL)
            if match:
                review_count = int(match.group(1))
                result.update({
                    'review_count': review_count,
                    'insufficient_reviews': True,
                    'review_summary': 'Need more reviews for score'
                })
                return
        
        # Check for "No user reviews" case
        if 'No user reviews' in page_text:
            result.update({
                'review_count': 0,
                'review_summary': 'No user reviews'
            })
    
    def _extract_release_info(self, soup: BeautifulSoup, page_text: str, app_data: Dict = None) -> Dict:
        """Extract release date information for coming soon games"""
        result = {}
        
        if app_data and app_data.get('release_date', {}).get('coming_soon'):
            planned_date = self._extract_planned_release_date(soup, page_text)
            if planned_date:
                result['planned_release_date'] = planned_date
        
        return result
    
    def _extract_planned_release_date(self, soup: BeautifulSoup, page_text: str) -> Optional[str]:
        """Extract more specific planned release date for coming soon games"""
        # Coming soon date patterns
        coming_soon_patterns = [
            r'Coming Soon.*?(\w+ \d{1,2},? \d{4})',  # "Coming Soon - January 15, 2025"
            r'Coming Soon.*?(\w+ \d{4})',            # "Coming Soon - March 2025"  
            r'Coming Soon.*?(Q[1-4] \d{4})',         # "Coming Soon - Q2 2025"
            r'Coming Soon.*?(\d{4})',                # "Coming Soon - 2025"
            r'Release Date.*?(\w+ \d{1,2},? \d{4})', # "Release Date: January 15, 2025"
            r'Release Date.*?(\w+ \d{4})',           # "Release Date: March 2025"
            r'Release Date.*?(Q[1-4] \d{4})',        # "Release Date: Q2 2025"
        ]
        
        for pattern in coming_soon_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                if is_valid_date_string(date_str):
                    return date_str
        
        # Look for release date in structured elements
        release_date_element = soup.find('div', class_='release_date')
        if release_date_element:
            date_text = release_date_element.get_text(strip=True)
            date_match = re.search(r'Release Date:?\s*(.+)', date_text, re.IGNORECASE)
            if date_match:
                extracted_date = date_match.group(1).strip()
                if is_valid_date_string(extracted_date):
                    return extracted_date
        
        return None
    
    def _find_demo_app_id(self, soup: BeautifulSoup, page_text: str, html_content: str) -> Optional[str]:
        """Try to find the demo app ID from a main game page"""
        current_app_id = self._get_current_app_id(soup)
        
        # Search raw HTML for demo-related links
        if html_content:
            demo_id = self._search_html_for_demo(html_content, current_app_id)
            if demo_id:
                return demo_id
        
        # Search page text for demo patterns
        demo_id = self._search_text_for_demo(page_text, current_app_id)
        if demo_id:
            return demo_id
        
        # Search HTML elements for demo links
        return self._search_elements_for_demo(soup, current_app_id)
    
    def _find_full_game_id(self, soup: BeautifulSoup, page_text: str) -> Optional[str]:
        """Try to find the full game app ID from a demo page"""
        # Look for Community Hub link
        community_links = soup.find_all('a', href=re.compile(r'steamcommunity\.com/app/(\d+)'))
        for link in community_links:
            match = re.search(r'/app/(\d+)', link.get('href', ''))
            if match:
                return match.group(1)
        
        # Look for main game patterns in text
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
        
        return None
    
    def _get_current_app_id(self, soup: BeautifulSoup) -> Optional[str]:
        """Get the current app ID from the page"""
        canonical_link = soup.find('link', {'rel': 'canonical'})
        if canonical_link:
            match = re.search(r'/app/(\d+)', canonical_link.get('href', ''))
            if match:
                return match.group(1)
        return None
    
    def _search_html_for_demo(self, html_content: str, current_id: Optional[str]) -> Optional[str]:
        """Search HTML content for demo app IDs"""
        # Steam protocol install links
        steam_protocol_pattern = r'steam://install/(\d+)'
        matches = re.findall(steam_protocol_pattern, html_content)
        for demo_id in matches:
            if demo_id != current_id:
                return demo_id
        
        # JavaScript modal patterns
        js_modal_pattern = r'ShowGotSteamModal.*?[\'"]steam://install/(\d+)[\'"]'
        matches = re.findall(js_modal_pattern, html_content)
        for demo_id in matches:
            if demo_id != current_id:
                return demo_id
        
        # Demo URL patterns
        demo_url_pattern = r'store\.steampowered\.com/app/(\d+)/[^"\']*[Dd]emo[^"\'/]*/?'
        matches = re.findall(demo_url_pattern, html_content)
        for demo_id in matches:
            if demo_id != current_id:
                return demo_id
        
        return None
    
    def _search_text_for_demo(self, page_text: str, current_id: Optional[str]) -> Optional[str]:
        """Search page text for demo patterns"""
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
        
        return None
    
    def _search_elements_for_demo(self, soup: BeautifulSoup, current_id: Optional[str]) -> Optional[str]:
        """Search HTML elements for demo links"""
        # Look for demo links
        demo_links = soup.find_all('a', href=re.compile(r'store\.steampowered\.com/app/(\d+)'))
        for link in demo_links:
            href = link.get('href', '')
            link_text = link.get_text().lower()
            if 'demo' in link_text or 'demo' in href.lower():
                match = re.search(r'/app/(\d+)', href)
                if match:
                    demo_id = match.group(1)
                    if demo_id != current_id:
                        return demo_id
        
        # Look for demo button classes
        demo_elements = soup.find_all(['a', 'div'], class_=re.compile(r'demo', re.IGNORECASE))
        for element in demo_elements:
            href = element.get('href', '')
            if 'store.steampowered.com/app/' in href:
                match = re.search(r'/app/(\d+)', href)
                if match:
                    return match.group(1)
        
        return None
    
    def _merge_store_data(self, game_data: SteamGameData, store_data: Dict):
        """Merge store page data into game data object"""
        for key, value in store_data.items():
            if hasattr(game_data, key):
                setattr(game_data, key, value)