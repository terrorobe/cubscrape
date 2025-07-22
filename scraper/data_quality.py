"""
Data quality checking and reporting utilities
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

from .config_manager import ConfigManager


class DataQualityChecker:
    """Handles data quality analysis and reporting"""

    def __init__(self, project_root: Path, steam_data: dict, other_games_data: dict):
        self.project_root = project_root
        self.steam_data = steam_data
        self.other_games_data = other_games_data
        self.config_manager = ConfigManager(project_root)
        self.skip_steam_matching_games = self.config_manager.get_skip_steam_matching_games()

    def check_data_quality(self, channels_config: dict) -> int:
        """Check data quality across all channels and games"""
        print("\n" + "="*80)
        print("DATA QUALITY REPORT")
        print("="*80)

        total_issues = 0

        # 1. Check for videos with missing game data
        total_issues += self._check_videos_missing_games(channels_config)

        # 2. Check for missing Steam games referenced in videos
        total_issues += self._check_missing_steam_games(channels_config)

        # 3. Check Steam games for missing metadata
        total_issues += self._check_steam_metadata_quality()

        # 4. Check other games for missing metadata
        total_issues += self._check_other_games_metadata_quality()

        # 5. Check for stale data
        self._check_stale_data()

        # 6. Summary
        self._print_summary(total_issues, channels_config)

        return total_issues

    def _check_videos_missing_games(self, channels_config: dict) -> int:
        """Check for videos with missing game data"""
        print("\n1. CHECKING VIDEOS WITH MISSING GAME DATA")
        print("-" * 50)

        videos_missing_games = 0
        videos_with_games = 0
        total_issues = 0

        for channel_id in channels_config:
            videos_file = self.project_root / 'data' / f'videos-{channel_id}.json'
            if not videos_file.exists():
                print(f"⚠️  Missing video file for channel {channel_id}: {videos_file}")
                total_issues += 1
                continue

            with videos_file.open() as f:
                channel_data = json.load(f)

            channel_videos_missing = 0
            channel_videos_with_games = 0

            for video_id, video in channel_data.get('videos', {}).items():
                has_game = bool(video.get('steam_app_id') or video.get('itch_url') or video.get('crazygames_url'))

                # Check if this video has a detected game that's intentionally skipped
                youtube_detected_game = video.get('youtube_detected_game', '')
                is_intentionally_skipped = any(skip_game.lower() in youtube_detected_game.lower()
                                             for skip_game in self.skip_steam_matching_games)

                if has_game or is_intentionally_skipped:
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

        return total_issues

    def _check_missing_steam_games(self, channels_config: dict) -> int:
        """Check for missing Steam games referenced in videos"""
        print("\n\n2. CHECKING FOR MISSING STEAM GAMES")
        print("-" * 50)

        # Collect all Steam app IDs referenced in videos
        referenced_steam_apps = set()
        for channel_id in channels_config:
            videos_file = self.project_root / 'data' / f'videos-{channel_id}.json'
            if videos_file.exists():
                with videos_file.open() as f:
                    channel_data = json.load(f)

                for video in channel_data.get('videos', {}).values():
                    steam_app_id = video.get('steam_app_id')
                    if steam_app_id:
                        referenced_steam_apps.add(steam_app_id)

        # Check which referenced Steam games are missing from our database
        missing_steam_games = [
            app_id for app_id in referenced_steam_apps
            if app_id not in self.steam_data.get('games', {})
        ]

        total_issues = 0
        if missing_steam_games:
            print(f"❌ Found {len(missing_steam_games)} Steam games referenced in videos but missing from database:")
            for _i, app_id in enumerate(missing_steam_games[:10]):  # Show first 10
                print(f"   🎮 Steam App ID: {app_id} (https://store.steampowered.com/app/{app_id})")

            if len(missing_steam_games) > 10:
                print(f"   ... and {len(missing_steam_games) - 10} more missing Steam games")

            total_issues += len(missing_steam_games)
            print(f"\n📊 {len(missing_steam_games)} out of {len(referenced_steam_apps)} referenced Steam games are missing ({(len(missing_steam_games)/len(referenced_steam_apps)*100):.1f}%)")
        else:
            print("✅ All referenced Steam games have metadata in database")

        print(f"Total referenced Steam games: {len(referenced_steam_apps)}")
        print(f"Steam games in database: {len(self.steam_data.get('games', {}))}")

        return total_issues

    def _check_steam_metadata_quality(self) -> int:
        """Check Steam games for missing metadata"""
        print("\n\n3. CHECKING STEAM GAMES METADATA")
        print("-" * 50)

        steam_issues = 0
        required_steam_fields = ['name', 'steam_app_id', 'tags', 'positive_review_percentage']
        optional_steam_fields = ['header_image', 'review_summary', 'price']

        for app_id, game in self.steam_data.get('games', {}).items():
            missing_required = []
            missing_optional = []

            # Check required fields, but skip positive_review_percentage for coming soon games
            for field in required_steam_fields:
                if not getattr(game, field, None):
                    # Coming soon games legitimately don't have review data
                    if field == 'positive_review_percentage' and game.coming_soon:
                        continue
                    # Games with insufficient reviews also legitimately don't have percentage scores
                    if field == 'positive_review_percentage' and game.insufficient_reviews:
                        continue
                    # Games with no reviews also legitimately don't have percentage scores
                    if field == 'positive_review_percentage' and game.review_count == 0:
                        continue
                    missing_required.append(field)

            for field in optional_steam_fields:
                if not getattr(game, field, None):
                    # Coming soon games legitimately don't have price or review data
                    if game.coming_soon and field in ['review_summary', 'price']:
                        continue
                    missing_optional.append(field)

            if missing_required:
                print(f"❌ Steam game {app_id} ({game.name}) missing required: {', '.join(missing_required)}")
                steam_issues += 1
            elif missing_optional:
                print(f"⚠️  Steam game {app_id} ({game.name}) missing optional: {', '.join(missing_optional)}")

        # Count coming soon games and insufficient reviews for informational purposes
        coming_soon_count = sum(1 for game in self.steam_data.get('games', {}).values() if game.coming_soon)
        insufficient_reviews_count = sum(1 for game in self.steam_data.get('games', {}).values() if game.insufficient_reviews)
        no_reviews_count = sum(1 for game in self.steam_data.get('games', {}).values() if game.review_count == 0)

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

        return steam_issues

    def _check_other_games_metadata_quality(self) -> int:
        """Check other games for missing metadata"""
        print("\n\n4. CHECKING OTHER GAMES METADATA")
        print("-" * 50)

        other_issues = 0
        required_other_fields = ['name', 'platform', 'tags']
        optional_other_fields = ['header_image', 'positive_review_percentage', 'review_count']

        for game in self.other_games_data.get('games', {}).values():
            missing_required = []
            missing_optional = []

            for field in required_other_fields:
                value = getattr(game, field, None)
                if not value or (field == 'tags' and len(value) == 0):
                    missing_required.append(field)

            missing_optional = [
                field for field in optional_other_fields
                if not getattr(game, field, None)
            ]

            if missing_required:
                print(f"❌ {game.platform} game '{game.name}' missing required: {', '.join(missing_required)}")
                other_issues += 1
            elif missing_optional:
                print(f"⚠️  {game.platform} game '{game.name}' missing optional: {', '.join(missing_optional)}")

        print(f"\nOther games checked: {len(self.other_games_data.get('games', {}))}")
        if other_issues == 0:
            print("✅ All other games have required metadata")
        else:
            print(f"❌ {other_issues} other games have missing required metadata")

        return other_issues

    def _check_stale_data(self) -> None:
        """Check for stale data"""
        print("\n\n5. CHECKING FOR STALE DATA")
        print("-" * 50)

        stale_threshold = datetime.now() - timedelta(days=30)  # 30 days
        stale_steam = 0
        stale_other = 0

        for app_id, game in self.steam_data.get('games', {}).items():
            if game.last_updated:
                try:
                    last_updated_date = datetime.fromisoformat(game.last_updated)
                    if last_updated_date < stale_threshold:
                        days_old = (datetime.now() - last_updated_date).days
                        print(f"🕐 Steam game {app_id} ({game.name}) is {days_old} days old")
                        stale_steam += 1
                except ValueError:
                    print(f"❌ Steam game {app_id} has invalid last_updated format: {game.last_updated}")

        for game in self.other_games_data.get('games', {}).values():
            last_updated = game.last_updated
            if last_updated:
                try:
                    last_updated_date = datetime.fromisoformat(last_updated)
                    if last_updated_date < stale_threshold:
                        days_old = (datetime.now() - last_updated_date).days
                        print(f"🕐 {game.platform} game '{game.name}' is {days_old} days old")
                        stale_other += 1
                except ValueError:
                    print(f"❌ {game.platform} game has invalid last_updated format: {last_updated}")

        if stale_steam == 0 and stale_other == 0:
            print("✅ No stale game data found")
        else:
            print(f"📊 {stale_steam} Steam games and {stale_other} other games are older than 30 days")

    def _print_summary(self, total_issues: int, channels_config: dict) -> None:
        """Print summary report"""
        print("\n\n" + "="*80)
        print("SUMMARY")
        print("="*80)

        # Count total videos across all channels
        total_videos = 0
        videos_with_games = 0
        videos_missing_games = 0

        for channel_id in channels_config:
            videos_file = self.project_root / 'data' / f'videos-{channel_id}.json'
            if videos_file.exists():
                with videos_file.open() as f:
                    channel_data = json.load(f)
                for video in channel_data.get('videos', {}).values():
                    total_videos += 1
                    has_game = bool(video.get('steam_app_id') or video.get('itch_url') or video.get('crazygames_url'))

                    # Check if this video has a detected game that's intentionally skipped
                    youtube_detected_game = video.get('youtube_detected_game', '')
                    is_intentionally_skipped = any(skip_game.lower() in youtube_detected_game.lower()
                                                 for skip_game in self.skip_steam_matching_games)

                    if has_game or is_intentionally_skipped:
                        videos_with_games += 1
                    else:
                        videos_missing_games += 1

        # Count stale games
        stale_threshold = datetime.now() - timedelta(days=30)
        stale_steam = sum(1 for game in self.steam_data.get('games', {}).values()
                         if game.last_updated and datetime.fromisoformat(game.last_updated) < stale_threshold)
        stale_other = sum(1 for game in self.other_games_data.get('games', {}).values()
                         if game.last_updated and datetime.fromisoformat(game.last_updated) < stale_threshold)

        print(f"📊 Total videos: {total_videos}")
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
