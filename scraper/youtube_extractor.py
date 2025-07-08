"""
YouTube video extraction and metadata utilities
"""

import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional

import requests
import yt_dlp


class YouTubeExtractor:
    """Handles YouTube video metadata extraction and game detection"""

    def __init__(self):
        # yt-dlp options
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'force_generic_extractor': False,
        }

    def get_channel_videos_lightweight(self, channel_url: str, skip_count: int, batch_size: int) -> List[Dict]:
        """Fetch lightweight video info (just IDs and titles) from YouTube channel"""
        videos = []

        # Use playlist start/end to simulate offset
        ydl_opts_lightweight = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'force_generic_extractor': False,
            'playliststart': skip_count + 1,
            'playlistend': skip_count + batch_size
        }

        with yt_dlp.YoutubeDL(ydl_opts_lightweight) as ydl:
            try:
                logging.info(f"Fetching lightweight data from {channel_url}")
                info = ydl.extract_info(channel_url, download=False)

                if 'entries' in info:
                    entries = info['entries']
                else:
                    entries = [info] if info else []

                # Process entries - just extract basic info
                for entry in entries:
                    if not entry:
                        continue

                    video_id = entry.get('id')
                    if not video_id:
                        continue

                    videos.append({
                        'video_id': video_id,
                        'title': entry.get('title', ''),
                        'published_at': datetime.fromtimestamp(
                            entry.get('timestamp', 0)
                        ).isoformat() if entry.get('timestamp') and entry.get('timestamp') > 0 else None,
                        'thumbnail': entry.get('thumbnail', '')
                    })

            except Exception as e:
                logging.error(f"Error fetching lightweight channel videos: {e}")

        return videos

    def get_full_video_metadata(self, video_id: str) -> Optional[Dict]:
        """Fetch full metadata for a specific video"""
        try:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                video_info = ydl.extract_info(video_url, download=False)

                return {
                    'video_id': video_id,
                    'title': video_info.get('title', ''),
                    'description': video_info.get('description', ''),
                    'published_at': datetime.fromtimestamp(
                        video_info.get('timestamp', 0)
                    ).isoformat() if video_info.get('timestamp') else '',
                    'thumbnail': video_info.get('thumbnail', '')
                }
        except Exception as e:
            error_msg = str(e)
            if "This video is available to this channel's members" in error_msg:
                logging.info(f"Skipping member-only video {video_id}")
            elif "Private video" in error_msg or "Video unavailable" in error_msg:
                logging.info(f"Skipping unavailable video {video_id}")
            else:
                logging.error(f"Error fetching full metadata for video {video_id}: {e}")
            return None

    def extract_youtube_detected_game(self, video_id: str) -> Optional[str]:
        """Extract YouTube's detected game from JSON data as last resort"""
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                return None

            page_content = response.text

            # Look for YouTube's initial data JSON
            pattern = r'var ytInitialData = ({.*?});'
            match = re.search(pattern, page_content)
            if not match:
                return None

            data = json.loads(match.group(1))

            # Navigate to the rich metadata renderer
            try:
                contents = data['contents']['twoColumnWatchNextResults']['results']['results']['contents']
                for content in contents:
                    if 'videoSecondaryInfoRenderer' in content:
                        metadata_container = content['videoSecondaryInfoRenderer'].get('metadataRowContainer', {})
                        rows = metadata_container.get('metadataRowContainerRenderer', {}).get('rows', [])

                        for row in rows:
                            if 'richMetadataRowRenderer' in row:
                                rich_contents = row['richMetadataRowRenderer'].get('contents', [])
                                for rich_content in rich_contents:
                                    if 'richMetadataRenderer' in rich_content:
                                        title = rich_content['richMetadataRenderer'].get('title', {})
                                        if 'simpleText' in title:
                                            game_title = title['simpleText'].strip()
                                            if game_title and len(game_title) > 3:
                                                return game_title
            except (KeyError, TypeError):
                pass

            return None

        except Exception as e:
            logging.debug(f"Error extracting YouTube detected game for {video_id}: {e}")
            return None
