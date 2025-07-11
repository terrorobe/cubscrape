# CubScrape - YouTube to Steam Game Discovery

A tool that scrapes YouTube gaming channels to discover Steam games, fetches their metadata, and presents them in a filterable web interface.

## Features

- **Multi-Platform Support**: Steam, Itch.io, and CrazyGames link extraction and metadata
- **Multi-Channel Support**: Process multiple YouTube channels independently  
- **Interactive Game Resolution**: Prompts for low confidence matches, handles missing/depublished games
- **Web Interface**: Filterable, sortable game discovery with unified 0-100 rating scale

## Setup

### Prerequisites
- Python 3.12+
- uv (Python package manager)
- direnv (recommended for automatic environment loading)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   uv sync --extra dev
   ```
   This creates a virtual environment and installs all dependencies including development tools.

4. Configure channels and options:
   ```bash
   # Edit config.json to configure YouTube channels and scraper options
   ```
   
   **Configuration Options**:
   - **channels**: YouTube channels to scrape with URLs and enabled status
   - **skip_steam_matching**: List of game names to exclude from Steam matching (e.g., "League of Legends")


### Processing Modes

**Backfill Mode** - Process a specific channel with full options:
```bash
uv run python scraper/scraper.py backfill --channel idlecub --max-new 20
uv run python scraper/scraper.py backfill --channel dextag --max-steam-updates 10
uv run python scraper/scraper.py backfill --channel olexa --max-new 50
```

Note: Steam games now use age-based refresh intervals automatically:
- Games < 30 days old: Daily refresh
- Games < 365 days old: Weekly refresh  
- Games ≥ 365 days old: Monthly refresh

**Cron Mode** - Process recent videos from all enabled channels:
```bash
uv run python scraper/scraper.py cron
```

**Reprocess Mode** - Reprocess existing videos to extract new game links:
```bash
uv run python scraper/scraper.py reprocess --channel idlecub
```

**Single App Mode** - Fetch specific Steam game data:
```bash
uv run python scraper/scraper.py single-app --app-id 123456
```

**Data Quality Mode** - Check data integrity and completeness:
```bash
uv run python scraper/scraper.py data-quality
# Identifies missing Steam games referenced in videos
```

**Game Inference Mode** - Find games from video titles and resolve missing Steam games:
```bash
uv run python scraper/scraper.py infer-games
# Uses YouTube's game detection when available (more reliable)
# Falls back to title parsing for game name extraction  
# Interactive prompts for low confidence matches
# Resolves missing/depublished Steam games
```

Data is saved to:
- `data/videos-{channel}.json` - YouTube video data per channel
- `data/steam_games.json` - Steam game metadata
- `data/other_games.json` - Itch.io and CrazyGames metadata

### Viewing the Web Interface

1. Open `index.html` in a web browser
2. Or serve it with a local web server:
   ```bash
   uv run python -m http.server 8000
   # Visit http://localhost:8000/
   ```

## Data Structure

Key data structures:

**videos-{channel}.json** - YouTube video data per channel:
```json
{
  "videos": {
    "video_id": {
      "video_id": "...",
      "title": "...",
      "description": "...",
      "published_at": "...",
      "thumbnail": "...",
      "steam_app_id": "12345",
      "itch_url": "https://...",
      "crazygames_url": "https://...",
      "broken_app_id": "789012",
      "inferred_game": true,
      "inference_reason": "missing_steam_game",
      "channel_id": "idlecub",
      "channel_name": "Idle Cub",
      "last_updated": "2025-01-07T..."
    }
  },
  "last_updated": "2025-01-07T..."
}
```

**steam_games.json** - Steam game data:
```json
{
  "games": {
    "12345": {
      "steam_app_id": "12345",
      "name": "...",
      "tags": ["..."],
      "positive_review_percentage": 85,
      "review_summary": "Very Positive",
      "is_early_access": false,
      "has_demo": true,
      "last_updated": "2025-01-07T...",
      ...
    }
  },
  "last_updated": "2025-01-07T..."
}
```