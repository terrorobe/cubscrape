"""
Game Unification Logic

Handles merging demo and full game pairs into unified entries,
and processing all game data for database generation.
"""

import json
import logging

from utils import generate_review_summary


def _resolve_stub_entries(steam_data):
    """Resolve stub entries by replacing them with their resolved targets"""
    resolved_data = {}

    for app_id, game_data in steam_data.items():
        # Check if this is a stub with a resolution
        if game_data.get('is_stub') and game_data.get('resolved_to'):
            resolved_app_id = game_data['resolved_to']
            resolved_game = steam_data.get(resolved_app_id)

            if resolved_game:
                logging.info(f"Resolving stub {app_id} to {resolved_app_id}: {resolved_game.get('name')}")
                resolved_data[app_id] = resolved_game
            else:
                logging.warning(f"Stub {app_id} points to missing game {resolved_app_id}")
                resolved_data[app_id] = game_data
        else:
            # Not a stub or unresolved stub - use as-is
            resolved_data[app_id] = game_data

    return resolved_data


def _create_fallback_game(game_key, game_data, missing_ref_id=None):
    """Create a fallback game entry when relationships are missing"""
    if missing_ref_id:
        logging.warning(f"Game {game_key} references missing game {missing_ref_id}")

    return {
        'game_key': game_key,
        'platform': 'steam',
        'name': game_data.get('name', 'Unknown Game'),
        'videos': [],
        'video_count': 0,
        **game_data
    }

def _determine_active_data_and_demo_info(demo_data, full_game_data, demo_id, _full_game_id):
    """Determine which data to use as active and what demo info to include

    Args:
        demo_data: Steam data for the demo
        full_game_data: Steam data for the full game
        demo_id: Steam app ID for the demo
        _full_game_id: Steam app ID for the full game
    """
    is_full_game_released = not full_game_data.get('coming_soon', False)

    if is_full_game_released:
        # Released full game: use full game data, reference demo
        active_data = full_game_data
        demo_info = {}

        # Add Steam demo info if available (takes precedence)
        if demo_id:
            demo_info['demo_steam_app_id'] = demo_id
            demo_info['demo_steam_url'] = f"https://store.steampowered.com/app/{demo_id}"

        # Always add Itch URL if present (as secondary demo option)
        if full_game_data.get('itch_url'):
            demo_info['itch_url'] = full_game_data['itch_url']
    else:
        # Unreleased full game: use demo data but keep full game's release status
        active_data = {
            **demo_data,  # Demo data (reviews, image, etc.)
            # Override with full game's release status
            'coming_soon': full_game_data.get('coming_soon', False),
            'planned_release_date': full_game_data.get('planned_release_date'),
            'release_date': full_game_data.get('release_date', 'Coming soon'),
            # Keep demo's app ID and URL as main links since that's what's playable
            'steam_app_id': demo_id,
            'steam_url': f"https://store.steampowered.com/app/{demo_id}",
        }
        demo_info = {}

    return active_data, demo_info

def _create_unified_game_entry(primary_key, primary_name, demo_id, full_game_id, active_data, demo_info):
    """Create a unified game entry with consistent structure"""
    return {
        'platform': 'steam',
        'videos': [],
        'video_count': 0,
        # Use active data for display
        **active_data,
        # Store demo info for links
        **demo_info,
        # Always keep the primary name and key (override any from active_data)
        'name': primary_name,
        'game_key': primary_key,
        # Store both IDs for video merging
        '_demo_app_id': demo_id,
        '_full_game_app_id': full_game_id
    }

def _merge_itch_data_into_steam_game(steam_game, itch_data):
    """Merge Itch.io data into Steam game when Steam data is incomplete or missing"""

    # Use Itch review data if Steam has no reviews
    if not steam_game.get('review_count') and itch_data.get('review_count'):
        itch_percentage = itch_data.get('positive_review_percentage')
        itch_count = itch_data.get('review_count')

        # Only set percentage if there are enough reviews for a meaningful score
        if itch_count >= 10:
            steam_game['positive_review_percentage'] = itch_percentage
        steam_game['review_count'] = itch_count

        # Generate proper review summary using Steam's thresholds (clean, no asterisk)
        steam_game['review_summary'] = generate_review_summary(itch_percentage, itch_count)
        steam_game['is_inferred_summary'] = True  # Flag to indicate this is inferred from non-Steam data

        # Store supplementary review info for tooltip
        steam_game['review_tooltip'] = f"Based on {itch_count} Itch.io reviews"

    # Handle release date logic carefully
    steam_release = steam_game.get('release_date', '')
    steam_planned = steam_game.get('planned_release_date', '')
    itch_release = itch_data.get('release_date', '')

    # If Steam is "coming soon" but Itch is released, this means Itch is like a demo
    if (steam_release in ['To be announced', 'Coming soon', ''] and
        steam_planned in ['To be announced', 'Coming soon', ''] and
        itch_release):
        # Keep Steam as "coming soon" but mark that a demo exists
        steam_game['is_demo'] = False  # This is the full game, but unreleased
        steam_game['has_demo'] = True  # The Itch version acts as a demo
        # Don't change coming_soon - keep it as coming soon for Steam
    elif steam_release in ['To be announced', 'Coming soon', ''] and itch_release:
        # If no planned date, use Itch date as the release date
        steam_game['release_date'] = itch_release
        steam_game['coming_soon'] = False

    # Use Itch tags to supplement Steam tags (merge unique tags)
    if itch_data.get('tags'):
        steam_tags = set(steam_game.get('tags', []))
        itch_tags = set(itch_data.get('tags', []))
        merged_tags = list(steam_tags | itch_tags)  # Union of both tag sets
        steam_game['tags'] = merged_tags[:20]  # Limit to 20 tags

    # Use Itch pricing info if available
    if itch_data.get('is_free') and not steam_game.get('price'):
        steam_game['is_free'] = True
        steam_game['price'] = 'Free'

    logging.info(f"Merged Itch.io data into Steam game: {steam_game.get('name')}")


def create_unified_steam_games(steam_data):
    """Create unified Steam games by merging demo and full game pairs"""
    unified_games = {}
    processed_games = set()

    logging.info(f"Creating unified games from {len(steam_data)} Steam entries")

    # Resolve stub entries before processing
    resolved_steam_data = _resolve_stub_entries(steam_data)

    for game_key, game_data in resolved_steam_data.items():
        if game_key in processed_games:
            continue

        # Check if this is a demo with a full game
        if game_data.get('is_demo') and game_data.get('full_game_app_id'):
            full_game_id = game_data['full_game_app_id']
            full_game_data = resolved_steam_data.get(full_game_id, {})

            if not full_game_data:
                # Full game data not found, treat as regular demo
                unified_games[game_key] = _create_fallback_game(game_key, game_data, full_game_id)
                processed_games.add(game_key)
                continue

            # Determine what data to use based on release status
            active_data, demo_info = _determine_active_data_and_demo_info(
                game_data, full_game_data, game_key, full_game_id
            )

            # Create unified entry using full game ID as key
            primary_name = full_game_data.get('name', game_data.get('name', 'Unknown Game'))
            unified_games[full_game_id] = _create_unified_game_entry(
                full_game_id, primary_name, game_key, full_game_id, active_data, demo_info
            )

            processed_games.add(game_key)
            processed_games.add(full_game_id)

        # Check if this is a full game with a demo
        elif game_data.get('has_demo') and game_data.get('demo_app_id'):
            demo_id = game_data['demo_app_id']
            demo_data = steam_data.get(demo_id, {})

            if not demo_data:
                # Demo data not found, treat as regular full game
                unified_games[game_key] = _create_fallback_game(game_key, game_data, demo_id)
                processed_games.add(game_key)
                continue

            # Determine what data to use based on release status
            active_data, demo_info = _determine_active_data_and_demo_info(
                demo_data, game_data, demo_id, game_key
            )

            # Create unified entry using full game ID as key
            primary_name = game_data.get('name', 'Unknown Game')
            unified_games[game_key] = _create_unified_game_entry(
                game_key, primary_name, demo_id, game_key, active_data, demo_info
            )

            processed_games.add(game_key)
            processed_games.add(demo_id)

        # Regular game (no demo relationship)
        else:
            unified_games[game_key] = _create_fallback_game(game_key, game_data)
            processed_games.add(game_key)

    unified_count = len(unified_games)
    demo_pairs = sum(1 for g in unified_games.values() if g.get('_demo_app_id'))
    logging.info(f"Created {unified_count} unified games ({demo_pairs} demo/full pairs)")

    return unified_games


def process_and_unify_games(steam_data, other_games, all_videos):
    """Process games using existing logic adapted from JavaScript processGames()"""
    unified_games = {}

    # First, create unified demo/full game entries
    unified_games = create_unified_steam_games(steam_data)

    # Add other platform games (itch, crazygames)
    # But skip Itch games that have been absorbed into Steam games
    other_games_added = 0
    itch_absorbed = 0
    itch_to_steam_mapping = {}  # Map Itch URLs to Steam game keys for video processing

    for game_key, game_data in other_games.items():
        if game_key not in unified_games:
            # Check if this is an Itch game that's been absorbed into a Steam game
            if game_data.get('platform') == 'itch' and game_data.get('steam_url'):
                # Check if any Steam game has this Itch URL
                absorbed = False
                for steam_game_key, steam_game in unified_games.items():
                    if steam_game.get('platform') == 'steam' and steam_game.get('itch_url') == game_key:
                        absorbed = True
                        itch_absorbed += 1

                        # Map Itch URL to Steam game key for video processing
                        itch_to_steam_mapping[game_key] = steam_game_key

                        # Merge Itch data into Steam game when Steam data is incomplete
                        _merge_itch_data_into_steam_game(steam_game, game_data)
                        break

                if absorbed:
                    continue  # Skip this Itch game as it's part of a Steam game

            # Mark Itch.io and CrazyGames as free
            if game_data.get('platform') in ['itch', 'crazygames']:
                game_data['is_free'] = True

            unified_games[game_key] = {
                'game_key': game_key,
                'platform': game_data.get('platform', 'other'),
                'name': game_data.get('name', 'Unknown Game'),
                'videos': [],
                'video_count': 0,
                **game_data  # Include all game data
            }
            other_games_added += 1

    logging.info(f"Added {other_games_added} other platform games to unified dataset")
    if itch_absorbed > 0:
        logging.info(f"Skipped {itch_absorbed} Itch games that are part of Steam games")

    # Then, process each video and add to existing game entries
    for video_id, video in all_videos.items():
        # Skip videos without game references
        if not (video.get('steam_app_id') or video.get('itch_url') or video.get('crazygames_url')):
            continue

        # Determine game key and platform
        if video.get('steam_app_id'):
            steam_app_id = video['steam_app_id']

            # Find the unified game entry for this Steam app ID
            target_game_key = None
            for game_key, game_data in unified_games.items():
                if (game_data.get('platform') == 'steam' and
                    (game_key == steam_app_id or  # Direct match
                     game_data.get('_demo_app_id') == steam_app_id or  # Demo video
                     game_data.get('_full_game_app_id') == steam_app_id)):  # Full game video
                        target_game_key = game_key
                        break

            if not target_game_key:
                # This shouldn't happen with our unified creation, but handle it
                continue

            game_key = target_game_key

        elif video.get('itch_url'):
            itch_url = video['itch_url']
            # Check if this Itch URL maps to a Steam game
            game_key = itch_to_steam_mapping.get(itch_url, itch_url)
        elif video.get('crazygames_url'):
            game_key = video['crazygames_url']
        else:
            continue

        # Game should already exist from unified creation
        if game_key not in unified_games:
            continue

        # Add video to game
        unified_games[game_key]['videos'].append({
            'video_id': video_id,
            'video_title': video.get('title', ''),
            'video_date': video.get('published_at', ''),
            'video_url': f"https://www.youtube.com/watch?v={video_id}",
            'channel_name': video.get('channel_name', ''),
            'published_at': video.get('published_at', '')
        })

    # Update video counts
    for game in unified_games.values():
        game['video_count'] = len(game['videos'])

    logging.info(f"Processed {len(unified_games)} games from {len(all_videos)} videos")
    return unified_games


def load_all_unified_games(project_root):
    """Load and process all game data from JSON files"""

    # Load JSON files
    try:
        with (project_root / 'data' / 'steam_games.json').open() as f:
            steam_data = json.load(f).get('games', {})
    except FileNotFoundError:
        logging.warning("steam_games.json not found, using empty data")
        steam_data = {}

    try:
        with (project_root / 'data' / 'other_games.json').open() as f:
            other_games = json.load(f).get('games', {})
    except FileNotFoundError:
        logging.warning("other_games.json not found, using empty data")
        other_games = {}

    # Load config to get channel names
    config_file = project_root / 'config.json'
    try:
        with config_file.open() as f:
            config = json.load(f)
            channels_config = config.get('channels', {})
    except Exception as e:
        logging.warning(f"Failed to load config.json: {e}")
        channels_config = {}

    # Load all video files
    video_files = list(project_root.glob('data/videos-*.json'))
    all_videos = {}

    for file in video_files:
        try:
            # Extract channel ID from filename (e.g., videos-aliensrock.json -> aliensrock)
            channel_id = file.stem.replace('videos-', '')
            channel_name = channels_config.get(channel_id, {}).get('name', channel_id)

            with file.open() as f:
                channel_data = json.load(f)
                # Add channel info to each video
                for video in channel_data.get('videos', {}).values():
                    video['channel_id'] = channel_id
                    video['channel_name'] = channel_name
                all_videos.update(channel_data.get('videos', {}))
        except Exception as e:
            logging.warning(f"Failed to load {file}: {e}")

    # Process and unify games
    return process_and_unify_games(steam_data, other_games, all_videos)
