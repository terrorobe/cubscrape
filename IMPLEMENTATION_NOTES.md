# Implementation Notes

## Key Technical Decisions

### YouTube Scraping
- Uses yt-dlp with playlist pagination (`playliststart`/`playlistend`)

### Data Storage  
- Per-channel video files, shared game metadata files
- Independent update cycles for videos vs game data

### Steam Review Extraction
- Text-based regex parsing for inconsistent page structures

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

