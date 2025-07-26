#!/usr/bin/env python3
"""
YouTube Channel Video Scraper with Steam Game Data Integration
"""

import json
import logging
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from .config_manager import ConfigManager
from .data_manager import DataManager
from .data_quality import DataQualityChecker
from .database_manager import DatabaseManager
from .game_inference import GameInferenceEngine
from .game_unifier import load_all_unified_games
from .models import SteamGameData, VideoData
from .steam_fetcher import SteamDataFetcher
from .video_processor import VideoProcessor
from .youtube_extractor import YouTubeExtractor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class YouTubeSteamScraper:
    def __init__(self, channel_id: str):
        # Get the directory of this script, then build paths relative to project root
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent

        # Initialize managers and utilities
        self.config_manager = ConfigManager(project_root)
        self.data_manager = DataManager(project_root)
        self.youtube_extractor = YouTubeExtractor()
        self.game_inference = GameInferenceEngine()

        # Load data
        self.videos_data = self.data_manager.load_videos_data(channel_id)
        self.steam_data = self.data_manager.load_steam_data()
        self.other_games_data = self.data_manager.load_other_games_data()

        # Store channel info
        self.channel_id = channel_id

        # Initialize Steam fetcher
        self.steam_fetcher = SteamDataFetcher(self.data_manager)

        # Initialize video processor
        self.video_processor = VideoProcessor(
            self.data_manager, self.youtube_extractor, self.config_manager,
            self.game_inference, self.other_games_data
        )



    def save_videos(self) -> None:
        """Save video data to JSON file"""
        self.data_manager.save_videos_data(self.videos_data, self.channel_id)

    def save_steam(self) -> None:
        """Save Steam data to JSON file"""
        self.data_manager.save_steam_data(self.steam_data)

    def extract_youtube_detected_game(self, video_id: str) -> str | None:
        """Extract YouTube's detected game from JSON data as last resort"""
        return self.youtube_extractor.extract_youtube_detected_game(video_id)


    def fetch_steam_data(self, steam_url: str) -> SteamGameData | None:
        """Fetch game data from Steam using the modular fetcher"""
        # Always fetch both EUR and USD prices for new games
        return self.steam_fetcher.fetch_data(steam_url, fetch_usd=True)

    def process_videos(self, channel_url: str, max_new_videos: int | None = None, fetch_newest_first: bool = False, cutoff_date: str | None = None) -> int:
        """Process YouTube videos only"""
        new_videos_processed = self.video_processor.process_videos(
            self.videos_data, channel_url, max_new_videos, fetch_newest_first, cutoff_date
        )
        self.save_videos()
        return new_videos_processed

    def reprocess_video_descriptions(self) -> int:
        """Reprocess existing video descriptions to extract game links with current logic"""
        updated_count = self.video_processor.reprocess_video_descriptions(self.videos_data)
        self.save_videos()
        return updated_count

    def get_channel_videos_lightweight(self, channel_url: str, skip_count: int, batch_size: int) -> list[dict]:
        """Fetch lightweight video info (just IDs and titles) from YouTube channel"""
        return self.video_processor.get_channel_videos_lightweight(channel_url, skip_count, batch_size)


    def _process_video_game_links(self, video: VideoData) -> VideoData:
        """Extract and process game links from a video"""
        return self.video_processor.process_video_game_links(video)


    def check_data_quality(self, channels_config: dict) -> int:
        """Check data quality across all channels and games"""
        # Get the directory of this script, then build paths relative to project root
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent

        quality_checker = DataQualityChecker(project_root, self.steam_data, self.other_games_data)
        return quality_checker.check_data_quality(channels_config)

    def search_steam_games(self, query: str) -> list[dict]:
        """Search Steam for games by name"""
        return self.game_inference.search_steam_games(query)

    def find_steam_match(self, game_name: str, confidence_threshold: float = 0.5) -> dict | None:
        """Find best Steam match for a game name with confidence scoring"""
        return self.game_inference.find_steam_match(game_name, confidence_threshold)

    def find_steam_match_interactive(self, game_name: str, confidence_threshold: float = 0.5) -> dict | None:
        """Find Steam match with interactive prompting for low confidence results"""
        return self.game_inference.find_steam_match_interactive(game_name, confidence_threshold)


    def _should_process_video_for_inference(self, video: dict) -> str | None:
        """Determine if video needs processing for game inference"""
        # Case 1: No game references at all
        game_references = video.get('game_references', [])
        if not game_references:
            return "no_game_data"

        # Case 2: Has Steam references but they're missing from our database
        for game_ref in game_references:
            if game_ref.get('platform') == 'steam':
                steam_app_id = game_ref.get('platform_id')
                if steam_app_id:
                    game_data = self.steam_data.get('games', {}).get(steam_app_id)
                    if not game_data:
                        return "missing_steam_game"
                    # Case 3: Has Steam reference but it points to an unresolved stub
                    if game_data.is_stub and not game_data.resolved_to:
                        return "stub_entry"

        return None

    def _check_steam_availability(self, app_id: str) -> str:
        """Check if Steam app is still available"""
        return self.game_inference.check_steam_availability(app_id)

    def resolve_games(self, channels_config: dict) -> int:
        """Resolve games for videos with missing, broken, or stub game data"""
        print("\n" + "="*80)
        print("GAME RESOLUTION FOR VIDEOS")
        print("="*80)

        total_videos_processed = 0
        games_found = 0
        missing_resolved = 0
        stubs_resolved = 0

        # Load all channel video files
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent

        for channel_id in channels_config:
            videos_file = project_root / 'data' / f'videos-{channel_id}.json'
            if not videos_file.exists():
                print(f"⚠️  Missing video file for channel {channel_id}: {videos_file}")
                continue

            with videos_file.open() as f:
                channel_data = json.load(f)

            print(f"\n📺 Processing channel: {channel_id}")

            # Find videos that need processing
            videos_to_process = []
            for video_id, video in channel_data.get('videos', {}).items():
                process_reason = self._should_process_video_for_inference(video)
                if process_reason:
                    videos_to_process.append((video_id, video, process_reason))

            if not videos_to_process:
                print("   ✅ All videos have valid game data")
                continue

            # Categorize videos
            no_game_data = [v for v in videos_to_process if v[2] == "no_game_data"]
            missing_steam = [v for v in videos_to_process if v[2] == "missing_steam_game"]
            stub_entries = [v for v in videos_to_process if v[2] == "stub_entry"]

            print(f"   🔍 Found {len(no_game_data)} videos without game data")
            print(f"   🔍 Found {len(missing_steam)} videos with missing Steam games")
            print(f"   🔍 Found {len(stub_entries)} videos with unresolved stub entries")

            channel_games_found = 0
            channel_missing_resolved = 0
            channel_stubs_resolved = 0

            # Process all videos that need inference
            for _video_id, video, reason in videos_to_process:
                total_videos_processed += 1
                title = video.get('title', '')

                if reason == "missing_steam_game":
                    youtube_url = f"https://www.youtube.com/watch?v={video.get('video_id')}"
                    print(f"\n   📹 {title} [MISSING STEAM: {video.get('steam_app_id')}]")
                    print(f"      🔗 {youtube_url}")

                    # First, try to fetch the missing Steam game directly
                    missing_app_id = video.get('steam_app_id')
                    availability = self._check_steam_availability(missing_app_id)

                    if availability == "available":
                        print(f"      🔄 Steam app {missing_app_id} is available, attempting fetch...")
                        try:
                            steam_url = f"https://store.steampowered.com/app/{missing_app_id}"
                            steam_data = self.fetch_steam_data(steam_url)
                            if steam_data:
                                steam_data = replace(steam_data, last_updated=datetime.now().isoformat())
                                self.steam_data['games'][missing_app_id] = steam_data
                                print(f"      ✅ Successfully fetched: {steam_data.name}")
                                missing_resolved += 1
                                channel_missing_resolved += 1
                                continue
                        except Exception as e:
                            print(f"      ⚠️  Failed to fetch {missing_app_id}: {e}")

                    elif availability == "depublished":
                        print(f"      🚫 Steam app {missing_app_id} is depublished, searching for alternatives...")
                        # Mark the original as broken and try to find alternatives
                        video['broken_app_id'] = missing_app_id
                        video['steam_app_id'] = None  # Clear so we can find alternative

                    else:
                        print(f"      ❓ Steam app {missing_app_id} status unknown, searching for alternatives...")

                elif reason == "stub_entry":
                    youtube_url = f"https://www.youtube.com/watch?v={video.get('video_id')}"
                    stub_app_id = video.get('steam_app_id')
                    print(f"\n   📹 {title} [STUB ENTRY: {stub_app_id}]")
                    print(f"      🔗 {youtube_url}")

                    # For stub entries, we need to extract game names from ALL videos referencing this stub
                    # Not just the current video, since multiple videos might provide different clues
                    print(f"      🔄 Finding alternative for stub {stub_app_id}...")
                    potential_names = self._extract_game_names_from_videos_with_steam_id(stub_app_id)

                    if not potential_names:
                        print(f"      ❌ No game names found for stub {stub_app_id}")
                        continue

                else:
                    youtube_url = f"https://www.youtube.com/watch?v={video.get('video_id')}"
                    print(f"\n   📹 {title}")
                    print(f"      🔗 {youtube_url}")

                # First try YouTube detection as it's more reliable than title parsing
                potential_names = []

                print("      🔍 Trying YouTube game detection...")
                detected_game = self.extract_youtube_detected_game(video.get('video_id'))
                if detected_game:
                    print(f"      🎮 YouTube detected: {detected_game}")
                    potential_names.append(detected_game)
                else:
                    print("      ❌ No YouTube game detection found")

                # Fallback to extracting game names from title
                title_names = self.game_inference.extract_potential_game_names_from_title(title)
                if title_names:
                    print(f"      📝 Title extracted: {title_names}")
                    potential_names.extend(title_names)

                if not potential_names:
                    print("      ❌ No potential game names found from YouTube or title")
                    continue

                print(f"      🎯 All potential names: {potential_names}")

                # Check if any potential names should skip Steam matching
                skip_games = self.config_manager.get_skip_steam_matching_games()
                should_skip_any = any(
                    any(skip_game.lower() in name.lower() for skip_game in skip_games)
                    for name in potential_names
                )

                if should_skip_any:
                    skipped_names = [name for name in potential_names
                                   if any(skip_game.lower() in name.lower() for skip_game in skip_games)]
                    print(f"      🚫 Steam matching skipped for {skipped_names} (in config skip list)")
                    continue

                # Search Steam for each potential name
                best_match = None

                for name in potential_names:
                    steam_match = self.find_steam_match_interactive(name, confidence_threshold=0.5)
                    if steam_match and (not best_match or steam_match['confidence'] > best_match['confidence']):
                            best_match = steam_match

                if best_match:
                    app_id = best_match['app_id']
                    game_name = best_match['name']
                    print(f"      ✅ Found match: {game_name} (App ID: {app_id}, confidence: {best_match['confidence']:.2f})")

                    if reason == "stub_entry":
                        # For stub entries, update the stub's resolved_to field, keep video unchanged
                        stub_app_id = video.get('steam_app_id')
                        if stub_app_id in self.steam_data.get('games', {}):
                            stub_data = self.steam_data['games'][stub_app_id]
                            stub_data.resolved_to = app_id
                            self.steam_data['games'][stub_app_id] = stub_data
                            print(f"      🔗 Updated stub {stub_app_id} to resolve to {app_id}")
                            channel_stubs_resolved += 1
                        else:
                            print(f"      ⚠️  Stub {stub_app_id} not found in steam_data")
                    else:
                        # For missing games and no game data, update video data as before
                        video['steam_app_id'] = app_id
                        video['inferred_game'] = True  # Mark as inferred for review
                        video['inference_reason'] = reason
                        video['last_updated'] = datetime.now().isoformat()

                    # Store YouTube detection info if it was used
                    if detected_game:
                        video['youtube_detected_game'] = detected_game
                        if detected_game == best_match['name']:
                            video['youtube_detected_matched'] = True

                    # Fetch full game data
                    try:
                        steam_url = f"https://store.steampowered.com/app/{app_id}"
                        steam_data = self.fetch_steam_data(steam_url)
                        if steam_data:
                            steam_data = replace(steam_data, last_updated=datetime.now().isoformat())
                            self.steam_data['games'][app_id] = steam_data
                            print(f"      📊 Fetched game metadata: {steam_data.name}")
                    except Exception as e:
                        logging.error(f"      ❌ Error fetching Steam data for {app_id}: {e}")

                    games_found += 1
                    if reason == "stub_entry":
                        # Stub resolution is tracked separately
                        pass
                    else:
                        channel_games_found += 1
                        if reason == "missing_steam_game":
                            missing_resolved += 1
                            channel_missing_resolved += 1
                else:
                    print("      ❌ No confident matches found on Steam")

            # Save updated video data and steam data
            if channel_games_found > 0 or channel_missing_resolved > 0:
                with videos_file.open('w') as f:
                    json.dump(channel_data, f, indent=2, sort_keys=True)
                print(f"   💾 Saved {channel_games_found} game inferences and {channel_missing_resolved} resolved missing games for {channel_id}")

            if channel_stubs_resolved > 0:
                self.data_manager.save_steam_data(self.steam_data)
                print(f"   💾 Saved {channel_stubs_resolved} resolved stub entries")
                stubs_resolved += channel_stubs_resolved

        # Save updated Steam data
        if games_found > 0 or missing_resolved > 0:
            self.save_steam()

        print("\n" + "="*80)
        print("GAME RESOLUTION SUMMARY")
        print("="*80)
        print(f"📊 Videos processed: {total_videos_processed}")
        print(f"🎮 New games found via inference: {games_found}")
        print(f"🔧 Missing Steam games resolved: {missing_resolved}")
        print(f"🔗 Stub entries resolved: {stubs_resolved}")
        print(f"✅ Total games found/resolved: {games_found + missing_resolved + stubs_resolved}")
        if total_videos_processed > 0:
            success_rate = ((games_found + missing_resolved + stubs_resolved) / total_videos_processed) * 100
            print(f"📈 Success rate: {success_rate:.1f}%")
        if games_found > 0:
            print("\n⚠️  Note: Inferred games are marked with 'inferred_game: true' for review")
        if missing_resolved > 0:
            print("⚠️  Note: Some videos may have 'broken_app_id' field for depublished games")
        if stubs_resolved > 0:
            print("⚠️  Note: Videos with resolved stub entries keep their original Steam IDs")
        print("="*80)

        return games_found + missing_resolved + stubs_resolved

    def _extract_game_names_from_videos_with_steam_id(self, steam_app_id: str) -> list[str]:
        """Extract potential game names from videos that reference a specific Steam app ID"""
        game_names = set()

        # Search through all video files
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent

        for videos_file in project_root.glob('data/videos-*.json'):
            try:
                with videos_file.open() as f:
                    channel_data = json.load(f)

                for video in channel_data.get('videos', {}).values():
                    if video.get('steam_app_id') == steam_app_id:
                        # Try YouTube detected game first
                        if video.get('youtube_detected_game'):
                            game_names.add(video['youtube_detected_game'])

                        # Extract from title using the game inference engine
                        title = video.get('title', '')
                        extracted_names = self.game_inference.extract_potential_game_names_from_title(title)
                        game_names.update(extracted_names)

            except Exception as e:
                logging.error(f"Error reading {videos_file}: {e}")

        return list(game_names)


def build_database() -> None:
    """Generate SQLite database from existing JSON files"""
    try:
        # Get project root
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent

        # Load existing JSON data
        all_games = load_all_unified_games(project_root)

        # Generate SQLite database
        db_manager = DatabaseManager()
        db_manager.create_database(all_games)

        logging.info("SQLite database generation completed")

    except Exception as e:
        logging.error(f"Database generation failed: {e}")
        raise



if __name__ == "__main__":
    from .cli_commands import CLICommands

    cli = CLICommands()
    cli.parse_and_execute()
