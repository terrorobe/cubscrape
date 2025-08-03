"""
Data models for the YouTube Steam scraper
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class VideoGameReference(BaseModel):
    """Represents a single game reference in a video"""
    platform: Literal['steam', 'itch', 'crazygames']
    platform_id: str  # app_id for Steam, URL for others
    inferred: bool = False  # Whether this specific game reference was inferred
    youtube_detected_matched: bool = False  # Whether this reference came from YouTube matching

    @field_validator('platform_id')
    @classmethod
    def validate_platform_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('platform_id cannot be empty')
        return v.strip()


class VideoData(BaseModel):
    """Represents a YouTube video with game data"""
    video_id: str
    title: str
    description: str
    published_at: str
    thumbnail: str = ""
    youtube_detected_game: str | None = None
    inference_reason: str | None = None
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())
    game_references: list[VideoGameReference] = Field(default_factory=list)

    @field_validator('video_id')
    @classmethod
    def validate_video_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('video_id cannot be empty')
        return v.strip()


class SteamGameData(BaseModel):
    """Represents Steam game metadata"""
    steam_app_id: str
    steam_url: str
    name: str
    is_free: bool = False
    release_date: str = ""
    coming_soon: bool = False
    genres: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    developers: list[str] = Field(default_factory=list)
    publishers: list[str] = Field(default_factory=list)
    price_eur: int | str | None = None  # Price in cents (int) or old format (str)
    price_usd: int | str | None = None  # Price in cents (int) or old format (str)
    header_image: str = ""
    tags: list[str] = Field(default_factory=list)
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
    discount_percent: int | None = None  # 0-99 discount percentage (only set when > 0)
    original_price_eur: int | str | None = None  # Original price in cents (int) or old format (str)
    original_price_usd: int | str | None = None  # Original price in cents (int) or old format (str)
    is_on_sale: bool = False  # True if discount_percent > 0
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())

    # Removal detection fields
    removal_detected: str | None = None  # Date when removal was detected
    removal_pending: bool = False  # True if game needs removal processing

    # Full refresh flag for bidirectional change detection
    needs_full_refresh: bool = False  # True if game needs full refresh due to pricing changes

    is_stub: bool = False  # True if this is a stub entry for a failed fetch
    stub_reason: str | None = None  # Reason for stub creation (e.g., "HTTP 400", "Not found")
    resolved_to: str | None = None  # Steam app ID this stub should resolve to

    @field_validator('steam_app_id')
    @classmethod
    def validate_steam_app_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('steam_app_id cannot be empty')
        return v.strip()

    @field_validator('resolved_to')
    @classmethod
    def validate_resolved_to(cls, v: str | None) -> str | None:
        if v is not None and (not v or not v.strip()):
            raise ValueError('resolved_to cannot be empty string if provided')
        return v.strip() if v else None


class OtherGameData(BaseModel):
    """Represents non-Steam game metadata (Itch.io, CrazyGames, etc.)"""
    platform: str  # 'itch', 'crazygames', etc.
    url: str
    name: str
    is_free: bool = True
    release_date: str = ""
    header_image: str = ""
    tags: list[str] = Field(default_factory=list)
    positive_review_percentage: int | None = None
    review_count: int | None = None
    steam_url: str = ""  # Steam link if found and name matches
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())
    is_stub: bool = False  # True if this is a stub entry for a failed fetch
    stub_reason: str | None = None  # Reason for stub creation (e.g., "HTTP 400", "Not found")
    resolved_to: str | None = None  # URL this stub should resolve to

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('url cannot be empty')
        return v.strip()

    @field_validator('resolved_to')
    @classmethod
    def validate_resolved_to(cls, v: str | None) -> str | None:
        if v is not None and (not v or not v.strip()):
            raise ValueError('resolved_to cannot be empty string if provided')
        return v.strip() if v else None


class GameLinks(BaseModel):
    """Represents extracted game store links"""
    steam: str | None = None
    itch: str | None = None
    crazygames: str | None = None


class SteamSearchResult(BaseModel):
    """Represents a Steam search result match"""
    app_id: str
    name: str
    confidence: float

    @field_validator('app_id')
    @classmethod
    def validate_app_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('app_id cannot be empty')
        return v.strip()

    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError('confidence must be between 0.0 and 1.0')
        return v
