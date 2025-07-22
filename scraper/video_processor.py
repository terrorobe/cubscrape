"""
Video Processing Pipeline

Handles YouTube video processing, game link extraction,
and video metadata management.
"""

import logging
from dataclasses import replace
from datetime import datetime
from typing import Any

from .models import VideoData
from .utils import extract_game_links, extract_steam_app_id


class VideoProcessor:
    """Handles video processing pipeline and game link extraction"""

    def __init__(self, data_manager: Any, youtube_extractor: Any, config_manager: Any, game_inference: Any, other_games_data: dict) -> None:
        self.data_manager = data_manager
        self.youtube_extractor = youtube_extractor
        self.config_manager = config_manager
        self.game_inference = game_inference
        self.other_games_data = other_games_data

    def process_videos(self, videos_data: dict, channel_url: str, max_new_videos: int | None = None,
                      fetch_newest_first: bool = False, cutoff_date: str | None = None) -> int:
        """Process YouTube videos only"""
        logging.info(f"Processing videos from channel: {channel_url}")

        if not max_new_videos:
            max_new_videos = 50

        # Parse cutoff date if provided
        cutoff_datetime = None
        if cutoff_date:
            try:
                cutoff_datetime = datetime.strptime(cutoff_date, '%Y-%m-%d')
                logging.info(f"Using cutoff date: {cutoff_date}")
            except ValueError:
                logging.error(f"Invalid cutoff date format: {cutoff_date}. Use YYYY-MM-DD format.")
                return 0

        known_video_ids = set(videos_data['videos'].keys())
        new_videos_processed = 0
        batch_size = min(max_new_videos * 2, 50)  # Fetch more IDs to account for known videos
        videos_fetched_total = 0
        consecutive_known_batches = 0
        cutoff_reached = False

        # Smart starting position: if we have videos and not fetching newest first, start from a reasonable offset
        if fetch_newest_first:
            smart_start_offset = 0  # Start from beginning (newest videos)
            logging.info("Fetching newest videos first (cron mode)")
        else:
            smart_start_offset = max(0, len(known_video_ids) - 10) if known_video_ids else 0
            if smart_start_offset > 0:
                logging.info(f"Smart start: skipping to position {smart_start_offset + 1} (have {len(known_video_ids)} videos)")

        videos_fetched_total = smart_start_offset

        while new_videos_processed < max_new_videos and not cutoff_reached:
            # Calculate how many videos to skip (based on total fetched so far)
            skip_count = videos_fetched_total

            logging.info(f"Fetching {batch_size} video IDs starting from position {skip_count + 1}")

            # Fetch videos with offset (lightweight - just IDs and basic info)
            videos = self.get_channel_videos_lightweight(channel_url, skip_count, batch_size)

            if not videos:
                logging.info("No more videos available from channel")
                break

            videos_fetched_total += len(videos)
            batch_new_count = 0
            new_videos_in_batch = []

            # First pass: identify new videos without fetching full metadata
            for video in videos:
                video_id = video['video_id']

                # Check if we've hit the max new videos limit
                if new_videos_processed >= max_new_videos:
                    break

                # Skip if we already have this video
                if video_id in known_video_ids:
                    continue

                new_videos_in_batch.append(video)
                if len(new_videos_in_batch) >= max_new_videos - new_videos_processed:
                    break

            if not new_videos_in_batch:
                consecutive_known_batches += 1
                logging.info("No new videos in this batch, continuing deeper into channel history")
                # If we've had 3 consecutive batches with no new videos, we're likely caught up
                if consecutive_known_batches >= 3:
                    logging.info("Hit 3 consecutive batches with no new videos, stopping search")
                    break
                continue

            # Second pass: fetch full metadata only for new videos
            logging.info(f"Found {len(new_videos_in_batch)} new videos, fetching full metadata")
            batch_new_count = 0
            for video in new_videos_in_batch:
                video_id = video['video_id']

                if new_videos_processed >= max_new_videos:
                    break

                # Get full video metadata
                try:
                    full_video, is_expected_skip = self.get_full_video_metadata(video_id)
                    if full_video:
                        video_date = full_video.get('published_at', '')[:10] if full_video.get('published_at') else 'Unknown'

                        # Check cutoff date if provided
                        if cutoff_datetime and video_date != 'Unknown':
                            try:
                                video_datetime = datetime.strptime(video_date, '%Y-%m-%d')
                                if video_datetime < cutoff_datetime:
                                    logging.info(f"Reached cutoff date. Stopping processing at video: {full_video.get('title', 'Unknown Title')} ({video_date})")
                                    cutoff_reached = True
                                    break
                            except ValueError:
                                logging.warning(f"Could not parse video date: {video_date}")

                        logging.info(f"Processing: {full_video.get('title', 'Unknown Title')} ({video_date})")
                        # Convert dict to VideoData object for processing
                        video_obj = VideoData(
                            video_id=full_video.get('video_id', ''),
                            title=full_video.get('title', ''),
                            description=full_video.get('description', ''),
                            published_at=full_video.get('published_at', ''),
                            thumbnail=full_video.get('thumbnail', ''),
                            steam_app_id=None,
                            itch_url=None,
                            itch_is_demo=False,
                            crazygames_url=None,
                            youtube_detected_game=None,
                            youtube_detected_matched=False,
                            inferred_game=False
                        )
                        # Process video with game link extraction
                        video_data = self.process_video_game_links(video_obj)

                        videos_data['videos'][video_id] = video_data
                        known_video_ids.add(video_id)  # Add to our tracking set
                        new_videos_processed += 1
                        batch_new_count += 1
                    else:
                        # Only warn if it's not an expected skip (members-only, private, etc.)
                        if not is_expected_skip:
                            logging.warning(f"Failed to get full metadata for {video_id}")
                except Exception as e:
                    logging.error(f"Error processing video {video_id}: {e}")
                    continue

            logging.info(f"Processed {batch_new_count} new videos in this batch")

            # Treat batches with no successfully processed videos the same as empty batches
            if batch_new_count == 0:
                consecutive_known_batches += 1
                logging.info("No videos successfully processed in this batch, treating as empty batch")
                if consecutive_known_batches >= 3:
                    logging.info("Hit 3 consecutive unproductive batches, stopping search")
                    break
            else:
                consecutive_known_batches = 0

        logging.info(f"Video processing complete. Processed {new_videos_processed} new videos.")
        return new_videos_processed

    def process_video_game_links(self, video: VideoData) -> VideoData:
        """Extract and process game links from a video"""
        # Extract game links from description
        game_links = extract_game_links(video.description)

        # Store video data with game links if found
        video_data = VideoData(
            video_id=video.video_id,
            title=video.title,
            description=video.description,
            published_at=video.published_at,
            thumbnail=video.thumbnail,
            steam_app_id=None,
            itch_url=None,
            itch_is_demo=False,  # Flag to indicate itch.io is demo/test version
            crazygames_url=None,
            youtube_detected_game=None,
            youtube_detected_matched=False,
            inferred_game=False
        )

        # Priority: Steam > Itch.io > CrazyGames, but store all found links
        if game_links.steam:
            app_id = extract_steam_app_id(game_links.steam)
            video_data = replace(video_data, steam_app_id=app_id)
            # Store other platforms as secondary
            if game_links.itch:
                video_data = replace(video_data, itch_url=game_links.itch, itch_is_demo=True)
            if game_links.crazygames:
                video_data = replace(video_data, crazygames_url=game_links.crazygames)
            logging.info(f"  Found Steam link: {game_links.steam}" +
                        (f", Itch.io: {game_links.itch}" if game_links.itch else "") +
                        (f", CrazyGames: {game_links.crazygames}" if game_links.crazygames else ""))
        elif game_links.itch:
            video_data = replace(video_data, itch_url=game_links.itch)
            if game_links.crazygames:
                video_data = replace(video_data, crazygames_url=game_links.crazygames)
            logging.info(f"  Found Itch.io link: {game_links.itch}" +
                        (f", CrazyGames: {game_links.crazygames}" if game_links.crazygames else ""))

        elif game_links.crazygames:
            video_data = replace(video_data, crazygames_url=game_links.crazygames)
            logging.info(f"  Found CrazyGames link: {game_links.crazygames}")

        else:
            logging.info("  No game links found, trying YouTube detection...")

            # Last resort: try YouTube's detected game
            detected_game = self.youtube_extractor.extract_youtube_detected_game(video.video_id)
            if detected_game:
                logging.info(f"  YouTube detected game: {detected_game}")
                video_data = replace(video_data, youtube_detected_game=detected_game)

                # Check if this game should skip Steam matching
                skip_games = self.config_manager.get_skip_steam_matching_games()
                should_skip = any(skip_game.lower() in detected_game.lower() for skip_game in skip_games)

                # Try to find this game on Steam (unless matching is disabled)
                if not should_skip:
                    steam_match = self.game_inference.find_steam_match(detected_game, confidence_threshold=0.6)
                    if steam_match:
                        video_data = replace(video_data, steam_app_id=steam_match['app_id'], youtube_detected_matched=True)
                        logging.info(f"  Matched to Steam: {steam_match['name']} (App ID: {steam_match['app_id']}, confidence: {steam_match['confidence']:.2f})")
                    else:
                        logging.info("  No confident Steam matches found for YouTube detected game")
                else:
                    logging.info(f"  Steam matching skipped for '{detected_game}' (in config skip list)")
            else:
                logging.info("  No YouTube detected game found")

        return video_data

    def reprocess_video_descriptions(self, videos_data: dict) -> int:
        """Reprocess existing video descriptions to extract game links with current logic"""
        logging.info("Reprocessing existing video descriptions")

        videos_processed = 0
        updated_count = 0

        for video_id, video_data in videos_data['videos'].items():
            video_date = video_data.published_at[:10] if video_data.published_at else None
            date_str = video_date if video_date else 'No date'
            logging.info(f"Reprocessing: {video_data.title} ({date_str})")

            # Store original data for comparison
            original_steam_id = video_data.steam_app_id
            original_itch_url = video_data.itch_url
            original_itch_is_demo = video_data.itch_is_demo
            original_crazygames_url = video_data.crazygames_url

            # Reprocess with current logic
            updated_video_data = self.process_video_game_links(video_data)

            # Check if anything changed
            if (updated_video_data.steam_app_id != original_steam_id or
                updated_video_data.itch_url != original_itch_url or
                updated_video_data.itch_is_demo != original_itch_is_demo or
                updated_video_data.crazygames_url != original_crazygames_url):
                updated_count += 1
                logging.info("  Updated game links for video")

            # Update the video data
            videos_data['videos'][video_id] = updated_video_data
            videos_processed += 1

        logging.info(f"Reprocessing complete. Processed {videos_processed} videos, updated {updated_count} videos.")
        return updated_count

    def get_channel_videos_lightweight(self, channel_url: str, skip_count: int, batch_size: int) -> list[dict[Any, Any]]:
        """Fetch lightweight video info (just IDs and titles) from YouTube channel"""
        result = self.youtube_extractor.get_channel_videos_lightweight(channel_url, skip_count, batch_size)
        return result if isinstance(result, list) else []

    def get_full_video_metadata(self, video_id: str) -> tuple[dict[Any, Any] | None, bool]:
        """Fetch full metadata for a specific video"""
        result = self.youtube_extractor.get_full_video_metadata(video_id)
        return result if isinstance(result, tuple) else (None, False)
