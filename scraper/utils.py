"""
Utility functions for the YouTube Steam scraper
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List

from models import GameLinks


def extract_game_links(description: str) -> GameLinks:
    """Extract game store links from video description"""
    links = GameLinks()

    # Steam patterns
    steam_patterns = [
        r'https?://store\.steampowered\.com/app/(\d+)',
        r'https?://steam\.com/app/(\d+)',
        r'https?://s\.team/a/(\d+)',
        r'https?://store\.steampowered\.com/news/app/(\d+)'
    ]

    for pattern in steam_patterns:
        match = re.search(pattern, description)
        if match:
            app_id = match.group(1)
            links.steam = f"https://store.steampowered.com/app/{app_id}"
            break

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

    for pattern in valid_patterns:
        if re.search(pattern, date_str, re.IGNORECASE):
            return True

    return False


def calculate_name_similarity(name1: str, name2: str) -> float:
    """Calculate similarity between two game names using word overlap"""
    words1 = set(name1.lower().split())
    words2 = set(name2.lower().split())
    overlap = len(words1 & words2)
    return overlap / max(len(words1), len(words2))


def extract_potential_game_names(title: str) -> List[str]:
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


def load_json(filepath: str, default: Dict) -> Dict:
    """Load JSON file or return default"""
    if os.path.exists(filepath):
        with open(filepath) as f:
            return json.load(f)
    return default


def save_data(data_dict: Dict, file_path: str):
    """Save data to JSON file with timestamp"""
    data_dict['last_updated'] = datetime.now().isoformat()
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as f:
        json.dump(data_dict, f, indent=2)


def clean_tag_text(tag_text: str) -> str:
    """Clean up tag text - remove trailing numbers like 'Casual1,157'"""
    return re.sub(r'[\d,]+$', '', tag_text).strip()


def extract_steam_app_id(steam_url: str) -> str:
    """Extract Steam app ID from URL"""
    match = re.search(r'/app/(\d+)', steam_url)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract app ID from URL: {steam_url}")
