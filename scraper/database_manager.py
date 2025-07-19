import json
import logging
import re
import sqlite3
from pathlib import Path


class DatabaseManager:
    def __init__(self, schema_file='data/schema.sql', db_file='data/games.db'):
        self.schema_file = schema_file
        self.db_file = db_file

    def create_database(self, games_data):
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

    def _populate_games(self, conn, games_data):
        cursor = conn.cursor()

        for game_key, game in games_data.items():
            # Generate review summary for non-Steam platforms
            review_summary = self._generate_review_summary(game)
            review_summary_priority = self._get_review_summary_priority(review_summary)

            # Insert game record
            cursor.execute('''
                INSERT INTO games (
                    game_key, steam_app_id, name, platform, coming_soon,
                    is_early_access, is_demo, is_free, price, price_final,
                    positive_review_percentage, review_count, review_summary, review_summary_priority,
                    recent_review_percentage, recent_review_count, recent_review_summary,
                    insufficient_reviews, release_date, planned_release_date, header_image, steam_url, itch_url,
                    crazygames_url, last_updated, video_count, latest_video_date,
                    unique_channels, genres, tags, developers, publishers,
                    demo_steam_app_id, demo_steam_url, demo_itch_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                game_key,
                game.get('steam_app_id'),
                game.get('name'),
                game.get('platform'),
                game.get('coming_soon', False),
                game.get('is_early_access', False),
                game.get('is_demo', False),
                game.get('is_free', False),
                game.get('price'),
                self._extract_price_final(game),
                game.get('positive_review_percentage', 0),
                game.get('review_count', 0),
                review_summary,
                review_summary_priority,
                game.get('recent_review_percentage'),
                game.get('recent_review_count'),
                game.get('recent_review_summary'),
                game.get('insufficient_reviews', False),
                game.get('release_date'),
                game.get('planned_release_date'),
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
                game.get('demo_itch_url')
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

    def _generate_review_summary(self, game):
        """Generate review summary for non-Steam platforms using Steam's thresholds"""
        platform = game.get('platform')

        # Steam games already have official summaries
        if platform == 'steam':
            return game.get('review_summary')

        percentage = game.get('positive_review_percentage')
        review_count = game.get('review_count', 0)

        if not review_count or review_count == 0:
            return 'No user reviews'

        if review_count < 10:
            return 'Need more reviews for score'

        if not percentage:
            return None

        # Apply Steam's thresholds
        if percentage >= 95:
            if review_count >= 500:
                return 'Overwhelmingly Positive'
            elif review_count >= 50:
                return 'Very Positive'
            else:
                return 'Positive'
        elif percentage >= 80:
            if review_count >= 50:
                return 'Very Positive'
            else:
                return 'Positive'
        elif percentage >= 70:
            return 'Mostly Positive'
        elif percentage >= 40:
            return 'Mixed'
        elif percentage >= 20:
            return 'Mostly Negative'
        else:
            return 'Negative'

    def _get_review_summary_priority(self, review_summary):
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

    def _extract_price_final(self, game):
        """Extract numeric price for filtering"""
        if game.get('is_free'):
            return 0.0

        price = game.get('price', '')
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

    def _get_latest_video_date(self, game):
        """Get the most recent video date for this game"""
        videos = game.get('videos', [])
        if not videos:
            return None

        dates = [v.get('video_date') for v in videos if v.get('video_date')]
        return max(dates) if dates else None

    def _get_unique_channels(self, game):
        """Get unique channel names that featured this game"""
        videos = game.get('videos', [])
        channels = set()

        for video in videos:
            if video.get('channel_name'):
                channels.add(video['channel_name'])

        return list(channels)

    def _get_demo_steam_app_id(self, game):
        """Get demo Steam app ID if available"""
        if game.get('has_demo') and game.get('demo_app_id'):
            return game['demo_app_id']
        return None

    def _get_demo_steam_url(self, game):
        """Get demo Steam URL if available"""
        demo_app_id = self._get_demo_steam_app_id(game)
        if demo_app_id:
            return f"https://store.steampowered.com/app/{demo_app_id}"
        return None

    def _get_platform_url(self, game):
        """Get the correct platform URL based on the game's platform"""
        platform = game.get('platform', 'steam')

        if platform == 'itch':
            return game.get('url')  # Itch games use 'url' field
        else:
            return game.get('itch_url')  # Steam games might have itch_url field

    def _get_crazygames_url(self, game):
        """Get the correct CrazyGames URL"""
        platform = game.get('platform', 'steam')

        if platform == 'crazygames':
            return game.get('url')  # CrazyGames use 'url' field
        else:
            return game.get('crazygames_url')  # Other platforms might have crazygames_url field
