-- Games Database Schema
-- Single source of truth for database structure

CREATE TABLE games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_key TEXT UNIQUE NOT NULL,
    steam_app_id TEXT,
    name TEXT NOT NULL,
    platform TEXT NOT NULL,
    coming_soon BOOLEAN DEFAULT 0,
    is_early_access BOOLEAN DEFAULT 0,
    is_demo BOOLEAN DEFAULT 0,
    is_free BOOLEAN DEFAULT 0,
    price TEXT,
    price_final REAL,
    positive_review_percentage INTEGER,
    review_count INTEGER,
    review_summary TEXT,
    review_summary_priority INTEGER,
    recent_review_percentage INTEGER,
    recent_review_count INTEGER,
    recent_review_summary TEXT,
    insufficient_reviews BOOLEAN DEFAULT 0,
    release_date TEXT,
    planned_release_date TEXT,
    header_image TEXT,
    steam_url TEXT,
    itch_url TEXT,
    crazygames_url TEXT,
    last_updated TEXT,
    video_count INTEGER DEFAULT 0,
    latest_video_date TEXT,
    unique_channels TEXT,  -- JSON array
    genres TEXT,           -- JSON array
    tags TEXT,             -- JSON array
    developers TEXT,       -- JSON array
    publishers TEXT,       -- JSON array
    demo_steam_app_id TEXT,
    demo_steam_url TEXT,
    demo_itch_url TEXT
);

CREATE TABLE game_videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER REFERENCES games(id),
    video_id TEXT,
    video_title TEXT,
    video_date TEXT,
    channel_name TEXT,
    published_at TEXT
);

-- Indexes for fast filtering
CREATE INDEX idx_platform ON games(platform);
CREATE INDEX idx_release_status ON games(coming_soon, is_early_access);
CREATE INDEX idx_rating ON games(positive_review_percentage);
CREATE INDEX idx_review_priority ON games(review_summary_priority);
CREATE INDEX idx_game_videos ON game_videos(game_id);
CREATE INDEX idx_channel_videos ON game_videos(channel_name);