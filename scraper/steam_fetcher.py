"""
Steam data fetching and parsing functionality
"""

import json
import logging
import re
import time
from typing import TYPE_CHECKING, Any, TypedDict

import requests
from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from .data_manager import DataManager

from .base_fetcher import BaseFetcher
from .models import SteamGameData
from .steam_price_update_service import PriceUpdateResult
from .utils import extract_steam_app_id, is_valid_date_string


class RemovalDetectionResult(TypedDict):
    """Type definition for removal detection results"""
    removed_count: int
    restored_count: int
    price_updates: int
    removed_games: list[str]
    restored_games: list[str]




class SteamDataFetcher(BaseFetcher):
    """Handles fetching and parsing Steam game data"""

    def __init__(self, data_manager: 'DataManager | None' = None) -> None:
        self.data_manager = data_manager

        # Use centralized configuration
        if data_manager and hasattr(data_manager, 'config_manager'):
            self.config = data_manager.config_manager.get_steam_bulk_config()
        else:
            # Fallback to constants
            from .constants import STEAM_BULK_DEFAULTS
            self.config = STEAM_BULK_DEFAULTS.copy()

        # Initialize shared HTTP client and error handler
        from .bulk_fetch_error_handler import BulkFetchErrorHandler
        from .constants import USER_AGENT
        from .steam_bulk_http_client import SteamBulkHttpClient

        self.http_client = SteamBulkHttpClient(self.config)
        self.error_handler = BulkFetchErrorHandler(self.config)

        # Keep headers and cookies for legacy store page requests
        self.headers = {
            'User-Agent': USER_AGENT
        }
        self.cookies = {'birthtime': '0', 'mature_content': '1'}

    def _make_request_with_retry(self, url: str, request_type: str = "API", **kwargs: Any) -> requests.Response | None:
        """Make HTTP request with unified error handling and retry logic"""
        from .constants import HTTP_TIMEOUT_SECONDS

        for attempt in range(int(self.config['max_retries'])):
            try:
                response = requests.get(url, timeout=HTTP_TIMEOUT_SECONDS, **kwargs)

                if response.status_code == 429:  # Rate limited
                    should_retry, delay = self.error_handler.handle_rate_limit(attempt)
                    if should_retry:
                        time.sleep(delay)
                        continue
                    else:
                        return None

                if response.status_code != 200:
                    should_retry, delay = self.error_handler.handle_standard_retry(
                        response.status_code, attempt, request_type
                    )
                    if should_retry:
                        time.sleep(delay)
                        continue
                    else:
                        return None

                return response

            except requests.exceptions.RequestException as e:
                should_retry, delay = self.error_handler.handle_request_exception(e, attempt, request_type)
                if should_retry:
                    time.sleep(delay)
                    continue
                else:
                    return None

        return None

    def fetch_data(self, steam_url: str, fetch_usd: bool = False, existing_data: 'SteamGameData | None' = None, known_full_game_id: str | None = None) -> SteamGameData | None:
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
                    # Update USD-specific discount data
                    usd_discount_data = self._extract_discount_data(api_data_usd)
                    if usd_discount_data['original_price_usd']:
                        game_data.original_price_usd = usd_discount_data['original_price_usd']

            # Fetch additional data from store page
            store_data = self._fetch_store_page_data(steam_url, api_data_eur, existing_data, known_full_game_id)

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

    def _fetch_api_data(self, app_id: str, country_code: str = 'at') -> dict[str, Any] | None:
        """Fetch basic data from Steam API using unified HTTP client"""
        # Use the shared HTTP client instead of manual requests
        response_data = self.http_client.make_single_app_request(app_id, country_code)

        if not response_data:
            return None

        if not isinstance(response_data, dict):
            logging.error(f"Steam API returned non-dict response for app {app_id}")
            return None

        app_info = response_data.get(app_id)
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

    def _parse_api_data(self, app_data: dict[str, Any], app_id: str, steam_url: str) -> SteamGameData:
        """Parse API data into SteamGameData object"""
        # Extract discount data
        discount_data = self._extract_discount_data(app_data)

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
            header_image=app_data.get('header_image', ''),
            discount_percent=discount_data['discount_percent'],
            original_price_eur=discount_data['original_price_eur'],
            original_price_usd=discount_data['original_price_usd'],
            is_on_sale=discount_data['is_on_sale']
        )

    def _get_price(self, app_data: dict[str, Any]) -> int | None:
        """Extract price information in cents"""
        if app_data.get('is_free'):
            return None

        price_data = app_data.get('price_overview', {})
        if price_data:
            # Steam API provides price in cents
            final_price_cents = price_data.get('final', 0)
            return final_price_cents if final_price_cents > 0 else None

        return None

    def _extract_discount_data(self, app_data: dict[str, Any]) -> dict[str, Any]:
        """Extract discount and sale information"""
        result: dict[str, Any] = {
            'discount_percent': 0,
            'original_price_eur': None,
            'original_price_usd': None,
            'is_on_sale': False
        }

        if app_data.get('is_free'):
            return result

        price_data = app_data.get('price_overview', {})
        if not price_data:
            return result

        discount_percent = price_data.get('discount_percent', 0)
        # Only set discount_percent if it's non-zero
        if discount_percent > 0:
            result['discount_percent'] = int(discount_percent)
            result['is_on_sale'] = True
        else:
            result['is_on_sale'] = False

        # Extract original prices when on sale (in cents)
        if discount_percent > 0:
            initial_price_cents = price_data.get('initial', 0)
            currency = price_data.get('currency', 'EUR')
            if initial_price_cents > 0:
                # Set currency-specific field based on API currency
                if currency == 'EUR':
                    result['original_price_eur'] = initial_price_cents
                elif currency == 'USD':
                    result['original_price_usd'] = initial_price_cents

        return result

    def _fetch_store_page_data(self, steam_url: str, app_data: dict[str, Any] | None = None, existing_data: 'SteamGameData | None' = None, known_full_game_id: str | None = None) -> dict[str, Any]:
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
        result.update(self._extract_demo_info(soup, page_text, html_content, steam_url, app_data, existing_data, known_full_game_id))
        result.update(self._extract_early_access(soup))
        result.update(self._extract_review_data(page_text))
        result.update(self._extract_release_info(soup, page_text, app_data))

        return result

    def _extract_tags(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Extract Steam tags"""
        tags = []
        tag_elements = soup.select('a.app_tag')
        for tag in tag_elements[:10]:  # Top 10 tags
            tag_text = tag.text.strip()
            if tag_text:
                tags.append(tag_text)
        return {'tags': tags}

    def _extract_demo_info(self, soup: BeautifulSoup, page_text: str, html_content: str, steam_url: str, app_data: dict[str, Any] | None = None, existing_data: 'SteamGameData | None' = None, known_full_game_id: str | None = None) -> dict[str, Any]:
        """Extract demo-related information"""
        result: dict[str, Any] = {}

        # Check if this IS a demo first
        categories_from_api = [c.get('description', '') for c in app_data.get('categories', [])] if app_data else []

        # Steam categories are 100% reliable for demo detection
        is_demo = any('demo' in cat.lower() for cat in categories_from_api)
        result['is_demo'] = is_demo

        # If this is a demo, try to find the full game
        if is_demo:
            # Use known full game ID if provided (from relationship context)
            if known_full_game_id:
                result['full_game_app_id'] = known_full_game_id
            else:
                # Extract app_id from steam_url
                app_id_match = re.search(r'/app/(\d+)', steam_url)
                current_app_id = app_id_match.group(1) if app_id_match else None
                full_game_id = self._find_full_game_id(soup, page_text, current_app_id)
                if full_game_id:
                    result['full_game_app_id'] = full_game_id
                elif existing_data and existing_data.full_game_app_id:
                    # Preserve existing relationship when no new one is found
                    result['full_game_app_id'] = existing_data.full_game_app_id
        else:
            # For non-demo apps, try to find demo app ID - only set has_demo if we find one
            demo_app_id = self._find_demo_app_id(soup, html_content)
            if demo_app_id:
                result['has_demo'] = True
                result['demo_app_id'] = demo_app_id
            else:
                result['has_demo'] = False

        return result

    def _extract_early_access(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Extract early access information"""
        early_access = soup.find('div', class_='early_access_header')
        return {'is_early_access': early_access is not None}

    def _extract_review_data(self, page_text: str) -> dict[str, Any]:
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

    def _extract_insufficient_reviews(self, page_text: str, result: dict[str, Any]) -> None:
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

    def _extract_release_info(self, soup: BeautifulSoup, page_text: str, app_data: dict[str, Any] | None = None) -> dict[str, Any]:
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

    def _find_demo_app_id(self, soup: BeautifulSoup, html_content: str) -> str | None:
        """Try to find the demo app ID from a main game page - only using steam:// protocol links"""
        current_app_id = self._get_current_app_id(soup)

        # Only search for steam://install/ protocol links - most reliable and universal
        if html_content:
            steam_protocol_pattern = r'steam://install/(\d+)'
            matches = re.findall(steam_protocol_pattern, html_content)
            for demo_id in matches:
                if str(demo_id) != current_app_id:
                    return str(demo_id)

        return None

    def _find_full_game_id(self, soup: BeautifulSoup, page_text: str, current_app_id: str | None = None) -> str | None:
        """Try to find the full game app ID from a demo page"""
        # Use provided app_id or try to get it from the page
        if not current_app_id:
            current_app_id = self._get_current_app_id(soup)

        # 1. Check for redirect - 91% of demos redirect to their main game
        try:
            demo_url = f"https://store.steampowered.com/app/{current_app_id}/"
            from .constants import HTTP_TIMEOUT_SECONDS
            response = requests.get(demo_url, timeout=HTTP_TIMEOUT_SECONDS, allow_redirects=True)

            if demo_url != response.url:
                # Demo page redirected
                match = re.search(r'/app/(\d+)', response.url)
                if match:
                    main_game_id = match.group(1)
                    if main_game_id != current_app_id:
                        logging.info(f"FULL_GAME_DETECTION: Found full game {main_game_id} for demo {current_app_id} via redirect")
                        return main_game_id
        except Exception as e:
            logging.warning(f"FULL_GAME_DETECTION: Failed to check redirect for demo {current_app_id}: {e}")

        # 2. Fallback: Check breadcrumbs - for the 9% that don't redirect
        from bs4 import Tag
        breadcrumbs = soup.find('div', class_='breadcrumbs')
        if breadcrumbs and isinstance(breadcrumbs, Tag):
            # Look for the game link right before "Demo" in breadcrumbs
            breadcrumb_links = breadcrumbs.find_all('a', href=re.compile(r'/app/(\d+)'))
            for i, link in enumerate(breadcrumb_links):
                href = self.safe_get_attr(link, 'href')
                match = re.search(r'/app/(\d+)', href)
                if match:
                    app_id = match.group(1)
                    # Check if next breadcrumb item contains "Demo"
                    if app_id != current_app_id and i < len(breadcrumb_links) - 1:
                        next_text = breadcrumb_links[i + 1].get_text() if i + 1 < len(breadcrumb_links) else ""
                        if "demo" in next_text.lower() or "demo" in page_text[page_text.find(href):page_text.find(href) + 200].lower():
                            logging.info(f"FULL_GAME_DETECTION: Found full game {app_id} for demo {current_app_id} via breadcrumb navigation")
                            return app_id

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


    def _merge_store_data(self, game_data: SteamGameData, store_data: dict[str, Any]) -> None:
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


class SteamBulkPriceFetcher:
    """Orchestrates bulk Steam price fetching using specialized components"""

    def __init__(self, data_manager: 'DataManager | None' = None) -> None:
        if not data_manager or not hasattr(data_manager, 'config_manager'):
            raise ValueError("SteamBulkPriceFetcher requires a DataManager with config_manager")

        self.data_manager = data_manager
        self.config = data_manager.config_manager.get_steam_bulk_config()

        # Initialize specialized components
        from .batch_manager import BatchManager
        from .bulk_fetch_error_handler import BulkFetchErrorHandler
        from .steam_api_response_parser import SteamApiResponseParser
        from .steam_bulk_http_client import SteamBulkHttpClient
        from .steam_price_update_service import SteamPriceUpdateService

        self.http_client = SteamBulkHttpClient(self.config)
        self.response_parser = SteamApiResponseParser()
        self.batch_manager = BatchManager(self.config)
        self.error_handler = BulkFetchErrorHandler(self.config)
        self.price_service = SteamPriceUpdateService(data_manager)


    def _process_batch_fetch_only(self, app_ids: list[str], country_code: str) -> dict[str, dict[str, Any]]:
        """Process batches and return parsed results without applying updates"""
        all_results = {}
        app_ids_to_process = app_ids.copy()

        # Get the configured initial batch size
        initial_batch_size = self.batch_manager.get_initial_batch_size(None)
        batch_number = 0
        total_apps = len(app_ids_to_process)

        while app_ids_to_process:
            batch_number += 1
            processed_apps = total_apps - len(app_ids_to_process)

            # Use configured batch size, but don't exceed remaining apps
            current_batch_size = min(initial_batch_size, len(app_ids_to_process))
            current_batch = app_ids_to_process[:current_batch_size]

            logging.info(f"Processing batch {batch_number} ({current_batch_size} apps, {processed_apps}/{total_apps} completed)")

            try:
                # Process this batch with all retry logic
                batch_results, actual_processed_count = self._process_single_batch_with_retries(current_batch, country_code)
                all_results.update(batch_results)

                # Remove processed apps and continue - use actual processed count from retry logic
                app_ids_to_process = app_ids_to_process[actual_processed_count:]

            except RuntimeError as e:
                logging.error(f"Failed to process batch {batch_number}: {e}")
                raise

        return all_results

    def _handle_http_error(self, error: requests.exceptions.HTTPError, current_batch_size: int,
                          general_attempts: int, rate_limit_attempts: int, app_ids_remaining: int) -> tuple[int, int, bool]:
        """
        Handle HTTP errors and return (new_batch_size, new_rate_limit_attempts, should_continue)

        Returns:
            tuple: (batch_size, rate_limit_attempts, should_continue)
        """
        if not error.response:
            return self._handle_server_error_with_retry(0, current_batch_size, general_attempts, app_ids_remaining)

        status_code = error.response.status_code

        if status_code == 500:
            return self._handle_server_error_with_retry(status_code, current_batch_size, general_attempts, app_ids_remaining)
        elif status_code == 429:
            return self._handle_rate_limit_error(rate_limit_attempts, general_attempts)
        elif status_code == 0 or status_code >= 500:
            return self._handle_server_error_with_retry(status_code, current_batch_size, general_attempts, app_ids_remaining)
        else:
            # Non-retryable HTTP errors (400, 404, etc.)
            self.error_handler.handle_unexpected_http_error(status_code, error.response)
            raise RuntimeError(f"HTTP {status_code} error - not retryable") from error

    def _handle_server_error_with_retry(self, status_code: int, current_batch_size: int,
                                       general_attempts: int, app_ids_remaining: int) -> tuple[int, int, bool]:
        """Handle 500/0 errors with batch size reduction"""
        new_batch_size, _ = self.error_handler.handle_server_error(current_batch_size, general_attempts)
        new_batch_size = min(new_batch_size, app_ids_remaining)

        if new_batch_size < 1:
            raise RuntimeError("Batch size reduced to less than 1 - cannot continue")

        if general_attempts + 1 >= self.config['max_retries']:
            raise RuntimeError(f"HTTP {status_code} error - exhausted {self.config['max_retries']} retries")

        return new_batch_size, 0, True  # Reset rate limit attempts on server errors

    def _handle_rate_limit_error(self, rate_limit_attempts: int, general_attempts: int) -> tuple[int, int, bool]:
        """Handle rate limiting errors"""
        should_retry, delay = self.error_handler.handle_rate_limit(rate_limit_attempts)

        if not should_retry or general_attempts + 1 >= self.config['max_retries']:
            raise RuntimeError("Rate limit exceeded - exhausted retries")

        time.sleep(delay)
        return -1, rate_limit_attempts + 1, True  # -1 indicates no batch size change

    def _process_single_batch_with_retries(self, batch_apps: list[str], country_code: str) -> tuple[dict[str, dict[str, Any]], int]:
        """Process a single batch with all retry logic, return (results, actual_processed_count)"""
        original_batch_size = len(batch_apps)
        current_batch_size = original_batch_size
        general_attempts = 0
        rate_limit_attempts = 0

        while general_attempts < self.config['max_retries']:
            try:
                # If batch size was reduced, process only the reduced batch size
                if current_batch_size < original_batch_size:
                    current_batch = batch_apps[:current_batch_size]
                    logging.info(f"Processing reduced batch: {current_batch_size} of {original_batch_size} apps")
                else:
                    current_batch = batch_apps

                logging.debug(f"Attempting {len(current_batch)} apps with batch size {current_batch_size}")

                response_data = self.http_client.make_bulk_request(current_batch, country_code)

                if response_data:
                    # Parse response using response parser
                    parsed_results = self.response_parser.parse_bulk_response(response_data, current_batch)
                    logging.debug(f"Batch fetch successful: {len(parsed_results)} results for {country_code}")
                    return parsed_results, len(current_batch)
                else:
                    # Empty response - treat as error
                    if not self.error_handler.should_retry_empty_response(general_attempts):
                        raise RuntimeError(f"Empty response after {general_attempts + 1} attempts")

                    logging.warning(f"Empty response from bulk request for {country_code} (attempt {general_attempts + 1}/{self.config['max_retries']})")
                    general_attempts += 1
                    continue

            except requests.exceptions.HTTPError as e:
                new_batch_size, new_rate_limit_attempts, should_continue = self._handle_http_error(
                    e, current_batch_size, general_attempts, rate_limit_attempts, len(batch_apps)
                )

                if not should_continue:
                    raise

                # Update batch size if it was changed (not -1)
                if new_batch_size != -1:
                    current_batch_size = new_batch_size

                rate_limit_attempts = new_rate_limit_attempts
                general_attempts += 1
                continue

            except requests.exceptions.RequestException as e:
                should_retry, delay = self.error_handler.handle_request_exception(e, general_attempts, "batch")
                if should_retry:
                    time.sleep(delay)
                    general_attempts += 1
                    continue
                else:
                    raise RuntimeError(f"Network error after {self.config['max_retries']} attempts: {e}") from e

            except Exception as e:
                if self.error_handler.should_retry_general_error(e, general_attempts):
                    general_attempts += 1
                    continue
                else:
                    raise RuntimeError(f"General error after {self.config['max_retries']} attempts: {e}") from e

        raise RuntimeError(f"Exhausted all {self.config['max_retries']} retry attempts")


    def refresh_prices_with_removal_detection(self, app_ids: list[str]) -> RemovalDetectionResult:
        """
        Combined price refresh and removal detection for cron mode

        Args:
            app_ids: List of ALL Steam app IDs (including stubs, demos)

        Returns:
            Dict with removal statistics and price update results
        """
        logging.info(f"Running price refresh with removal detection for {len(app_ids)} games")

        # Step 1: Fetch EUR prices and detect removed/restored games
        eur_results, removed_games, restored_games = self._fetch_eur_with_removal_detection(app_ids)

        # Step 2: Fetch USD prices for existing games only
        usd_results = self._fetch_usd_for_existing_games(app_ids, removed_games)

        # Validation: Ensure EUR and USD counts match expectations
        self._validate_price_fetch_counts(app_ids, removed_games, eur_results, usd_results)

        # Step 3: Update removal status in database
        self._process_removal_status_updates(removed_games, restored_games)

        # Step 4: Apply atomic price updates
        price_results = self._apply_price_updates(eur_results, usd_results)

        return self._build_removal_detection_results(removed_games, restored_games, price_results)

    def _fetch_eur_with_removal_detection(self, app_ids: list[str]) -> tuple[dict[str, Any], list[str], list[str]]:
        """
        Fetch EUR prices and detect removed/restored games

        This is the first phase of removal detection. EUR prices are fetched for ALL games
        (including stubs and demos) to determine which games Steam no longer recognizes.

        Args:
            app_ids: Complete list of Steam app IDs to check (includes stubs, demos, full games)

        Returns:
            tuple: (eur_price_results, removed_game_ids, restored_game_ids)
                - eur_price_results: Dict of successful EUR price fetches {app_id: price_data}
                - removed_game_ids: List of app IDs that Steam returned success=false for
                - restored_game_ids: List of previously removed games that are now available again

        Note:
            Games with success=false are considered removed from Steam's store and will be
            marked for removal processing. Previously removed games that now return success=true
            are considered restored and their removal flags will be cleared.
        """
        logging.info("Fetching EUR prices for removal detection...")
        removed_games = []
        restored_games = []
        eur_results = {}

        try:
            eur_results = self._process_batch_fetch_only(app_ids, 'at')
            self._detect_removed_and_restored_games(eur_results, app_ids, removed_games, restored_games)
        except requests.exceptions.RequestException as e:
            logging.error(f"EUR removal detection network error: {e}")
        except Exception as e:
            logging.error(f"EUR removal detection failed: {e}")

        return eur_results, removed_games, restored_games

    def _fetch_usd_for_existing_games(self, app_ids: list[str], removed_games: list[str]) -> dict[str, Any]:
        """
        Fetch USD prices for games that weren't removed

        This is the second phase of price fetching. USD prices are only fetched for games
        that were successfully fetched in EUR phase, avoiding wasted API calls for removed games.

        Args:
            app_ids: Original list of all Steam app IDs
            removed_games: List of app IDs that were detected as removed in EUR phase

        Returns:
            dict: USD price results {app_id: price_data} for existing games only

        Note:
            This optimization reduces API load by ~50% when there are removed games,
            since we don't waste USD API calls on games we know are removed.
        """
        existing_games = [app_id for app_id in app_ids if app_id not in removed_games]
        usd_results = {}

        if existing_games:
            logging.info("Fetching USD prices for existing games...")
            try:
                usd_results = self._process_batch_fetch_only(existing_games, 'us')
            except requests.exceptions.RequestException as e:
                logging.error(f"USD price fetch network error: {e}")
            except Exception as e:
                logging.error(f"USD price fetch failed: {e}")

        return usd_results

    def _validate_price_fetch_counts(self, app_ids: list[str], removed_games: list[str],
                                   eur_results: dict[str, Any], usd_results: dict[str, Any]) -> None:
        """
        Validate that EUR and USD price fetch counts match expectations

        This catches batching logic errors that cause mismatched result counts.
        """
        total_apps = len(app_ids)
        expected_existing_count = total_apps - len(removed_games)
        actual_eur_count = len(eur_results)
        actual_usd_count = len(usd_results)

        logging.info(f"Price fetch validation: Total={total_apps}, Removed={len(removed_games)}, "
                    f"Expected existing={expected_existing_count}")
        logging.info(f"Actual results: EUR={actual_eur_count}, USD={actual_usd_count}")

        # EUR should fetch prices for existing games (total - removed)
        # Some games might fail to fetch due to network/Steam issues, so allow some tolerance
        eur_missing = expected_existing_count - actual_eur_count
        if eur_missing > 10:  # Allow up to 10 missing due to network issues
            raise RuntimeError(f"EUR price fetch failed catastrophically: expected ~{expected_existing_count}, "
                             f"got {actual_eur_count} (missing {eur_missing})")

        # USD should match EUR count exactly (same games that had EUR success)
        if actual_usd_count != actual_eur_count:
            raise RuntimeError(f"EUR/USD price count mismatch! EUR={actual_eur_count}, USD={actual_usd_count}. "
                             f"This indicates batching logic is dropping apps. "
                             f"Expected USD count should equal EUR count ({actual_eur_count})")

        if eur_missing > 0:
            logging.warning(f"EUR fetch missing {eur_missing} games (network/Steam issues), but within tolerance")

    def _process_removal_status_updates(self, removed_games: list[str], restored_games: list[str]) -> None:
        """
        Update removal status in database

        Sets removal_detected and removal_pending flags for detected games.
        This marks games for processing by the Steam updater during the next cron cycle.

        Args:
            removed_games: App IDs that returned success=false (newly removed)
            restored_games: App IDs that were previously removed but now return success=true

        Side Effects:
            - Sets removal_detected=today, removal_pending=true for removed games
            - Clears removal_detected, removal_pending for restored games
            - Saves updated steam_games.json to disk
        """
        if removed_games or restored_games:
            self._update_removal_status(removed_games, restored_games)

    def _apply_price_updates(self, eur_results: dict[str, Any], usd_results: dict[str, Any]) -> PriceUpdateResult:
        """Apply atomic price updates for successful fetches"""
        if eur_results or usd_results:
            return self.price_service.apply_atomic_updates(eur_results, usd_results, dry_run=False)
        return {'successful': 0, 'failed': 0, 'errors': []}

    def _build_removal_detection_results(self, removed_games: list[str], restored_games: list[str],
                                       price_results: PriceUpdateResult) -> RemovalDetectionResult:
        """Build the final results dictionary"""
        return {
            'removed_count': len(removed_games),
            'restored_count': len(restored_games),
            'price_updates': price_results.get('successful', 0),
            'removed_games': removed_games,
            'restored_games': restored_games
        }

    def _process_batch_fetch_only_with_removal_detection(self, app_ids: list[str], country_code: str) -> dict[str, Any]:
        """Process batch with removal detection - tracks success/failure status"""
        all_results = {}
        app_ids_to_process = app_ids.copy()
        removed_games = []
        restored_games = []

        # Get the configured initial batch size
        initial_batch_size = self.batch_manager.get_initial_batch_size(None)

        batch_number = 0
        total_apps = len(app_ids_to_process)

        while app_ids_to_process:
            batch_number += 1
            processed_apps = total_apps - len(app_ids_to_process)

            # Use configured batch size, but don't exceed remaining apps
            current_batch_size = min(initial_batch_size, len(app_ids_to_process))
            logging.info(f"Processing removal detection batch {batch_number} ({current_batch_size} apps, {processed_apps}/{total_apps} completed)")

            general_attempts = 0
            rate_limit_attempts = 0

            # Retry loop for current batch with progressive size reduction
            while general_attempts < self.config['max_retries']:
                try:
                    # Take only the apps we can handle with current batch size
                    current_batch = app_ids_to_process[:current_batch_size]

                    response_data = self.http_client.make_bulk_request(current_batch, country_code)

                    if response_data:
                        # Parse response AND extract removal status
                        batch_results = self._parse_bulk_response_with_removal_detection(
                            response_data, current_batch, removed_games, restored_games
                        )

                        # Add price results for existing games
                        all_results.update(batch_results)
                        app_ids_to_process = app_ids_to_process[current_batch_size:]
                        break  # Success - move to remaining apps
                    else:
                        # Empty response - treat as error
                        general_attempts += 1
                        if general_attempts < self.config['max_retries']:
                            logging.warning(f"Empty response from bulk request for {country_code} (attempt {general_attempts}/{self.config['max_retries']})")
                            continue
                        else:
                            raise RuntimeError(f"Empty response after {general_attempts} attempts")

                except requests.exceptions.HTTPError as e:
                    if e.response and e.response.status_code == 500:
                        # Reduce batch size and retry
                        new_batch_size, _ = self.error_handler.handle_server_error(current_batch_size, general_attempts)
                        current_batch_size = min(new_batch_size, len(app_ids_to_process))
                        general_attempts += 1

                        if current_batch_size < 1:
                            raise RuntimeError("Batch size reduced to less than 1 - cannot continue") from e
                        if general_attempts >= self.config['max_retries']:
                            raise RuntimeError(f"HTTP 500 error - exhausted {self.config['max_retries']} retries") from e
                        continue

                    elif e.response and e.response.status_code == 429:
                        should_retry, delay = self.error_handler.handle_rate_limit(rate_limit_attempts)
                        if should_retry and general_attempts < self.config['max_retries']:
                            time.sleep(delay)
                            rate_limit_attempts += 1
                            general_attempts += 1
                            continue
                        else:
                            raise RuntimeError("Rate limit exceeded - exhausted retries") from e

                    else:
                        status_code = e.response.status_code if e.response else 0
                        # HTTP 0 (connection errors) and 5xx should be retryable
                        if status_code == 0 or status_code >= 500:
                            new_batch_size, _ = self.error_handler.handle_server_error(current_batch_size, general_attempts)
                            current_batch_size = min(new_batch_size, len(app_ids_to_process))
                            general_attempts += 1

                            if current_batch_size < 1:
                                raise RuntimeError("Batch size reduced to less than 1 - cannot continue") from e
                            if general_attempts >= self.config['max_retries']:
                                raise RuntimeError(f"HTTP {status_code} error - exhausted {self.config['max_retries']} retries") from e
                            continue
                        else:
                            # Other HTTP errors (400, 404, etc.) are not retryable
                            self.error_handler.handle_unexpected_http_error(status_code, e.response)
                            raise RuntimeError(f"HTTP {status_code} error - not retryable") from e

                except Exception as e:
                    general_attempts += 1
                    if general_attempts < self.config['max_retries']:
                        logging.warning(f"General error (attempt {general_attempts}/{self.config['max_retries']}): {e}")
                        continue
                    else:
                        raise RuntimeError(f"General error - exhausted {self.config['max_retries']} retries") from e

            # If we're here, we broke out of retry loop successfully, continue with remaining apps

        return {
            'price_data': all_results,
            'removed_games': removed_games,
            'restored_games': restored_games
        }

    def _parse_bulk_response_with_removal_detection(self, response_data: dict[str, Any], app_ids: list[str],
                                                   removed_games: list[str], restored_games: list[str]) -> dict[str, dict[str, Any]]:
        """
        Parse bulk API response and track removal/restoration status

        Processes Steam's bulk price API response to identify removed and restored games
        while extracting price data for successful responses.

        Args:
            response_data: Raw Steam API response {app_id: {success: bool, data: {...}}}
            app_ids: List of app IDs that were requested
            removed_games: List to append newly detected removed games to
            restored_games: List to append restored games to

        Returns:
            dict: Price data for successful responses {app_id: price_data}

        Side Effects:
            - Modifies removed_games list with app IDs where success=false
            - Modifies restored_games list with previously removed games now success=true

        Logic:
            - success=false → Game is removed/delisted, add to removed_games
            - success=true + previously had removal_detected → Game restored, add to restored_games
            - success=true + normal game → Extract price data normally
        """
        # Use existing response parser for price data
        price_results = self.response_parser.parse_bulk_response(response_data, app_ids)

        # Load steam games data ONCE for this batch (performance fix)
        try:
            steam_games = self.data_manager.load_steam_games()
        except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
            logging.warning(f"Failed to load steam games data: {e}")
            steam_games = {}

        # Check each app for removal/restoration status
        for app_id in app_ids:
            app_response = response_data.get(app_id, {})
            success = app_response.get('success', False)

            if not success:
                # Game is removed/delisted
                if app_id not in removed_games:
                    removed_games.append(app_id)
                    logging.info(f"Detected removed game: {app_id}")
            else:
                # Game exists - check if it was previously marked as removed
                game_data = steam_games.get(app_id)
                was_removed = bool(game_data and game_data.removal_pending)
                if was_removed and app_id not in restored_games:
                    restored_games.append(app_id)
                    logging.info(f"Detected restored game: {app_id}")

        return price_results

    def _detect_removed_and_restored_games(self, batch_results: dict[str, dict[str, Any]],
                                         app_ids: list[str], removed_games: list[str],
                                         restored_games: list[str]) -> None:
        """
        Analyze batch price fetch results to detect removed and restored games

        Compares the list of requested app IDs against successful price fetch results
        to identify games that Steam no longer recognizes (removed) or that have
        been restored after being previously removed.

        Args:
            batch_results: Results from price fetch {app_id: price_data} - only successful fetches
            app_ids: Complete list of app IDs that were requested from Steam API
            removed_games: List to append detected removed game IDs to
            restored_games: List to append detected restored game IDs to

        Side Effects:
            - Modifies removed_games list with app IDs that failed to fetch
            - Modifies restored_games list with previously removed games that now fetch successfully

        Detection Logic:
            - If app_id in app_ids but NOT in batch_results → Game was removed
            - If app_id in batch_results AND game has removal_detected flag → Game was restored

        Note:
            This method complements _parse_bulk_response_with_removal_detection() by handling
            cases where games completely fail to appear in the API response vs. returning success=false.
        """
        # Load steam games data ONCE for all detection
        try:
            steam_games = self.data_manager.load_steam_games()
        except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
            logging.warning(f"Failed to load steam games data: {e}")
            steam_games = {}

        for app_id in app_ids:
            # Check if app was successfully fetched
            if app_id in batch_results:
                # Game exists - check if it was previously marked as removed
                game_data = steam_games.get(app_id)
                was_removed = bool(game_data and game_data.removal_pending)
                if was_removed and app_id not in restored_games:
                    restored_games.append(app_id)
                    logging.info(f"Detected restored game: {app_id}")
            else:
                # Game is missing from results - likely removed/delisted
                if app_id not in removed_games:
                    removed_games.append(app_id)
                    logging.info(f"Detected removed game: {app_id}")

    def _update_removal_status(self, removed_games: list[str], restored_games: list[str]) -> None:
        """
        Update removal status flags in steam_games.json for detected changes

        This method persists the removal detection results to the database by setting
        appropriate flags that will be processed by the Steam updater in the next cron cycle.

        Args:
            removed_games: App IDs detected as newly removed from Steam
            restored_games: App IDs that were previously removed but are now available again

        Side Effects:
            - Sets removal_detected=today and removal_pending=true for removed games
            - Clears removal_detected and removal_pending flags for restored games
            - Saves updated steam_games.json to disk
            - Logs the number of games processed

        Database Fields Modified:
            - removal_detected: Date string when removal was first detected (YYYY-MM-DD)
            - removal_pending: Boolean flag indicating game needs removal processing

        Note:
            Games marked with removal_pending=true will be processed by SteamDataUpdater
            during the next cron cycle, either converting to stubs or deleting entirely.
        """
        if not removed_games and not restored_games:
            return

        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')

        try:
            steam_games = self.data_manager.load_steam_games()
            updated = False

            # Mark removed games
            for app_id in removed_games:
                if app_id in steam_games:
                    steam_games[app_id].removal_detected = today
                    steam_games[app_id].removal_pending = True
                    updated = True

            # Clear flags for restored games
            for app_id in restored_games:
                if app_id in steam_games:
                    steam_games[app_id].removal_detected = None
                    steam_games[app_id].removal_pending = False
                    updated = True

            if updated:
                from datetime import datetime
                self.data_manager.save_steam_data({'games': steam_games, 'last_updated': datetime.now().isoformat()})
                logging.info(f"Updated removal status: {len(removed_games)} marked as removed, {len(restored_games)} restored")

        except Exception as e:
            logging.error(f"Failed to update removal status: {e}")

