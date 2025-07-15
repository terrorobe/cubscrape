# Implementation Notes

## Key Technical Decisions

### YouTube Scraping
- Uses yt-dlp with playlist pagination (`playliststart`/`playlistend`)

### Data Storage  
- **SQLite-Centric**: Database serves as primary data source for web interface
- **JSON Files**: Intermediate data sources that populate the SQLite database
- **Database**: Normalized schema with games and game_videos tables
- **Schema Management**: Versioned through `data/schema.sql` with comprehensive indexes
- **Data Flow**: Scraper → JSON → Database → Web Interface
- Independent update cycles for videos vs game data

### Steam Review Extraction
- Text-based regex parsing for inconsistent page structures
- Extracts comprehensive review data: overall and recent percentages, counts, and summaries
- Handles insufficient review scenarios with dedicated flag
- Database schema includes: `review_summary`, `recent_review_percentage`, `recent_review_count`, `recent_review_summary`, `insufficient_reviews`

### Smart Pagination
- Two-phase: lightweight ID fetching → full metadata for new videos only
- Smart starting position to skip known videos

### Platform Prioritization
- Steam primary, itch.io marked as demo when both present

### Demo/Full Game Detection  
- Bidirectional relationship detection and auto-fetching
- Handles Steam protocol links (`steam://install/`) and Community Hub patterns

### Release Date Extraction
- Filters out system requirements to avoid false date matches

### Modular Code Structure
- **Main Scraper**: `scraper/scraper.py` - Fully modularized implementation using structured components
- **Fetchers**: `steam_fetcher.py`, `itch_fetcher.py`, `crazygames_fetcher.py` - Platform-specific data fetching
- **Steam Updater**: `steam_updater.py` - Steam data orchestration and multi-channel updates
- **YouTube Extractor**: `youtube_extractor.py` - YouTube video metadata extraction and processing
- **Game Inference**: `game_inference.py` - Game name inference and Steam matching logic
- **Data Management**: `data_manager.py` - Data loading, saving, and serialization operations
- **Database Management**: `database_manager.py` - SQLite database operations and schema management
- **Configuration**: `config_manager.py` - Configuration loading and management
- **Data Quality**: `data_quality.py` - Data quality checking and reporting tools
- **Models**: `models.py` - Structured dataclasses (VideoData, SteamGameData, OtherGameData, GameLinks)
- **Utils**: `utils.py` - Shared utility functions (game link extraction, similarity matching, etc.)
- **Type Safety**: Full migration from dictionaries to dataclasses for better maintainability

### Interactive Game Resolution
- Prompts for low confidence matches instead of algorithmic guessing
- Example: "Asgard's Fall" → "Asgard's Fall — Viking Survivors" (0.40 confidence)


## Testing Strategy

### Manual Testing Commands
```bash
# Ensure virtual environment is active
source .venv/bin/activate

# Test specific channel processing
python scraper/scraper.py backfill --channel olexa --max-new 5

# Test missing Steam games resolution (interactive)
python scraper/scraper.py infer-games

# Test data quality checks
python scraper/scraper.py data-quality

# Fetch single Steam app (useful for debugging)
python scraper/scraper.py single-app --app-id 3586420

# Test all channels (cron mode)
python scraper/scraper.py cron
```

