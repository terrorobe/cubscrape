"""
Data management utilities for the YouTube Steam scraper
"""

from dataclasses import asdict
from pathlib import Path
from typing import Dict

from models import OtherGameData, SteamGameData, VideoData
from utils import load_json, save_data


class DataManager:
    """Handles loading, saving, and managing data files"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.data_dir = project_root / 'data'

    def get_videos_file_path(self, channel_id: str) -> Path:
        """Get path to videos data file for a channel"""
        return self.data_dir / f'videos-{channel_id}.json'

    def get_steam_file_path(self) -> Path:
        """Get path to Steam games data file"""
        return self.data_dir / 'steam_games.json'

    def get_other_games_file_path(self) -> Path:
        """Get path to other games data file"""
        return self.data_dir / 'other_games.json'

    def load_videos_data(self, channel_id: str) -> Dict:
        """Load and convert video data for a channel"""
        videos_file = self.get_videos_file_path(channel_id)
        videos_raw = load_json(videos_file, {'videos': {}, 'last_updated': None})

        # Convert loaded dictionaries to VideoData objects
        return {
            'videos': {vid: self._dict_to_video_data(vdata) if isinstance(vdata, dict) else vdata
                      for vid, vdata in videos_raw['videos'].items()},
            'last_updated': videos_raw.get('last_updated')
        }

    def load_steam_data(self) -> Dict:
        """Load and convert Steam games data"""
        steam_file = self.get_steam_file_path()
        steam_raw = load_json(steam_file, {'games': {}, 'last_updated': None})

        # Convert loaded dictionaries to SteamGameData objects
        return {
            'games': {app_id: self._dict_to_steam_data(sdata) if isinstance(sdata, dict) else sdata
                     for app_id, sdata in steam_raw['games'].items()},
            'last_updated': steam_raw.get('last_updated')
        }

    def load_other_games_data(self) -> Dict:
        """Load and convert other games data"""
        other_games_file = self.get_other_games_file_path()
        other_games_raw = load_json(other_games_file, {'games': {}, 'last_updated': None})

        # Convert loaded dictionaries to OtherGameData objects
        return {
            'games': {game_id: self._dict_to_other_game_data(gdata) if isinstance(gdata, dict) else gdata
                     for game_id, gdata in other_games_raw['games'].items()},
            'last_updated': other_games_raw.get('last_updated')
        }

    def save_videos_data(self, videos_data: Dict, channel_id: str):
        """Save video data to JSON file"""
        videos_file = self.get_videos_file_path(channel_id)

        # Convert VideoData objects to dictionaries for JSON serialization
        videos_dict = {}
        for video_id, video_data in videos_data['videos'].items():
            if isinstance(video_data, VideoData):
                video_dict = asdict(video_data)
                # Remove None values and False boolean values to keep JSON clean
                video_dict = self._clean_dict_for_json(video_dict)
                videos_dict[video_id] = video_dict
            else:
                videos_dict[video_id] = video_data

        data_to_save = {
            'videos': videos_dict
        }
        save_data(data_to_save, videos_file)

    def save_steam_data(self, steam_data: Dict):
        """Save Steam data to JSON file"""
        steam_file = self.get_steam_file_path()

        # Convert SteamGameData objects to dictionaries for JSON serialization
        games_dict = {}
        for app_id, game_data in steam_data['games'].items():
            if isinstance(game_data, SteamGameData):
                game_dict = asdict(game_data)
                # Remove None values and False boolean values to keep JSON clean
                game_dict = self._clean_dict_for_json(game_dict)
                games_dict[app_id] = game_dict
            else:
                games_dict[app_id] = game_data

        data_to_save = {
            'games': games_dict
        }
        save_data(data_to_save, steam_file)

    def save_other_games_data(self, other_games_data: Dict):
        """Save other games data to JSON file"""
        other_games_file = self.get_other_games_file_path()

        # Convert OtherGameData objects to dictionaries for JSON serialization
        games_dict = {}
        for game_id, game_data in other_games_data['games'].items():
            if isinstance(game_data, OtherGameData):
                game_dict = asdict(game_data)
                # Remove None values and False boolean values to keep JSON clean
                game_dict = self._clean_dict_for_json(game_dict)
                games_dict[game_id] = game_dict
            else:
                games_dict[game_id] = game_data

        data_to_save = {
            'games': games_dict
        }
        save_data(data_to_save, other_games_file)

    def _dict_to_video_data(self, video_dict: Dict) -> VideoData:
        """Convert dictionary to VideoData object"""
        return VideoData(**video_dict)

    def _dict_to_steam_data(self, steam_dict: Dict) -> SteamGameData:
        """Convert dictionary to SteamGameData object"""
        return SteamGameData(**steam_dict)

    def _dict_to_other_game_data(self, game_dict: Dict) -> OtherGameData:
        """Convert dictionary to OtherGameData object"""
        return OtherGameData(**game_dict)

    def _clean_dict_for_json(self, data_dict: Dict) -> Dict:
        """Remove None values and False boolean values to keep JSON clean"""
        return {k: v for k, v in data_dict.items() if v is not None and v is not False}
