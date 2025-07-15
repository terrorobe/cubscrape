"""
Itch.io data fetching and parsing functionality
"""

import logging
import re

import requests
from bs4 import BeautifulSoup
from models import OtherGameData


class ItchDataFetcher:
    """Handles fetching and parsing Itch.io game data"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def fetch_data(self, itch_url: str) -> OtherGameData | None:
        """Fetch game data from Itch.io"""
        try:
            response = requests.get(itch_url, headers=self.headers)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, 'lxml')

            # Create base game data
            game_data = OtherGameData(
                platform='itch',
                url=itch_url,
                name=self._extract_name(soup),
                is_free=True,  # Most itch games are free or pay-what-you-want
                header_image=self._extract_header_image(soup),
                tags=self._extract_tags(soup)
            )

            # Extract rating information
            rating_data = self._extract_rating(soup)
            if rating_data:
                game_data.positive_review_percentage = rating_data.get('percentage')
                game_data.review_count = rating_data.get('count')

            return game_data

        except Exception as e:
            logging.error(f"Error fetching itch.io data for {itch_url}: {e}")
            return None

    def _extract_name(self, soup: BeautifulSoup) -> str:
        """Extract game name from page"""
        title_elem = soup.find('h1', class_='game_title') or soup.find('h1')
        if title_elem:
            return title_elem.get_text(strip=True)
        return ""

    def _extract_header_image(self, soup: BeautifulSoup) -> str:
        """Extract header image from meta tags"""
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return og_image['content']
        return ""

    def _extract_tags(self, soup: BeautifulSoup) -> list:
        """Extract tags from Itch.io page"""
        tags = []

        # Try to find tags in the info table (most reliable for Itch.io)
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
                count_text = count_elem.get_text(strip=True) or count_elem.get('data-downloads', '')
                # Extract number from "1,234 downloads" or "1,234 plays"
                count_match = re.search(r'([\d,]+)', count_text)
                if count_match:
                    return {'count': int(count_match.group(1).replace(',', ''))}

        return None
