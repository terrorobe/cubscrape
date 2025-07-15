"""
CrazyGames data fetching and parsing functionality
"""

import json
import logging
import re

import requests
from bs4 import BeautifulSoup
from models import OtherGameData
from utils import clean_tag_text


class CrazyGamesDataFetcher:
    """Handles fetching and parsing CrazyGames game data"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def fetch_data(self, crazygames_url: str) -> OtherGameData | None:
        """Fetch game data from CrazyGames"""
        try:
            response = requests.get(crazygames_url, headers=self.headers)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, 'lxml')
            page_text = response.text

            # Create base game data
            game_data = OtherGameData(
                platform='crazygames',
                url=crazygames_url,
                name=self._extract_name(soup),
                is_free=True,  # CrazyGames are free browser games
                header_image=self._extract_header_image(soup),
                tags=self._extract_tags(soup)
            )

            # Extract rating information
            rating_data = self._extract_rating(soup, page_text)
            if rating_data:
                game_data.positive_review_percentage = rating_data.get('percentage')
                game_data.review_count = rating_data.get('count')

            return game_data

        except Exception as e:
            logging.error(f"Error fetching CrazyGames data for {crazygames_url}: {e}")
            return None

    def _extract_name(self, soup: BeautifulSoup) -> str:
        """Extract game name from page"""
        title_elem = soup.find('h1') or soup.find('title')
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            # Clean up title (remove " - CrazyGames" suffix)
            return title_text.split(' - CrazyGames')[0].split(' | CrazyGames')[0]
        return ""

    def _extract_header_image(self, soup: BeautifulSoup) -> str:
        """Extract header image from meta tags"""
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return og_image['content']
        return ""

    def _extract_tags(self, soup: BeautifulSoup) -> list:
        """Extract tags from CrazyGames page"""
        tags = []

        # CrazyGames uses specific CSS classes
        tag_elements = soup.select('.GameTags_gameTagChipContainer__F5xPO a')

        for tag in tag_elements[:10]:  # Limit to 10 tags
            tag_text = tag.get_text(strip=True)
            if tag_text:
                # Clean up tag text - remove trailing numbers like "Casual1,157"
                clean_tag = clean_tag_text(tag_text)
                if clean_tag and len(clean_tag) > 2 and clean_tag not in tags:
                    tags.append(clean_tag)

        return tags

    def _extract_rating(self, soup: BeautifulSoup, page_text: str) -> dict | None:
        """Extract rating information from CrazyGames page"""
        # Look for rating in structured data (JSON-LD)
        rating_data = self._extract_rating_from_json_ld(soup)
        if rating_data:
            return rating_data

        # Fallback: Look for rating in page text using regex patterns
        return self._extract_rating_from_text(page_text)

    def _extract_rating_from_json_ld(self, soup: BeautifulSoup) -> dict | None:
        """Extract rating from JSON-LD structured data"""
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
                                return self._parse_aggregate_rating(main_entity['aggregateRating'])

                elif isinstance(json_data, dict):
                    # Check for aggregateRating
                    aggregate_rating = json_data.get('aggregateRating', {})
                    if aggregate_rating.get('ratingValue'):
                        return self._parse_aggregate_rating(aggregate_rating)

            except Exception as e:
                logging.debug(f"Error parsing JSON-LD: {e}")

        return None

    def _parse_aggregate_rating(self, aggregate_rating: dict) -> dict:
        """Parse aggregate rating data"""
        rating_value = float(aggregate_rating['ratingValue'])
        best_rating = float(aggregate_rating.get('bestRating', 10))
        # Convert to 0-100 scale
        percentage = round((rating_value / best_rating) * 100)

        result = {'percentage': int(percentage)}

        rating_count = aggregate_rating.get('ratingCount')
        if rating_count:
            result['count'] = int(rating_count)

        logging.info(f"Found rating in JSON-LD: {rating_value}/{best_rating} = {percentage}%")
        return result

    def _extract_rating_from_text(self, page_text: str) -> dict | None:
        """Extract rating from page text using regex patterns"""
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
                    percentage = int((rating / 10.0) * 100)
                elif rating <= 100:  # Already percentage
                    percentage = int(rating)
                else:
                    continue

                result = {'percentage': percentage}

                # Look for vote/review count
                count = self._extract_review_count_from_text(page_text)
                if count:
                    result['count'] = count

                return result

        return None

    def _extract_review_count_from_text(self, page_text: str) -> int | None:
        """Extract review count from page text"""
        count_patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*(?:votes?|ratings?)',
            r'"ratingCount"[:\s]+["\']?(\d+)',
            r'Total Votes[:\s]+(\d{1,3}(?:,\d{3})*)',
        ]

        for pattern in count_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                count_str = match.group(1).replace(',', '')
                return int(count_str)

        return None
