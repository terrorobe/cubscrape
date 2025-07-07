"""
YouTube Steam Scraper - Refactored modular version

This package provides a modular approach to scraping YouTube channels
and matching videos with Steam (and other platform) game data.
"""

from .models import VideoData, SteamGameData, OtherGameData, GameLinks, SteamSearchResult
from .utils import (
    extract_game_links,
    calculate_name_similarity,
    is_valid_date_string,
    load_json,
    save_data,
    extract_steam_app_id
)
from .steam_fetcher import SteamDataFetcher
from .itch_fetcher import ItchDataFetcher
from .crazygames_fetcher import CrazyGamesDataFetcher
from .scraper_refactored import YouTubeSteamScraperRefactored

__all__ = [
    # Models
    'VideoData',
    'SteamGameData', 
    'OtherGameData',
    'GameLinks',
    'SteamSearchResult',
    
    # Utilities
    'extract_game_links',
    'calculate_name_similarity',
    'is_valid_date_string',
    'load_json',
    'save_data',
    'extract_steam_app_id',
    
    # Fetchers
    'SteamDataFetcher',
    'ItchDataFetcher',
    'CrazyGamesDataFetcher',
    
    # Main scraper
    'YouTubeSteamScraperRefactored'
]

__version__ = '2.0.0'