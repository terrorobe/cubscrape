"""
Unified Data Collector - Handles merging of persistent and in-memory data
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .scraper import YouTubeSteamScraper

from .data_manager import DataManager, VideosDataDict


class UnifiedDataCollector:
    """
    Collects and normalizes video data from both persistent storage and in-memory scrapers.
    Ensures all data is in consistent Pydantic model format before processing.
    """

    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager

    def collect_all_videos_data(self, channels: list[str],
                               pending_scrapers: list['YouTubeSteamScraper'] | None = None) -> dict[str, VideosDataDict]:
        """
        Collect and normalize all video data from both persistent storage and pending scrapers.

        Args:
            channels: List of channel IDs to collect data for
            pending_scrapers: Optional list of scrapers with in-memory data

        Returns:
            Dictionary mapping channel_id to normalized VideosDataDict (guaranteed Pydantic models)
        """
        unified_data = {}

        # Collect from persistent storage - DataManager ensures Pydantic models
        for channel_id in channels:
            unified_data[channel_id] = self.data_manager.load_videos_data(channel_id)

        # Merge in-memory data from pending scrapers - already in Pydantic format
        if pending_scrapers:
            for scraper in pending_scrapers:
                if hasattr(scraper, 'channel_id') and hasattr(scraper, 'videos_data'):
                    channel_id = scraper.channel_id

                    if scraper.videos_data and 'videos' in scraper.videos_data:
                        if channel_id in unified_data:
                            # Merge pending data with persistent data
                            # Pending data takes precedence for same video IDs
                            unified_data[channel_id]['videos'].update(scraper.videos_data['videos'])
                        else:
                            # Channel only has pending data
                            unified_data[channel_id] = scraper.videos_data.copy()

        return unified_data

    def collect_all_videos_flat(self, channels: list[str],
                               pending_scrapers: list['YouTubeSteamScraper'] | None = None) -> dict[str, Any]:
        """
        Collect all video data and return as a flat dictionary of video_id -> VideoData.
        Useful for operations that don't need channel grouping.

        Returns:
            Flat dictionary where all values are guaranteed to be VideoData objects
        """
        all_data = self.collect_all_videos_data(channels, pending_scrapers)

        flat_videos = {}
        for channel_data in all_data.values():
            flat_videos.update(channel_data['videos'])

        return flat_videos
