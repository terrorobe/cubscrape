"""
Configuration management utilities
"""

import json
from pathlib import Path
from typing import Dict


class ConfigManager:
    """Handles configuration loading and management"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.config_path = project_root / 'config.json'
        self._config = None

    def load_config(self) -> Dict:
        """Load configuration from config.json"""
        if self._config is None:
            if self.config_path.exists():
                with open(self.config_path) as f:
                    self._config = json.load(f)
            else:
                self._config = {'channels': {}}
        return self._config

    def get_channels(self) -> Dict:
        """Get channels configuration"""
        config = self.load_config()
        return config.get('channels', {})

    def get_channel_config(self, channel_id: str) -> Dict:
        """Get configuration for a specific channel"""
        channels = self.get_channels()
        return channels.get(channel_id, {})

    def is_channel_enabled(self, channel_id: str) -> bool:
        """Check if a channel is enabled"""
        channel_config = self.get_channel_config(channel_id)
        return channel_config.get('enabled', True)

    def get_channel_url(self, channel_id: str) -> str:
        """Get URL for a specific channel"""
        channel_config = self.get_channel_config(channel_id)
        return channel_config.get('url', '')

    def validate_channel_exists(self, channel_id: str) -> bool:
        """Validate that a channel exists in config"""
        channels = self.get_channels()
        return channel_id in channels

    def get_skip_steam_matching_games(self) -> list[str]:
        """Get list of games to skip Steam matching for"""
        config = self.load_config()
        return config.get('skip_steam_matching', [])
