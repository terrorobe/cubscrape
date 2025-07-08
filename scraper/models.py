"""
Data models for the YouTube Steam scraper
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class VideoData:
    """Represents a YouTube video with game data"""
    video_id: str
    title: str
    description: str
    published_at: str
    thumbnail: str = ""
    steam_app_id: Optional[str] = None
    itch_url: Optional[str] = None
    itch_is_demo: bool = False
    crazygames_url: Optional[str] = None
    youtube_detected_game: Optional[str] = None
    youtube_detected_matched: bool = False
    inferred_game: bool = False
    inference_reason: Optional[str] = None
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SteamGameData:
    """Represents Steam game metadata"""
    steam_app_id: str
    steam_url: str
    name: str
    is_free: bool = False
    release_date: str = ""
    coming_soon: bool = False
    genres: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    developers: List[str] = field(default_factory=list)
    publishers: List[str] = field(default_factory=list)
    price: Optional[str] = None
    header_image: str = ""
    tags: List[str] = field(default_factory=list)
    has_demo: bool = False
    demo_app_id: Optional[str] = None
    is_demo: bool = False
    full_game_app_id: Optional[str] = None
    is_early_access: bool = False
    positive_review_percentage: Optional[int] = None
    review_count: Optional[int] = None
    review_summary: Optional[str] = None
    recent_review_percentage: Optional[int] = None
    recent_review_count: Optional[int] = None
    recent_review_summary: Optional[str] = None
    insufficient_reviews: bool = False
    planned_release_date: Optional[str] = None
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class OtherGameData:
    """Represents non-Steam game metadata (Itch.io, CrazyGames, etc.)"""
    platform: str  # 'itch', 'crazygames', etc.
    url: str
    name: str
    is_free: bool = True
    header_image: str = ""
    tags: List[str] = field(default_factory=list)
    positive_review_percentage: Optional[int] = None
    review_count: Optional[int] = None
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class GameLinks:
    """Represents extracted game store links"""
    steam: Optional[str] = None
    itch: Optional[str] = None
    crazygames: Optional[str] = None


@dataclass
class SteamSearchResult:
    """Represents a Steam search result match"""
    app_id: str
    name: str
    confidence: float
