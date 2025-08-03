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

    def refresh_prices_bulk(self, app_ids: list[str], batch_size: int | None = None,
                          currencies: str = 'both', dry_run: bool = False) -> dict[str, Any]:
        """
        Main entry point for bulk price refresh

        Args:
            app_ids: List of Steam app IDs to refresh
            batch_size: Apps per batch (uses config default if None)
            currencies: 'eur', 'usd', or 'both'
            dry_run: Preview changes without applying

        Returns:
            Dict with 'successful' and 'failed' lists
        """
        batch_size = self.batch_manager.get_initial_batch_size(batch_size)

        logging.info(f"Starting bulk price refresh for {len(app_ids)} apps")
        logging.info(f"Batch size: {batch_size}, Currencies: {currencies}, Dry run: {dry_run}")

        # Collect all data first across all batches and currencies
        all_eur_updates = {}
        all_usd_updates = {}

        # Split app IDs into batches
        batches = self.batch_manager.create_batches(app_ids, batch_size)

        # Fetch all data first (no saving yet)
        for i, batch in enumerate(batches, 1):
            logging.info(f"Processing batch {i}/{len(batches)} ({len(batch)} apps)")

            try:
                # Fetch EUR prices if needed
                if currencies in ['eur', 'both']:
                    eur_batch_results = self._process_batch_fetch_only(batch, 'at')
                    all_eur_updates.update(eur_batch_results)

                # Fetch USD prices if needed
                if currencies in ['usd', 'both']:
                    usd_batch_results = self._process_batch_fetch_only(batch, 'us')
                    all_usd_updates.update(usd_batch_results)

            except Exception as e:
                logging.error(f"Batch {i} failed: {e}")
                # Continue processing other batches

        # Apply all updates using the price service
        if currencies == 'both':
            return self.price_service.apply_atomic_updates(all_eur_updates, all_usd_updates, dry_run)
        elif currencies == 'eur':
            return self.price_service.update_prices(all_eur_updates, 'eur', dry_run)
        elif currencies == 'usd':
            return self.price_service.update_prices(all_usd_updates, 'usd', dry_run)
        else:
            raise ValueError(f"Invalid currencies: {currencies}")

    def _process_batch_fetch_only(self, app_ids: list[str], country_code: str) -> dict[str, dict[str, Any]]:
        """Process a batch and return parsed results without applying updates"""
        current_batch_size = len(app_ids)
        general_attempts = 0
        rate_limit_attempts = 0

        while general_attempts < self.config['max_retries']:
            try:
                # Make bulk request using HTTP client
                response_data = self.http_client.make_bulk_request(app_ids[:current_batch_size], country_code)

                if response_data:
                    # Parse response using response parser
                    parsed_results = self.response_parser.parse_bulk_response(response_data, app_ids[:current_batch_size])
                    logging.debug(f"Batch fetch successful: {len(parsed_results)} results for {country_code}")
                    return parsed_results
                else:
                    # Empty response - increment attempts first
                    general_attempts += 1
                    if self.error_handler.should_retry_empty_response(general_attempts - 1):
                        logging.warning(f"Empty response from bulk request for {country_code} (attempt {general_attempts})")
                        continue
                    else:
                        return {}

            except requests.exceptions.HTTPError as e:
                if e.response and e.response.status_code == 500:
                    new_batch_size, should_continue = self.error_handler.handle_server_error(current_batch_size, general_attempts)
                    current_batch_size = new_batch_size
                    general_attempts += 1
                    if not should_continue:
                        break
                    continue
                elif e.response and e.response.status_code == 429:
                    should_retry, delay = self.error_handler.handle_rate_limit(rate_limit_attempts)
                    if should_retry:
                        time.sleep(delay)
                        rate_limit_attempts += 1
                        continue
                    else:
                        return {}
                else:
                    self.error_handler.handle_unexpected_http_error(e.response.status_code if e.response else 0, e.response)
                    return {}
            except Exception as e:
                if self.error_handler.should_retry_general_error(e, general_attempts):
                    general_attempts += 1
                    continue
                else:
                    return {}

        # If we get here, all retries failed
        logging.warning(f"All retries failed for batch fetch ({country_code}): "
                       f"attempts={general_attempts}, batch_size={current_batch_size}")
        return {}

