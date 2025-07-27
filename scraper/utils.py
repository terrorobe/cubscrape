"""
Utility functions for the YouTube Steam scraper
"""

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from .models import GameLinks, VideoGameReference


def extract_steam_app_id(url: str) -> str | None:
    """Extract Steam app ID from a Steam URL"""
    steam_patterns = [
        r'https?://store\.steampowered\.com/app/(\d+)',
        r'https?://steam\.com/app/(\d+)',
        r'https?://s\.team/a/(\d+)',
        r'https?://store\.steampowered\.com/news/app/(\d+)'
    ]

    for pattern in steam_patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def extract_all_steam_app_ids(text: str) -> list[str]:
    """Extract ALL Steam app IDs from text"""
    steam_patterns = [
        r'https?://store\.steampowered\.com/app/(\d+)',
        r'https?://steam\.com/app/(\d+)',
        r'https?://s\.team/a/(\d+)',
        r'https?://store\.steampowered\.com/news/app/(\d+)'
    ]

    app_ids = []
    seen = set()

    for pattern in steam_patterns:
        for match in re.finditer(pattern, text):
            app_id = match.group(1)
            if app_id not in seen:
                seen.add(app_id)
                app_ids.append(app_id)

    return app_ids


def extract_all_itch_urls(text: str) -> list[str]:
    """Extract ALL Itch.io URLs from text"""
    itch_patterns = [
        r'https?://([^.]+)\.itch\.io/([^/\s]+)',
        r'https?://itch\.io/games/([^/\s]+)'
    ]

    urls = []
    seen = set()

    for pattern in itch_patterns:
        for match in re.finditer(pattern, text):
            url = match.group(0)
            if url not in seen:
                seen.add(url)
                urls.append(url)

    return urls


def extract_all_crazygames_urls(text: str) -> list[str]:
    """Extract ALL CrazyGames URLs from text"""
    crazygames_patterns = [
        r'https?://www\.crazygames\.com/game/([^/\s]+)',
        r'https?://crazygames\.com/game/([^/\s]+)'
    ]

    urls = []
    seen = set()

    for pattern in crazygames_patterns:
        for match in re.finditer(pattern, text):
            url = match.group(0)
            if url not in seen:
                seen.add(url)
                urls.append(url)

    return urls


MAX_REFERENCES_PER_VIDEO = 100  # Configurable limit


def extract_all_game_links(description: str) -> list[VideoGameReference]:
    """Extract ALL game store links from video description"""
    references = []

    # Extract all Steam app IDs (Steam takes precedence)
    steam_ids = extract_all_steam_app_ids(description)
    references.extend([
        VideoGameReference(platform='steam', platform_id=app_id)
        for app_id in steam_ids
    ])

    # Extract all Itch.io URLs
    itch_urls = extract_all_itch_urls(description)
    references.extend([
        VideoGameReference(platform='itch', platform_id=itch_url)
        for itch_url in itch_urls
    ])

    # Extract all CrazyGames URLs
    crazygames_urls = extract_all_crazygames_urls(description)
    references.extend([
        VideoGameReference(platform='crazygames', platform_id=cg_url)
        for cg_url in crazygames_urls
    ])

    # Apply rate limiting
    if len(references) > MAX_REFERENCES_PER_VIDEO:
        # Use a logger if available, otherwise just truncate silently
        references = references[:MAX_REFERENCES_PER_VIDEO]

    return references


def extract_game_links(description: str) -> GameLinks:
    """Extract game store links from video description"""
    links = GameLinks()

    # Extract Steam link
    app_id = extract_steam_app_id(description)
    if app_id:
        links.steam = f"https://store.steampowered.com/app/{app_id}"

    # Itch.io patterns
    itch_patterns = [
        r'https?://([^.]+)\.itch\.io/([^/\s]+)',
        r'https?://itch\.io/games/([^/\s]+)'
    ]

    for pattern in itch_patterns:
        match = re.search(pattern, description)
        if match:
            links.itch = match.group(0)
            break

    # CrazyGames patterns
    crazygames_patterns = [
        r'https?://www\.crazygames\.com/game/([^/\s]+)',
        r'https?://crazygames\.com/game/([^/\s]+)'
    ]

    for pattern in crazygames_patterns:
        match = re.search(pattern, description)
        if match:
            links.crazygames = match.group(0)
            break

    return links


def is_valid_date_string(date_str: str) -> bool:
    """Validate that a date string looks like an actual date, not system specs"""
    date_str = date_str.lower().strip()

    # Invalid patterns (system requirements, etc.)
    invalid_patterns = [
        r'\b(at|while|during|via|per)\s+\d+',  # "at 1080", "while 60", etc.
        r'\d+p\b',                              # "1080p", "720p", etc.
        r'fps|hz|mhz|ghz',                      # Performance specs
        r'\b\d+\s*(mb|gb|tb)\b',               # Storage specs
    ]

    for pattern in invalid_patterns:
        if re.search(pattern, date_str, re.IGNORECASE):
            return False

    # Valid patterns (actual dates)
    valid_patterns = [
        r'^(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}$',
        r'^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2},?\s+\d{4}$',
        r'^(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}$',
        r'^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{4}$',
        r'^q[1-4]\s+\d{4}$',
        r'^\d{4}$',
        r'^(early|mid|late)\s+\d{4}$',
        r'^(spring|summer|fall|autumn|winter)\s+\d{4}$',
        r'^coming soon$',
        r'^tbd$',
        r'^to be announced$',
    ]

    return any(re.search(pattern, date_str, re.IGNORECASE) for pattern in valid_patterns)


def calculate_name_similarity(name1: str, name2: str) -> float:
    """Calculate similarity between two game names using word overlap"""
    words1 = set(name1.lower().split())
    words2 = set(name2.lower().split())
    overlap = len(words1 & words2)
    return overlap / max(len(words1), len(words2))


def extract_potential_game_names(title: str) -> list[str]:
    """Extract potential game names from video titles"""
    # Common patterns in gaming videos
    patterns = [
        r'\|\s*([^|]+?)\s*$',                                    # "Something | Game Name"
        r'^([^!|]+?)(?:\s+is\s+|\s+Review|\s+Gameplay|\s*\|)',  # "Game Name is Amazing!" or "Game Name | Channel"
        r'^\s*(.+?)\s+(?:Review|Gameplay|First Impression)',     # "Game Name Review"
        r'^(?:Playing|I Played|This)\s+(.+?)\s+(?:for|and|is)', # "I Played Game Name for..."
        r'^(.+?)\s+(?:Has|Will|Can|Gets)',                      # "Game Name Has Amazing Features"
    ]

    potential_names = []

    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Clean up common words and punctuation (but preserve 'the' for game titles)
            name = re.sub(r'\b(a|an|this|new|amazing|incredible|insane|crazy)\b', '', name, flags=re.IGNORECASE)
            name = re.sub(r'[!?]+$', '', name)  # Remove trailing exclamation/question marks
            name = re.sub(r'\s+', ' ', name).strip()
            if len(name) > 3 and name not in potential_names:  # Avoid very short matches and duplicates
                potential_names.append(name)

    return potential_names


def load_json(filepath: str | Path, default: dict[str, Any]) -> dict[str, Any]:
    """Load JSON file or return default"""
    path = Path(filepath)
    if path.exists():
        with path.open() as f:
            result = json.load(f)
            return result if isinstance(result, dict) else default
    return default


def save_data(data_dict: dict[str, Any], file_path: str | Path) -> None:
    """Save data to JSON file atomically"""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temporary file first
    with tempfile.NamedTemporaryFile(
        mode='w',
        dir=path.parent,
        prefix=f'.{path.name}.tmp-',
        suffix='.json',
        delete=False
    ) as tmp_file:
        json.dump(data_dict, tmp_file, indent=2, sort_keys=True)
        tmp_path = Path(tmp_file.name)

    # Atomically replace the original file
    tmp_path.replace(path)


def clean_tag_text(tag_text: str) -> str:
    """Clean up tag text - remove trailing numbers like 'Casual1,157'"""
    return re.sub(r'[\d,]+$', '', tag_text).strip()




def generate_review_summary(percentage: int | None, review_count: int) -> str | None:
    """Generate review summary using Steam's thresholds"""
    if not review_count or review_count == 0:
        return 'No user reviews'

    if review_count < 10:
        return 'Need more reviews for score'

    if not percentage:
        return None

    # Apply Steam's thresholds
    if percentage >= 95:
        if review_count >= 500:
            return 'Overwhelmingly Positive'
        elif review_count >= 50:
            return 'Very Positive'
        else:
            return 'Positive'
    elif percentage >= 80:
        if review_count >= 50:
            return 'Very Positive'
        else:
            return 'Positive'
    elif percentage >= 70:
        return 'Mostly Positive'
    elif percentage >= 40:
        return 'Mixed'
    elif percentage >= 20:
        return 'Mostly Negative'
    else:
        return 'Negative'


def load_env_file(env_file: str | Path = ".env") -> None:
    """Load environment variables from .env file if it exists"""
    env_path = Path(env_file)
    if not env_path.exists():
        return

    with env_path.open() as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Parse KEY=VALUE or KEY="VALUE"
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]

                # Only set if not already in environment
                if key not in os.environ:
                    os.environ[key] = value
