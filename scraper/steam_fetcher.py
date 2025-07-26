"""
Steam data fetching and parsing functionality
"""

import logging
import re
import time
from typing import TYPE_CHECKING, Any

import requests
from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from .data_manager import DataManager

from .base_fetcher import BaseFetcher
from .models import SteamGameData
from .utils import extract_steam_app_id, is_valid_date_string


class SteamDataFetcher(BaseFetcher):
    """Handles fetching and parsing Steam game data"""

    def __init__(self, data_manager: 'DataManager | None' = None) -> None:
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.cookies = {'birthtime': '0', 'mature_content': '1'}
        self.max_retries = 10
        self.base_delay = 16
        self.data_manager = data_manager

    def _make_request_with_retry(self, url: str, request_type: str = "API", **kwargs: Any) -> requests.Response | None:
        """Make HTTP request with exponential backoff retry logic"""
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, timeout=30, **kwargs)

                if response.status_code == 429:  # Rate limited
                    delay = self.base_delay * (2 ** attempt)
                    logging.warning(f"Rate limited for {request_type} request (attempt {attempt + 1}), waiting {delay}s")
                    time.sleep(delay)
                    continue

                if response.status_code != 200:
                    if attempt == self.max_retries - 1:  # Last attempt
                        logging.error(f"Failed {request_type} request after {self.max_retries} attempts: HTTP {response.status_code}")
                        return None

                    delay = self.base_delay * (2 ** attempt)
                    logging.warning(f"HTTP {response.status_code} for {request_type} request (attempt {attempt + 1}), retrying in {delay}s")
                    time.sleep(delay)
                    continue

                return response

            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:  # Last attempt
                    logging.error(f"Network error for {request_type} request after {self.max_retries} attempts: {e}")
                    return None

                delay = self.base_delay * (2 ** attempt)
                logging.warning(f"Network error for {request_type} request (attempt {attempt + 1}): {e}, retrying in {delay}s")
                time.sleep(delay)

        return None

    def fetch_data(self, steam_url: str, fetch_usd: bool = False, existing_data: 'SteamGameData | None' = None) -> SteamGameData | None:
        """Fetch complete game data from Steam with EUR by default"""
        try:
            app_id = extract_steam_app_id(steam_url)
            if not app_id:
                logging.error(f"Could not extract app ID from Steam URL: {steam_url}")
                return None

            # First, get basic data from Steam API with EUR (Austria)
            api_data_eur = self._fetch_api_data(app_id, 'at')
            if not api_data_eur:
                # Only create stub entry if the app is referenced by videos
                if self.data_manager and self.data_manager.is_game_referenced_by_videos('steam', app_id):
                    return self._create_stub_entry(app_id, steam_url, "Steam API fetch failed", existing_data=existing_data)
                else:
                    logging.info(f"Skipping stub creation for {app_id} - not referenced by any videos")
                    return None

            # Check if this is DLC or soundtrack - redirect to base game
            app_type = api_data_eur.get('type', '').lower()
            if app_type in ['dlc', 'music']:
                fullgame = api_data_eur.get('fullgame')
                if fullgame and fullgame.get('appid'):
                    base_game_id = fullgame['appid']
                    base_game_name = fullgame.get('name', 'Unknown Base Game')
                    content_type = 'DLC' if app_type == 'dlc' else 'Soundtrack'
                    logging.info(f"Redirecting {content_type} {app_id} to base game {base_game_id} ({base_game_name})")

                    # Create stub entry for the DLC/soundtrack pointing to base game
                    return self._create_stub_entry(app_id, steam_url, f"{content_type} redirected to base game", resolved_to=base_game_id, existing_data=existing_data)
                else:
                    # No base game found, treat as regular content
                    logging.warning(f"Found {app_type} {app_id} but no base game information available")

            # Create initial game data from API
            game_data = self._parse_api_data(api_data_eur, app_id, steam_url)

            # Fetch USD price if requested
            if fetch_usd:
                api_data_usd = self._fetch_api_data(app_id, 'us')
                if api_data_usd:
                    game_data.price_usd = self._get_price(api_data_usd)

            # Fetch additional data from store page
            store_data = self._fetch_store_page_data(steam_url, api_data_eur)

            # Merge store page data into game data
            self._merge_store_data(game_data, store_data)

            return game_data

        except Exception as e:
            logging.error(f"Error fetching Steam data for {steam_url}: {e}")
            app_id = extract_steam_app_id(steam_url)
            if app_id:
                # Only create stub entry if the app is referenced by videos
                if self.data_manager and self.data_manager.is_game_referenced_by_videos('steam', app_id):
                    return self._create_stub_entry(app_id, steam_url, f"Exception: {e!s}", existing_data=existing_data)
                else:
                    logging.info(f"Skipping stub creation for {app_id} - not referenced by any videos")
                    return None
            return None

    def _fetch_api_data(self, app_id: str, country_code: str = 'at') -> dict | None:
        """Fetch basic data from Steam API with country code and retry logic"""
        api_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc={country_code}"

        response = self._make_request_with_retry(api_url, f"Steam API (app {app_id})")
        if not response:
            return None

        try:
            data = response.json()
        except (ValueError, TypeError) as e:
            logging.error(f"Steam API returned invalid JSON for app {app_id}: {e}")
            return None

        if not isinstance(data, dict):
            logging.error(f"Steam API returned non-dict response for app {app_id}")
            return None

        app_info = data.get(app_id)
        if not isinstance(app_info, dict):
            logging.error(f"Steam API missing app info for app {app_id}")
            return None

        if not app_info.get('success'):
            logging.warning(f"Steam API returned success=false for app {app_id}")
            return None

        app_data = app_info.get('data')
        if not isinstance(app_data, dict):
            logging.error(f"Steam API app data is not a dict for app {app_id}")
            return None

        return app_data

    def _parse_api_data(self, app_data: dict, app_id: str, steam_url: str) -> SteamGameData:
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
            price_eur=self._get_price(app_data),
            header_image=app_data.get('header_image', '')
        )

    def _get_price(self, app_data: dict) -> str | None:
        """Extract price information"""
        if app_data.get('is_free'):
            return "Free"

        price_data = app_data.get('price_overview', {})
        if price_data:
            price = price_data.get('final_formatted', '')
            return str(price) if price is not None else None

        return None

    def _fetch_store_page_data(self, steam_url: str, app_data: dict | None = None) -> dict:
        """Scrape additional data from Steam store page with retry logic"""
        response = self._make_request_with_retry(
            steam_url,
            "Steam store page",
            headers=self.headers,
            cookies=self.cookies
        )
        if not response:
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

    def _extract_tags(self, soup: BeautifulSoup) -> dict:
        """Extract Steam tags"""
        tags = []
        tag_elements = soup.select('a.app_tag')
        for tag in tag_elements[:10]:  # Top 10 tags
            tag_text = tag.text.strip()
            if tag_text:
                tags.append(tag_text)
        return {'tags': tags}

    def _extract_demo_info(self, soup: BeautifulSoup, page_text: str, html_content: str, app_data: dict | None = None) -> dict[str, Any]:
        """Extract demo-related information"""
        result: dict[str, Any] = {}

        # Check if this IS a demo first
        categories_from_api = [c.get('description', '') for c in app_data.get('categories', [])] if app_data else []

        # Steam categories are 100% reliable for demo detection
        is_demo = any('demo' in cat.lower() for cat in categories_from_api)
        result['is_demo'] = is_demo

        # If this is a demo, try to find the full game
        if is_demo:
            full_game_id = self._find_full_game_id(soup, page_text)
            if full_game_id:
                result['full_game_app_id'] = full_game_id
        else:
            # For non-demo apps, try to find demo app ID - only set has_demo if we find one
            demo_app_id = self._find_demo_app_id(soup, page_text, html_content)
            if demo_app_id:
                result['has_demo'] = True
                result['demo_app_id'] = demo_app_id
            else:
                result['has_demo'] = False

        return result

    def _extract_early_access(self, soup: BeautifulSoup) -> dict:
        """Extract early access information"""
        early_access = soup.find('div', class_='early_access_header')
        return {'is_early_access': early_access is not None}

    def _extract_review_data(self, page_text: str) -> dict:
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

    def _extract_insufficient_reviews(self, page_text: str, result: dict) -> None:
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

    def _extract_release_info(self, soup: BeautifulSoup, page_text: str, app_data: dict | None = None) -> dict:
        """Extract release date information for coming soon games"""
        result = {}

        if app_data and app_data.get('release_date', {}).get('coming_soon'):
            planned_date = self._extract_planned_release_date(soup, page_text)
            if planned_date:
                result['planned_release_date'] = planned_date

        return result

    def _extract_planned_release_date(self, soup: BeautifulSoup, page_text: str) -> str | None:
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

    def _find_demo_app_id(self, soup: BeautifulSoup, page_text: str, html_content: str) -> str | None:
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

    def _find_full_game_id(self, soup: BeautifulSoup, page_text: str) -> str | None:
        """Try to find the full game app ID from a demo page"""
        # Look for Community Hub link
        community_links = soup.find_all('a', href=re.compile(r'steamcommunity\.com/app/(\d+)'))
        for link in community_links:
            href = self.safe_get_attr(link, 'href')
            match = re.search(r'/app/(\d+)', href)
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

    def _get_current_app_id(self, soup: BeautifulSoup) -> str | None:
        """Get the current app ID from the page"""
        canonical_link = soup.find('link', {'rel': 'canonical'})
        if canonical_link:
            href = self.safe_get_attr(canonical_link, 'href')
            match = re.search(r'/app/(\d+)', href)
            if match:
                return match.group(1)
        return None

    def _search_html_for_demo(self, html_content: str, current_id: str | None) -> str | None:
        """Search HTML content for demo app IDs"""
        # Steam protocol install links - look for any steam://install/ patterns
        steam_protocol_pattern = r'steam://install/(\d+)'
        matches = re.findall(steam_protocol_pattern, html_content)
        for demo_id in matches:
            if str(demo_id) != current_id:
                return str(demo_id)

        # JavaScript modal patterns - handle mixed quotes
        js_modal_patterns = [
            r'ShowGotSteamModal.*?[\'"]steam://install/(\d+)[\'"]',
            r'ShowGotSteamModal\s*\(\s*[\'"]steam://install/(\d+)[\'"]',
            r'steam://install/(\d+).*?ShowGotSteamModal',
        ]
        for pattern in js_modal_patterns:
            matches = re.findall(pattern, html_content)
            for demo_id in matches:
                if str(demo_id) != current_id:
                    return str(demo_id)

        # Demo URL patterns
        demo_url_patterns = [
            r'store\.steampowered\.com/app/(\d+)/[^"\']*[Dd]emo[^"\'/]*/?',
            r'/app/(\d+)/.*?[Dd]emo',
            r'[Dd]emo.*?/app/(\d+)',
        ]
        for pattern in demo_url_patterns:
            matches = re.findall(pattern, html_content)
            for demo_id in matches:
                if str(demo_id) != current_id:
                    return str(demo_id)

        return None

    def _search_text_for_demo(self, page_text: str, current_id: str | None) -> str | None:
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

    def _search_elements_for_demo(self, soup: BeautifulSoup, current_id: str | None) -> str | None:
        """Search HTML elements for demo links"""
        # Look for demo links
        demo_links = soup.find_all('a', href=re.compile(r'store\.steampowered\.com/app/(\d+)'))
        for link in demo_links:
            href = self.safe_get_attr(link, 'href')
            link_text = self.safe_get_text(link).lower()
            if 'demo' in link_text or 'demo' in href.lower():
                match = re.search(r'/app/(\d+)', href)
                if match:
                    demo_id = match.group(1)
                    if demo_id != current_id:
                        return demo_id

        # Look for demo button classes
        demo_elements = soup.find_all(['a', 'div'], class_=re.compile(r'demo', re.IGNORECASE))
        for element in demo_elements:
            href = self.safe_get_attr(element, 'href')
            if 'store.steampowered.com/app/' in href:
                match = re.search(r'/app/(\d+)', href)
                if match:
                    return match.group(1)

        return None

    def _merge_store_data(self, game_data: SteamGameData, store_data: dict) -> None:
        """Merge store page data into game data object"""
        for key, value in store_data.items():
            if hasattr(game_data, key):
                setattr(game_data, key, value)

    def _create_stub_entry(self, app_id: str, steam_url: str, reason: str, resolved_to: str | None = None, existing_data: 'SteamGameData | None' = None) -> SteamGameData:
        """Create a stub entry for failed fetches or redirects, preserving relationship fields from existing data"""
        logging.info(f"Creating stub entry for Steam app {app_id}: {reason}")

        # Use different naming for redirects vs failures
        if resolved_to:
            name = f"[REDIRECT] {app_id} -> {resolved_to}"
        else:
            name = f"[FAILED FETCH] {app_id}"

        # Preserve relationship fields from existing data if available
        preserved_full_game_app_id = existing_data.full_game_app_id if existing_data else None
        preserved_demo_app_id = existing_data.demo_app_id if existing_data else None
        preserved_is_demo = existing_data.is_demo if existing_data else False
        preserved_itch_url = existing_data.itch_url if existing_data else None
        preserved_is_free = existing_data.is_free if existing_data else False

        # For failed demo fetches, set resolved_to to the main game (following existing pattern)
        if not resolved_to and existing_data and existing_data.is_demo and existing_data.full_game_app_id:
            resolved_to = existing_data.full_game_app_id
            # Update the name to indicate the demo was removed
            if reason == "Steam API fetch failed":
                name = f"[REMOVED] {existing_data.name}" if existing_data.name and not existing_data.name.startswith('[') else name

        return SteamGameData(
            steam_app_id=app_id,
            steam_url=steam_url,
            name=name,
            is_stub=True,
            stub_reason=reason,
            resolved_to=resolved_to,
            # Preserve important relationship and stable data
            full_game_app_id=preserved_full_game_app_id,
            demo_app_id=preserved_demo_app_id,
            is_demo=preserved_is_demo,
            itch_url=preserved_itch_url,
            is_free=preserved_is_free
        )
