# CubScrape Architecture

## Core Design Principles

1. **Separation of Concerns**: Videos and Steam data are stored separately with independent update cycles
2. **Incremental Processing**: Videos are immutable once fetched; Steam data refreshes based on staleness
3. **Platform Agnostic**: Supports both Steam and Itch.io games
4. **Efficient Pagination**: Uses yt-dlp playlist offsets to resume scraping from any point
5. **Smart Relationships**: Bidirectional demo/full game detection and auto-fetching
6. **User-Centric Display**: Intelligent card selection based on game release status

## Data Flow

```
YouTube Channel → Video Extraction → Steam/Itch Link Detection → Steam API + Web Scraping → Demo/Full Game Detection → JSON Storage → SQLite Database → Web Interface
```

## File Structure

```
/scraper/
  scraper.py          # Main scraper using modular components
  steam_fetcher.py    # Steam-specific data fetching and parsing
  steam_updater.py    # Steam data orchestration and multi-channel updates
  itch_fetcher.py     # Itch.io data fetching and parsing
  crazygames_fetcher.py # CrazyGames data fetching and parsing
  youtube_extractor.py # YouTube video metadata extraction
  game_inference.py   # Game name inference and Steam matching
  data_manager.py     # Data loading, saving, and serialization
  database_manager.py # SQLite database operations and schema management
  config_manager.py   # Configuration loading and management
  data_quality.py     # Data quality checking and reporting
  models.py           # Structured dataclasses for type safety
  utils.py            # Shared utility functions
  __init__.py         # Python package initialization
  # Python dependencies managed by uv (see pyproject.toml)
  
/data/
  videos-{channel}.json # Per-channel YouTube video metadata (data source for database)
  steam_games.json    # Steam game data with detailed review information (data source for database)
  other_games.json    # Itch.io and CrazyGames metadata (data source for database)
  games.db            # SQLite database - primary data source for web interface
  schema.sql          # Database schema definition and indexes
  
/web/
  index.html          # Main web interface
  script.js           # Client-side data loading and filtering
  style.css           # Dark theme styling
  
/.github/workflows/
  scrape.yml          # Automated scraping workflow
  pages-with-db.yml   # GitHub Pages deployment with database generation
```

## Key Components

### Video Processing (`process_videos`)
- Uses yt-dlp to fetch video metadata without API keys
- Extracts Steam/Itch.io links using regex patterns
- Implements smart pagination to skip known videos
- Stores immutable video data with game link references

### Steam Data Processing (`update_steam_data`)
- Fetches comprehensive game data from Steam API and store pages
- Extracts detailed review metrics including summaries and recent reviews
- Tracks both overall and recent review percentages, counts, and summaries
- Handles insufficient review cases with appropriate flags
- Implements staleness detection (default: 7 days)
- Handles age-gated content and review parsing

### Database Storage (`database_manager.py`)
- SQLite database with normalized schema for games and videos
- JSON files serve as data sources that populate the database
- Web interface queries SQLite database directly for performance
- Comprehensive game table with review metrics, pricing, and metadata
- Separate game_videos table linking videos to games
- Performance indexes on key filtering columns (platform, rating, price)
- Schema versioning through `schema.sql` file

### Web Interface
- Queries SQLite database directly for game and video data
- Intelligent game consolidation (eliminates duplicates)
- Smart card selection (demo cards for unreleased games)
- Provides filtering by platform, rating, release status, tags
- Displays comprehensive game information with review counts
- Optimized for game discovery workflow with database-powered performance

## Review Data Extraction

The scraper extracts both overall and recent reviews from Steam:
- **Overall Reviews**: Long-term game reputation (prioritized)
- **Recent Reviews**: Recent sentiment (supplementary)
- Uses text-based parsing due to inconsistent Steam page structure

## Scalability Features

- **Batch Processing**: Configurable batch sizes for video fetching
- **Rate Limiting**: Built into yt-dlp and Steam requests
- **Resumable**: Can continue from any point in channel history
- **Efficient Storage**: Normalized data prevents duplication

## GitHub Actions Integration

### Automated Scraping (`scrape.yml`)
- **Automated Scraping**: Runs on schedule or manual trigger
- **Data Persistence**: Commits updated JSON files
- **Environment Management**: Uses repository secrets for configuration

### GitHub Pages Deployment (`pages-with-db.yml`)
- **Database Generation**: Creates SQLite database from JSON data sources during deployment
- **Triggered On**: JSON data changes in data/ directory
- **GitHub Pages**: Automatically deploys web interface with database
- **Performance**: Web interface queries SQLite database directly for optimal performance