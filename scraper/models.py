"""
Data models for the YouTube Steam scraper
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class VideoData:
    """Represents a YouTube video with game data"""
    video_id: str
    title: str
    description: str
    published_at: str
    thumbnail: str = ""
    steam_app_id: str | None = None
    itch_url: str | None = None
    itch_is_demo: bool = False
    crazygames_url: str | None = None
    youtube_detected_game: str | None = None
    youtube_detected_matched: bool = False
    inferred_game: bool = False
    inference_reason: str | None = None
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
    genres: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    developers: list[str] = field(default_factory=list)
    publishers: list[str] = field(default_factory=list)
    price_eur: str | None = None
    price_usd: str | None = None
    header_image: str = ""
    tags: list[str] = field(default_factory=list)
    has_demo: bool = False
    demo_app_id: str | None = None
    is_demo: bool = False
    full_game_app_id: str | None = None
    is_early_access: bool = False
    positive_review_percentage: int | None = None
    review_count: int | None = None
    review_summary: str | None = None
    recent_review_percentage: int | None = None
    recent_review_count: int | None = None
    recent_review_summary: str | None = None
    insufficient_reviews: bool = False
    planned_release_date: str | None = None
    itch_url: str | None = None  # Itch.io URL if this Steam game is also on Itch
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    is_stub: bool = False  # True if this is a stub entry for a failed fetch
    stub_reason: str | None = None  # Reason for stub creation (e.g., "HTTP 400", "Not found")


@dataclass
class OtherGameData:
    """Represents non-Steam game metadata (Itch.io, CrazyGames, etc.)"""
    platform: str  # 'itch', 'crazygames', etc.
    url: str
    name: str
    is_free: bool = True
    release_date: str = ""
    header_image: str = ""
    tags: list[str] = field(default_factory=list)
    positive_review_percentage: int | None = None
    review_count: int | None = None
    steam_url: str = ""  # Steam link if found and name matches
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    is_stub: bool = False  # True if this is a stub entry for a failed fetch
    stub_reason: str | None = None  # Reason for stub creation (e.g., "HTTP 400", "Not found")


@dataclass
class GameLinks:
    """Represents extracted game store links"""
    steam: str | None = None
    itch: str | None = None
    crazygames: str | None = None


@dataclass
class SteamSearchResult:
    """Represents a Steam search result match"""
    app_id: str
    name: str
    confidence: float
