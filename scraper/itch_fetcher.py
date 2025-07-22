"""
Itch.io data fetching and parsing functionality
"""

import logging
import os
import re

import requests
from bs4 import BeautifulSoup

from .base_fetcher import BaseFetcher
from .models import OtherGameData
from .utils import calculate_name_similarity, extract_steam_app_id, load_env_file


class ItchDataFetcher(BaseFetcher):
    """Handles fetching and parsing Itch.io game data"""

    def __init__(self) -> None:
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        # Load .env file if ITCH_COOKIES is not already set
        if 'ITCH_COOKIES' not in os.environ:
            load_env_file()

        # Load optional authentication from environment
        itch_cookies = os.getenv('ITCH_COOKIES')
        if itch_cookies:
            self.headers['Cookie'] = itch_cookies
            logging.info("Using Itch.io authentication token for enhanced data access")

    def fetch_data(self, itch_url: str) -> OtherGameData | None:
        """Fetch game data from Itch.io"""
        try:
            response = requests.get(itch_url, headers=self.headers)
            if response.status_code != 200:
                # Create stub entry for failed HTTP requests
                return self._create_stub_entry(itch_url, f"HTTP {response.status_code}")

            soup = BeautifulSoup(response.content, 'lxml')

            # Try to extract name to validate page content
            name = self._extract_name(soup)
            if not name:
                # Create stub entry if we can't extract basic game data
                return self._create_stub_entry(itch_url, "No game name found")

            # Create base game data
            game_data = OtherGameData(
                platform='itch',
                url=itch_url,
                name=name,
                is_free=True,  # Most itch games are free or pay-what-you-want
                release_date=self._extract_release_date(soup),
                header_image=self._extract_header_image(soup),
                tags=self._extract_tags(soup)
            )

            # Extract rating information
            rating_data = self._extract_rating(soup)
            if rating_data:
                game_data.positive_review_percentage = rating_data.get('percentage')
                game_data.review_count = rating_data.get('count')

            # Extract Steam link if present and name matches
            steam_url = self._extract_steam_link(soup, game_data.name)
            if steam_url:
                game_data.steam_url = steam_url
                logging.info(f"Found matching Steam link for {game_data.name}: {steam_url}")

            return game_data

        except Exception as e:
            logging.error(f"Error fetching itch.io data for {itch_url}: {e}")
            return self._create_stub_entry(itch_url, f"Exception: {e!s}")

    def _extract_name(self, soup: BeautifulSoup) -> str:
        """Extract game name from page"""
        title_elem = soup.find('h1', class_='game_title') or soup.find('h1')
        if title_elem:
            return title_elem.get_text(strip=True)
        return ""

    def _extract_header_image(self, soup: BeautifulSoup) -> str:
        """Extract header image from meta tags"""
        return self.safe_find_attr(soup, 'content', 'meta', property='og:image')

    def _extract_release_date(self, soup: BeautifulSoup) -> str:
        """Extract release/published date from Itch.io page"""
        # Look for the release date row in the info table
        date_keywords = ['published', 'release date', 'released', 'created']

        table_rows = soup.select('table tr')
        for row in table_rows:
            cells = row.find_all('td')
            if len(cells) == 2:
                label = cells[0].get_text(strip=True).lower()

                # Check for date keywords
                for keyword in date_keywords:
                    if keyword in label:
                        # Look for abbr element in the second cell
                        abbr = self.safe_find(cells[1], 'abbr', title=True)
                        if abbr:
                            title = self.safe_get_attr(abbr, 'title')
                            # Parse authenticated format: "08 April 2025 @ 04:55 UTC"
                            date_match = re.search(r'(\d{1,2} \w+ \d{4})', title)
                            if date_match:
                                return date_match.group(1)
                            # Return cleaned title if it contains a year (remove time part)
                            if re.search(r'\d{4}', title):
                                return title.split('@')[0].strip()

        return ""

    def _extract_steam_link(self, soup: BeautifulSoup, itch_game_name: str) -> str:
        """Extract Steam link if present and game name matches"""
        # Search in all links on the page
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = self.safe_get_attr(link, 'href')
            app_id = extract_steam_app_id(href)
            if app_id:
                steam_url = f"https://store.steampowered.com/app/{app_id}"

                # Check if this Steam link has a matching game name
                if self._verify_steam_game_name(steam_url, itch_game_name):
                    return steam_url

        return ""

    def _check_steam_demo_precedence(self, steam_app_id: str) -> bool:
        """Check if Steam app should be ignored due to demo precedence rules

        Returns True if the Steam game should be ignored (not linked to Itch)
        """
        try:
            import json
            from pathlib import Path

            # Load Steam games data to check for demo relationships
            script_dir = Path(__file__).resolve().parent
            project_root = script_dir.parent
            steam_data_file = project_root / 'data' / 'steam_games.json'

            if not steam_data_file.exists():
                return False

            with steam_data_file.open() as f:
                steam_data = json.load(f)

            steam_games = steam_data.get('games', {})
            steam_game = steam_games.get(steam_app_id, {})

            if not steam_game:
                return False

            # Check if this Steam game has demo relationships
            has_demo_pair = (
                steam_game.get('demo_app_id') or
                steam_game.get('full_game_app_id')
            )

            if has_demo_pair:
                logging.info(f"Steam app {steam_app_id} has demo pair - ignoring Itch link due to precedence rules")
                return True

            return False

        except Exception as e:
            logging.debug(f"Error checking Steam demo precedence for {steam_app_id}: {e}")
            return False

    def _verify_steam_game_name(self, steam_url: str, itch_game_name: str) -> bool:
        """Verify that the Steam game name matches the Itch.io game name"""
        try:
            # Extract Steam app ID to check precedence rules
            app_id = extract_steam_app_id(steam_url)
            if app_id and self._check_steam_demo_precedence(app_id):
                logging.info(f"Skipping Steam link {steam_url} due to demo precedence rules")
                return False

            # Make a quick request to Steam to get the game name
            response = requests.get(steam_url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return False

            # Extract game name from Steam page title
            steam_soup = BeautifulSoup(response.content, 'lxml')
            title_elem = steam_soup.find('title')
            if not title_elem:
                return False

            # Steam titles are usually in format "Game Name on Steam"
            steam_title = title_elem.get_text(strip=True)
            steam_name = steam_title.replace(' on Steam', '').strip()

            # Calculate similarity between names
            similarity = calculate_name_similarity(itch_game_name, steam_name)

            # Consider it a match if similarity is high enough (75% word overlap)
            if similarity >= 0.75:
                logging.info(f"Steam name match: '{itch_game_name}' ↔ '{steam_name}' (similarity: {similarity:.2f})")
                return True
            else:
                logging.debug(f"Steam name mismatch: '{itch_game_name}' ↔ '{steam_name}' (similarity: {similarity:.2f})")
                return False

        except Exception as e:
            logging.debug(f"Error verifying Steam game name for {steam_url}: {e}")
            return False

    def _extract_tags(self, soup: BeautifulSoup) -> list:
        """Extract tags from Itch.io page"""
        tags = []

        # Try to find tags in the info table (most reliable for Itch.io)
        table_rows = soup.select('table tr')
        for row in table_rows:
            cells = row.find_all('td')
            if len(cells) == 2 and cells[0].get_text(strip=True) == 'Tags':
                # Found the tags row, extract tags from second cell
                # Use safe method to find all links in the second cell
                tag_links = self.safe_find_all(cells[1], 'a')
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

        return tags[:10]  # Limit to 10 tags total

    def _extract_rating(self, soup: BeautifulSoup) -> dict | None:
        """Extract rating information from Itch.io page"""
        # Get rating (itch uses 5-star system, convert to 0-100)
        rating_elem = soup.select_one('.aggregate_rating') or soup.select_one('.star_value')
        if rating_elem:
            rating_text = rating_elem.get_text(strip=True)
            # Extract rating like "Rated 4.7 out of 5 stars"
            rating_match = re.search(r'(\d+\.?\d*)', rating_text)
            if rating_match:
                stars = float(rating_match.group(1))
                # Convert 5-star to 0-100 percentage
                percentage = int((stars / 5.0) * 100)

                result = {'percentage': percentage}

                # Also extract review count if available
                count_match = re.search(r'\((\d+)\s*total ratings?\)', rating_text)
                if count_match:
                    result['count'] = int(count_match.group(1))

                return result

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
                count_text = self.safe_get_text(count_elem) or self.safe_get_attr(count_elem, 'data-downloads')
                # Extract number from "1,234 downloads" or "1,234 plays"
                count_match = re.search(r'([\d,]+)', count_text)
                if count_match:
                    return {'count': int(count_match.group(1).replace(',', ''))}

        return None

    def _create_stub_entry(self, itch_url: str, reason: str, resolved_to: str | None = None) -> OtherGameData:
        """Create a stub entry for failed fetches to avoid retrying"""
        logging.info(f"Creating stub entry for itch.io URL {itch_url}: {reason}")
        return OtherGameData(
            platform='itch',
            url=itch_url,
            name=f"[FAILED FETCH] {itch_url}",
            is_stub=True,
            stub_reason=reason,
            resolved_to=resolved_to
        )
