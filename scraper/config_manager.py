"""
Configuration management utilities
"""

import json
from pathlib import Path
from typing import Any


class ConfigManager:
    """Handles configuration loading and management"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.config_path = project_root / 'config.json'
        self._config: dict[str, Any] | None = None

    def load_config(self) -> dict[str, Any]:
        """Load configuration from config.json with validation"""
        if self._config is None:
            if self.config_path.exists():
                try:
                    with self.config_path.open() as f:
                        config_data = json.load(f)

                    if not isinstance(config_data, dict):
                        raise ValueError(
                            f"Invalid config file: Root must be a JSON object, got {type(config_data).__name__}. "
                            f"Check your {self.config_path} file."
                        )

                    self._config = config_data
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"Invalid JSON in config file {self.config_path}: {e}. "
                        f"Please check for syntax errors like missing commas, quotes, or brackets."
                    ) from e
            else:
                self._config = {'channels': {}}
        return self._config

    def get_channels(self) -> dict[str, Any]:
        """Get channels configuration"""
        config = self.load_config()
        channels = config.get('channels', {})

        if not isinstance(channels, dict):
            raise ValueError(
                f"Invalid config: 'channels' must be a dict, got {type(channels).__name__}. "
                f"Check your config.json file. Expected format: {{\"channels\": {{\"channel1\": {{...}}}}}}"
            )

        return channels

    def get_channel_config(self, channel_id: str) -> dict[Any, Any]:
        """Get configuration for a specific channel"""
        channels = self.get_channels()
        config = channels.get(channel_id, {})

        if not isinstance(config, dict):
            raise ValueError(
                f"Invalid config: channel '{channel_id}' must be a dict, got {type(config).__name__}. "
                f"Check your config.json file. Expected format: {{\"{channel_id}\": {{\"enabled\": true, \"url\": \"...\"}}}}"
            )

        return config

    def is_channel_enabled(self, channel_id: str) -> bool:
        """Check if a channel is enabled"""
        channel_config = self.get_channel_config(channel_id)
        enabled = channel_config.get('enabled', True)
        return bool(enabled)

    def get_channel_url(self, channel_id: str) -> str:
        """Get URL for a specific channel"""
        channel_config = self.get_channel_config(channel_id)
        url = channel_config.get('url', '')
        return str(url)

    def validate_channel_exists(self, channel_id: str) -> bool:
        """Validate that a channel exists in config"""
        channels = self.get_channels()
        return channel_id in channels

    def get_skip_steam_matching_games(self) -> list[str]:
        """Get list of games to skip Steam matching for"""
        config = self.load_config()
        skip_list = config.get('skip_steam_matching', [])

        if not isinstance(skip_list, list):
            raise ValueError(
                f"Invalid config: 'skip_steam_matching' must be a list, got {type(skip_list).__name__}. "
                f"Check your config.json file. Expected format: {{\"skip_steam_matching\": [\"game1\", \"game2\"]}}"
            )

        return skip_list

    def get_global_settings(self) -> dict[str, Any]:
        """Get global settings configuration"""
        config = self.load_config()
        global_settings = config.get('global_settings', {})

        if not isinstance(global_settings, dict):
            raise ValueError(
                f"Invalid config: 'global_settings' must be a dict, got {type(global_settings).__name__}. "
                f"Check your config.json file. Expected format: {{\"global_settings\": {{\"key\": \"value\"}}}}"
            )

        return global_settings

    def get_backfill_cutoff_date(self) -> str | None:
        """Get global backfill cutoff date"""
        global_settings = self.get_global_settings()
        cutoff_date = global_settings.get('backfill_cutoff_date')
        return str(cutoff_date) if cutoff_date else None

    def get_backfill_max_videos(self) -> int | None:
        """Get global backfill max videos limit"""
        global_settings = self.get_global_settings()
        max_videos = global_settings.get('backfill_max_videos')
        if max_videos is not None:
            if not isinstance(max_videos, int) or max_videos <= 0:
                raise ValueError(
                    f"Invalid config: 'backfill_max_videos' must be a positive integer, got {max_videos}. "
                    f"Check your config.json file."
                )
            return max_videos
        return None

    def get_cron_enable_backfill(self) -> bool:
        """Get whether cron should include backfill processing"""
        global_settings = self.get_global_settings()
        enable_backfill = global_settings.get('cron_enable_backfill', False)
        return bool(enable_backfill)

    def get_cron_backfill_total_videos(self) -> int:
        """Get total video budget for cron backfill runs (uses backfill_max_videos)"""
        max_videos = self.get_backfill_max_videos()
        return max_videos if max_videos is not None else 50
