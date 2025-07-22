import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import Any

from .utils import generate_review_summary


class DatabaseManager:
    def __init__(self, schema_file: str = 'data/schema.sql', db_file: str = 'data/games.db') -> None:
        self.schema_file = schema_file
        self.db_file = db_file

    def create_database(self, games_data: dict[str, Any]) -> None:
        """Create fresh database from schema and populate with data"""
        # Remove existing database
        db_path = Path(self.db_file)
        if db_path.exists():
            db_path.unlink()

        # Create new database from schema
        conn = sqlite3.connect(self.db_file)
        with Path(self.schema_file).open() as f:
            conn.executescript(f.read())

        # Populate with data
        self._populate_games(conn, games_data)

        conn.commit()
        conn.close()

        logging.info(f"Created SQLite database: {self.db_file}")

    def _convert_to_sortable_date_int(self, date_str: str) -> int | None:
        """Convert release dates to sortable YYYYMMDD integer format
        Only handles formats for released games
        """
        if not date_str:
            return None

        from datetime import datetime

        # Steam format: "6 Feb, 2025" or "24 Sep, 2024"
        steam_match = re.match(r'^(\d{1,2})\s+(\w{3}),\s+(\d{4})$', date_str)
        if steam_match:
            day = steam_match.group(1)
            month = steam_match.group(2)
            year = steam_match.group(3)
            try:
                date_obj = datetime.strptime(f"{day} {month} {year}", "%d %b %Y")
                return int(date_obj.strftime("%Y%m%d"))
            except ValueError:
                pass

        # Itch format: "08 April 2025" or "21 March 2025"
        itch_match = re.match(r'^(\d{2})\s+(\w+)\s+(\d{4})$', date_str)
        if itch_match:
            day = itch_match.group(1)
            month = itch_match.group(2)
            year = itch_match.group(3)
            try:
                date_obj = datetime.strptime(f"{day} {month} {year}", "%d %B %Y")
                return int(date_obj.strftime("%Y%m%d"))
            except ValueError:
                pass

        # CrazyGames format: "March 2025" (use first day of month)
        month_year_match = re.match(r'^(\w+)\s+(\d{4})$', date_str)
        if month_year_match:
            month_name = month_year_match.group(1)
            year = month_year_match.group(2)
            try:
                # Parse month name and create date with first day of month
                date_obj = datetime.strptime(f"{month_name} 1 {year}", "%B %d %Y")
                return int(date_obj.strftime("%Y%m%d"))
            except ValueError:
                pass

        # Return None if we can't parse it
        return None

    def _populate_games(self, conn: sqlite3.Connection, games_data: dict[str, Any]) -> None:
        cursor = conn.cursor()

        for game_key, game in games_data.items():
            # Generate review summary for non-Steam platforms
            review_summary = self._generate_review_summary(game)
            review_summary_priority = self._get_review_summary_priority(review_summary)

            # Only use percentage if there are enough reviews (applies to all platforms)
            percentage = game.get('positive_review_percentage', 0)
            review_count = game.get('review_count', 0)
            if review_count < 10:
                percentage = None

            # Only give sortable dates to actually released games (not coming soon)
            is_released = not game.get('coming_soon', False)
            sortable_date = None
            if is_released:
                sortable_date = self._convert_to_sortable_date_int(game.get('release_date', ''))

            # Insert game record
            cursor.execute('''
                INSERT INTO games (
                    game_key, steam_app_id, name, platform, coming_soon,
                    is_early_access, is_demo, is_free, price_eur, price_usd, price_final,
                    positive_review_percentage, review_count, review_summary, review_summary_priority,
                    recent_review_percentage, recent_review_count, recent_review_summary,
                    insufficient_reviews, release_date, planned_release_date, release_date_sortable, header_image, steam_url, itch_url,
                    crazygames_url, last_updated, video_count, latest_video_date,
                    unique_channels, genres, tags, developers, publishers,
                    demo_steam_app_id, demo_steam_url, review_tooltip, is_inferred_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                game_key,
                game.get('steam_app_id'),
                game.get('name'),
                game.get('platform'),
                game.get('coming_soon', False),
                game.get('is_early_access', False),
                game.get('is_demo', False),
                game.get('is_free', False),
                None if game.get('is_free') else game.get('price_eur'),
                None if game.get('is_free') else game.get('price_usd'),
                self._extract_price_final(game),
                percentage,
                game.get('review_count', 0),
                review_summary,
                review_summary_priority,
                game.get('recent_review_percentage'),
                game.get('recent_review_count'),
                game.get('recent_review_summary'),
                game.get('insufficient_reviews', False),
                game.get('release_date'),
                game.get('planned_release_date'),
                sortable_date,
                game.get('header_image'),
                game.get('steam_url'),
                self._get_platform_url(game),
                self._get_crazygames_url(game),
                game.get('last_updated'),
                game.get('video_count', 0),
                self._get_latest_video_date(game),
                json.dumps(self._get_unique_channels(game)),
                json.dumps(game.get('genres', [])),
                json.dumps(game.get('tags', [])),
                json.dumps(game.get('developers', [])),
                json.dumps(game.get('publishers', [])),
                self._get_demo_steam_app_id(game),
                self._get_demo_steam_url(game),
                game.get('review_tooltip'),
                game.get('is_inferred_summary', False)
            ))

            game_id = cursor.lastrowid

            # Insert video records
            for video in game.get('videos', []):
                cursor.execute('''
                    INSERT INTO game_videos (
                        game_id, video_id, video_title, video_date,
                        channel_name, published_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    game_id,
                    video.get('video_id'),
                    video.get('video_title'),
                    video.get('video_date'),
                    video.get('channel_name'),
                    video.get('published_at')
                ))

    def _generate_review_summary(self, game: dict[str, Any]) -> str | None:
        """Generate review summary for non-Steam platforms using Steam's thresholds"""
        platform = game.get('platform')

        # Steam games already have official summaries
        if platform == 'steam':
            return game.get('review_summary')

        # For non-Steam platforms, generate clean summary (asterisk handled in frontend)
        percentage = game.get('positive_review_percentage')
        review_count = game.get('review_count', 0)

        return generate_review_summary(percentage, review_count)

    def _get_review_summary_priority(self, review_summary: str | None) -> int:
        """Get numeric priority for review summary for efficient sorting"""
        if not review_summary:
            return 99

        priorities = {
            'Overwhelmingly Positive': 1,
            'Very Positive': 2,
            'Positive': 3,
            'Mostly Positive': 4,
            'Mixed': 5,
            'Mostly Negative': 6,
            'Negative': 7,
            'Very Negative': 8,
            'Overwhelmingly Negative': 9,
            'Need more reviews for score': 10,
            'No user reviews': 11
        }

        return priorities.get(review_summary, 99)

    def _extract_price_final(self, game: dict[str, Any]) -> float:
        """Extract numeric price for filtering"""
        if game.get('is_free'):
            return 0.0

        # Try EUR price first, then USD
        price = game.get('price_eur', '') or game.get('price_usd', '')
        if not price:
            return 0.0

        # Extract numeric value from price string like "16,79€" or "$19.99"
        match = re.search(r'(\d+)[,.](\d+)', price)
        if match:
            return float(f"{match.group(1)}.{match.group(2)}")

        match = re.search(r'(\d+)', price)
        if match:
            return float(match.group(1))

        return 0.0

    def _get_latest_video_date(self, game: dict[str, Any]) -> str | None:
        """Get the most recent video date for this game"""
        videos = game.get('videos', [])
        if not videos:
            return None

        dates = [v.get('video_date') for v in videos if v.get('video_date')]
        return max(dates) if dates else None

    def _get_unique_channels(self, game: dict[str, Any]) -> list[str]:
        """Get unique channel names that featured this game"""
        videos = game.get('videos', [])
        channels = set()

        for video in videos:
            if video.get('channel_name'):
                channels.add(video['channel_name'])

        return list(channels)

    def _get_demo_steam_app_id(self, game: dict[str, Any]) -> str | None:
        """Get demo Steam app ID if available"""
        if game.get('has_demo') and game.get('demo_app_id'):
            demo_id = game['demo_app_id']
            return str(demo_id) if demo_id is not None else None
        return None

    def _get_demo_steam_url(self, game: dict[str, Any]) -> str | None:
        """Get demo Steam URL if available"""
        demo_app_id = self._get_demo_steam_app_id(game)
        if demo_app_id:
            return f"https://store.steampowered.com/app/{demo_app_id}"
        return None

    def _get_platform_url(self, game: dict[str, Any]) -> str | None:
        """Get the correct platform URL based on the game's platform"""
        platform = game.get('platform', 'steam')

        if platform == 'itch':
            return game.get('url')  # Itch games use 'url' field
        else:
            return game.get('itch_url')  # Steam games might have itch_url field

    def _get_crazygames_url(self, game: dict[str, Any]) -> str | None:
        """Get the correct CrazyGames URL"""
        platform = game.get('platform', 'steam')

        if platform == 'crazygames':
            return game.get('url')  # CrazyGames use 'url' field
        else:
            return game.get('crazygames_url')  # Other platforms might have crazygames_url field
