"""
Data management utilities for the YouTube Steam scraper
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    from .reference_validator import ReferenceValidator

from .models import OtherGameData, SteamGameData, VideoData, VideoGameReference
from .utils import load_json, save_data


class VideosDataDict(TypedDict):
    """Type definition for videos data dictionary"""
    videos: dict[str, VideoData]
    last_updated: str | None


class SteamDataDict(TypedDict):
    """Type definition for Steam games data dictionary"""
    games: dict[str, SteamGameData]
    last_updated: str | None


class OtherGamesDataDict(TypedDict):
    """Type definition for other games data dictionary"""
    games: dict[str, OtherGameData]
    last_updated: str | None


class DataManager:
    """Handles loading, saving, and managing data files"""

    def __init__(self, project_root: Path, validate_on_save: bool = True):
        self.project_root = project_root
        self.data_dir = project_root / 'data'
        self.validate_on_save = validate_on_save
        self._validator: ReferenceValidator | None = None  # Lazy-loaded to avoid circular imports

    def get_videos_file_path(self, channel_id: str) -> Path:
        """Get path to videos data file for a channel"""
        return self.data_dir / f'videos-{channel_id}.json'

    def get_steam_file_path(self) -> Path:
        """Get path to Steam games data file"""
        return self.data_dir / 'steam_games.json'

    def get_other_games_file_path(self) -> Path:
        """Get path to other games data file"""
        return self.data_dir / 'other_games.json'

    def _get_validator(self) -> 'ReferenceValidator':
        """Lazy-load validator to avoid circular imports"""
        if self._validator is None:
            from .reference_validator import ReferenceValidator
            self._validator = ReferenceValidator(self)
        return self._validator

    def _run_validation_if_enabled(self, channel_ids: list[str] | None = None) -> bool:
        """Run validation if enabled. Returns True if validation passes or is disabled."""
        if not self.validate_on_save:
            return True

        if channel_ids is None:
            # Try to discover channel IDs
            try:
                from .config_manager import ConfigManager
                config_manager = ConfigManager(self.project_root)
                channels = config_manager.get_channels()
                channel_ids = list(channels.keys())
            except Exception as e:
                logging.warning(f"Could not load channel IDs for validation: {e}")
                return True  # Don't fail save due to config issues

        try:
            validator = self._get_validator()
            errors = validator.validate_all(channel_ids)
            validation_errors = [e for e in errors if e.severity == "error"]

            if validation_errors:
                logging.error(f"Validation failed with {len(validation_errors)} errors:")
                for error in validation_errors[:5]:  # Show first 5 errors
                    logging.error(f"  • [{error.entity_type}:{error.entity_id}] {error.error_type}: {error.message}")
                if len(validation_errors) > 5:
                    logging.error(f"  ... and {len(validation_errors) - 5} more errors")
                logging.error("Save operation aborted due to validation failures. Run 'cubscrape validate' for full report.")
                return False
            else:
                logging.debug("Validation passed")
                return True
        except Exception as e:
            logging.warning(f"Validation failed due to error: {e}")
            return True  # Don't fail save due to validation system issues

    def load_videos_data(self, channel_id: str) -> VideosDataDict:
        """Load and convert video data for a channel"""
        videos_file = self.get_videos_file_path(channel_id)
        videos_raw = load_json(videos_file, {'videos': {}, 'last_updated': None})

        # Convert loaded dictionaries to VideoData objects
        videos_converted = {}
        for vid, vdata in videos_raw['videos'].items():
            try:
                videos_converted[vid] = self._ensure_video_data(vdata, vid)
            except (TypeError, ValueError) as e:
                logging.error(f"Skipping invalid video data for {vid}: {e}")
                # Skip this video entirely rather than creating broken data
                continue

        return {
            'videos': videos_converted,
            'last_updated': videos_raw.get('last_updated')
        }

    def load_steam_data(self) -> SteamDataDict:
        """Load and convert Steam games data"""
        steam_file = self.get_steam_file_path()
        steam_raw = load_json(steam_file, {'games': {}, 'last_updated': None})

        # Convert loaded dictionaries to SteamGameData objects
        games_converted = {}
        for app_id, sdata in steam_raw['games'].items():
            try:
                games_converted[app_id] = self._ensure_steam_data(sdata, app_id)
            except (TypeError, ValueError) as e:
                logging.error(f"Skipping invalid Steam game data for {app_id}: {e}")
                # Skip this game entirely rather than creating broken data
                continue

        return {
            'games': games_converted,
            'last_updated': steam_raw.get('last_updated')
        }

    def load_other_games_data(self) -> OtherGamesDataDict:
        """Load and convert other games data"""
        other_games_file = self.get_other_games_file_path()
        other_games_raw = load_json(other_games_file, {'games': {}, 'last_updated': None})

        # Convert loaded dictionaries to OtherGameData objects
        games_converted = {}
        for game_id, gdata in other_games_raw['games'].items():
            try:
                games_converted[game_id] = self._ensure_other_game_data(gdata, game_id)
            except (TypeError, ValueError) as e:
                logging.error(f"Skipping invalid other game data for {game_id}: {e}")
                # Skip this game entirely rather than creating broken data
                continue

        return {
            'games': games_converted,
            'last_updated': other_games_raw.get('last_updated')
        }

    def save_videos_data(self, videos_data: VideosDataDict, channel_id: str) -> None:
        """Save video data to JSON file"""
        videos_file = self.get_videos_file_path(channel_id)

        # Convert VideoData objects to dictionaries for JSON serialization
        videos_dict = {}
        for video_id, video_data in videos_data['videos'].items():
            if isinstance(video_data, VideoData):
                video_dict = video_data.model_dump(exclude_none=True)
                # Remove False boolean values to keep JSON clean
                video_dict = self._clean_dict_for_json(video_dict)
                videos_dict[video_id] = video_dict
            else:
                videos_dict[video_id] = video_data

        data_to_save = {
            'videos': videos_dict
        }

        # Run validation before saving
        if not self._run_validation_if_enabled([channel_id]):
            raise ValueError("Data validation failed - save operation aborted")

        save_data(data_to_save, videos_file)

    def save_steam_data(self, steam_data: SteamDataDict) -> None:
        """Save Steam data to JSON file"""
        steam_file = self.get_steam_file_path()

        # Convert SteamGameData objects to dictionaries for JSON serialization
        games_dict = {}
        for app_id, game_data in steam_data['games'].items():
            if isinstance(game_data, SteamGameData):
                game_dict = game_data.model_dump(exclude_none=True)
                # Remove False boolean values to keep JSON clean
                game_dict = self._clean_dict_for_json(game_dict)
                games_dict[app_id] = game_dict
            else:
                games_dict[app_id] = game_data

        data_to_save = {
            'games': games_dict
        }

        # Run validation before saving
        if not self._run_validation_if_enabled():
            raise ValueError("Data validation failed - save operation aborted")

        save_data(data_to_save, steam_file)

    def save_other_games_data(self, other_games_data: OtherGamesDataDict) -> None:
        """Save other games data to JSON file"""
        other_games_file = self.get_other_games_file_path()

        # Convert OtherGameData objects to dictionaries for JSON serialization
        games_dict = {}
        for game_id, game_data in other_games_data['games'].items():
            if isinstance(game_data, OtherGameData):
                game_dict = game_data.model_dump(exclude_none=True)
                # Remove False boolean values to keep JSON clean
                game_dict = self._clean_dict_for_json(game_dict)
                games_dict[game_id] = game_dict
            else:
                games_dict[game_id] = game_data

        data_to_save = {
            'games': games_dict
        }

        # Run validation before saving
        if not self._run_validation_if_enabled():
            raise ValueError("Data validation failed - save operation aborted")

        save_data(data_to_save, other_games_file)

    def _ensure_video_data(self, data: Any, video_id: str = "unknown") -> VideoData:
        """Ensure data is VideoData instance - fail fast on invalid data"""
        if isinstance(data, VideoData):
            return data
        elif isinstance(data, dict):
            try:
                return self._dict_to_video_data(data)
            except (TypeError, ValueError) as e:
                raise ValueError(f"Failed to convert video data for {video_id}: {e}. Data: {data}") from e
        else:
            raise TypeError(f"Expected dict or VideoData for {video_id}, got {type(data).__name__}. Data: {data}")

    def _ensure_steam_data(self, data: Any, app_id: str = "unknown") -> SteamGameData:
        """Ensure data is SteamGameData instance - fail fast on invalid data"""
        if isinstance(data, SteamGameData):
            return data
        elif isinstance(data, dict):
            try:
                return self._dict_to_steam_data(data)
            except (TypeError, ValueError) as e:
                raise ValueError(f"Failed to convert Steam data for {app_id}: {e}. Data: {data}") from e
        else:
            raise TypeError(f"Expected dict or SteamGameData for {app_id}, got {type(data).__name__}. Data: {data}")

    def _ensure_other_game_data(self, data: Any, game_id: str = "unknown") -> OtherGameData:
        """Ensure data is OtherGameData instance - fail fast on invalid data"""
        if isinstance(data, OtherGameData):
            return data
        elif isinstance(data, dict):
            try:
                return self._dict_to_other_game_data(data)
            except (TypeError, ValueError) as e:
                raise ValueError(f"Failed to convert other game data for {game_id}: {e}. Data: {data}") from e
        else:
            raise TypeError(f"Expected dict or OtherGameData for {game_id}, got {type(data).__name__}. Data: {data}")

    def _dict_to_video_data(self, video_dict: dict) -> VideoData:
        """Convert dictionary to VideoData object"""
        # Handle game_references conversion
        if 'game_references' in video_dict:
            game_refs = []
            for ref_dict in video_dict['game_references']:
                if isinstance(ref_dict, dict):
                    game_refs.append(VideoGameReference(**ref_dict))
                else:
                    game_refs.append(ref_dict)
            video_dict['game_references'] = game_refs

        return VideoData(**video_dict)

    def _dict_to_steam_data(self, steam_dict: dict) -> SteamGameData:
        """Convert dictionary to SteamGameData object"""
        return SteamGameData(**steam_dict)

    def _dict_to_other_game_data(self, game_dict: dict) -> OtherGameData:
        """Convert dictionary to OtherGameData object"""
        return OtherGameData(**game_dict)

    def _clean_dict_for_json(self, data_dict: dict) -> dict[str, Any]:
        """Remove None values and False boolean values to keep JSON clean"""
        cleaned: dict[str, Any] = {}
        for k, v in data_dict.items():
            if v is None or v is False:
                continue
            elif isinstance(v, dict):
                cleaned[k] = self._clean_dict_for_json(v)
            elif isinstance(v, list):
                cleaned_list = []
                for item in v:
                    if isinstance(item, dict):
                        cleaned_list.append(self._clean_dict_for_json(item))
                    else:
                        cleaned_list.append(item)
                cleaned[k] = cleaned_list
            else:
                cleaned[k] = v
        return cleaned

    def is_game_referenced_by_videos(self, platform: str, platform_id: str) -> bool:
        """Check if a game (by platform and ID) is referenced by any video across all channels"""
        video_files = list(self.project_root.glob("data/videos-*.json"))

        for video_file in video_files:
            try:
                videos_data = load_json(video_file, {})
                videos = videos_data.get('videos', {})

                for video_data in videos.values():
                    game_references = video_data.get('game_references', [])
                    for ref in game_references:
                        if (ref.get('platform') == platform and
                            ref.get('platform_id') == platform_id):
                            return True

            except Exception as e:
                logging.warning(f"Error checking video references in {video_file}: {e}")
                continue

        return False

    def is_steam_app_referenced_by_videos(self, app_id: str) -> bool:
        """Check if a Steam app ID is referenced by any video across all channels (legacy compatibility)"""
        return self.is_game_referenced_by_videos('steam', app_id)
