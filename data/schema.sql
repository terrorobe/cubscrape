-- Games Database Schema
-- Single source of truth for database structure

-- Metadata table for app version tracking
CREATE TABLE app_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

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
    price_eur INTEGER,
    price_usd INTEGER,
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
    release_date_sortable INTEGER,  -- YYYYMMDD format for sorting
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
    review_tooltip TEXT,   -- Supplementary review info for tooltip
    is_inferred_summary BOOLEAN DEFAULT 0,  -- Whether review summary is inferred from non-Steam data
    is_absorbed BOOLEAN DEFAULT 0,  -- Whether this game is absorbed into another game
    absorbed_into TEXT,  -- game_key of parent game (if absorbed)
    discount_percent INTEGER DEFAULT 0,
    original_price_eur INTEGER,
    original_price_usd INTEGER,
    is_on_sale BOOLEAN DEFAULT 0
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
CREATE INDEX idx_release_date_sortable ON games(release_date_sortable);
CREATE INDEX idx_game_videos ON game_videos(game_id);
CREATE INDEX idx_channel_videos ON game_videos(channel_name);

-- Performance indexes for multi-filtering patterns
CREATE INDEX idx_absorbed_platform ON games(is_absorbed, platform);
CREATE INDEX idx_latest_video_date ON games(latest_video_date);
CREATE INDEX idx_video_count ON games(video_count);
CREATE INDEX idx_price_filters ON games(is_free, price_eur, price_usd);
CREATE INDEX idx_price_eur ON games(price_eur);
CREATE INDEX idx_price_usd ON games(price_usd);
CREATE INDEX idx_multi_platform ON games(steam_url, itch_url, crazygames_url);

-- Composite indexes for common filter combinations
CREATE INDEX idx_platform_absorbed_rating ON games(platform, is_absorbed, positive_review_percentage);
CREATE INDEX idx_absorbed_video_date ON games(is_absorbed, latest_video_date);
CREATE INDEX idx_hidden_gems ON games(positive_review_percentage, video_count, review_count) WHERE positive_review_percentage >= 80;
CREATE INDEX idx_games_on_sale ON games(is_on_sale, discount_percent) WHERE is_on_sale = 1;

-- Indexes for sorting performance
CREATE INDEX idx_sort_rating_priority ON games(review_summary_priority, positive_review_percentage, review_count);
CREATE INDEX idx_sort_date_name ON games(latest_video_date, name);
CREATE INDEX idx_sort_release_date ON games(release_date_sortable, name);

-- Game videos performance indexes
CREATE INDEX idx_video_date ON game_videos(video_date);
CREATE INDEX idx_game_video_date ON game_videos(game_id, video_date);
CREATE INDEX idx_channel_video_date ON game_videos(channel_name, video_date);
