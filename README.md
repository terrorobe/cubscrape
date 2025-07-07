# CubScrape - YouTube to Steam Game Discovery

A tool that scrapes YouTube gaming channels to discover Steam games, fetches their metadata, and presents them in a filterable web interface.

## Features

- **YouTube Integration**: Fetches videos from multiple channels using yt-dlp (no API key required)
- **Multi-Platform Support**: Extracts Steam, Itch.io, and CrazyGames links from descriptions
- **Multi-Channel Support**: Configure and process multiple YouTube channels independently
- **Comprehensive Steam Data**: 
  - Overall and recent review scores with counts
  - Tags, release status, pricing, demo availability
  - Early access and coming soon detection
  - Enhanced planned release dates (specific dates, quarters)
  - Bidirectional demo/full game relationship detection
- **Smart Incremental Updates**: 
  - Videos fetched once (immutable)
  - Steam data refreshed independently with staleness detection
  - Efficient pagination through channel history
  - Automatic demo/full game data fetching
- **Modern Web Interface**: 
  - Dark theme optimized for game discovery
  - Smart game consolidation (no duplicate games)
  - Intelligent demo/full game card selection
  - **Multi-channel support with videos grouped by creator**
  - **Social preview images for enhanced visual appeal**
  - Filters by platform, release status, rating, tags, and channel
  - Sortable by rating, date, or name
  - Shows both overall and recent review data
  - Unified rating scale (0-100) across all platforms

## Setup

### Prerequisites
- Python 3.8+
- direnv (recommended for automatic environment loading)

### Installation

1. Clone the repository
2. Set up virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Or use direnv with the included .envrc
   ```

3. Install Python dependencies:
   ```bash
   pip install -r scraper/requirements.txt
   ```

4. Configure channels:
   ```bash
   # Edit config.json to add/remove YouTube channels
   # Channels are configured with their URLs and enabled status
   ```

### Virtual Environment Management

This project uses a Python virtual environment (`.venv/`) and includes a `.envrc` file for automatic activation with direnv:

- **Manual activation**: `source .venv/bin/activate`
- **With direnv**: The environment activates automatically when entering the directory
- **Deactivation**: `deactivate` (manual) or leave directory (direnv)

### Running the Scraper

```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # Or use direnv
```

### Processing Modes

**Backfill Mode** - Process a specific channel with full options:
```bash
python scraper/scraper.py backfill --channel idlecub --max-new 20
python scraper/scraper.py backfill --channel dextag --max-steam-updates 10
```

**Cron Mode** - Process recent videos from all enabled channels:
```bash
python scraper/scraper.py cron
```

**Reprocess Mode** - Reprocess existing videos to extract new game links:
```bash
python scraper/scraper.py reprocess --channel idlecub
```

**Single App Mode** - Fetch specific Steam game data:
```bash
python scraper/scraper.py single-app --app-id 123456
```

**Data Quality Mode** - Check data integrity and completeness:
```bash
python scraper/scraper.py data-quality
```

**Game Inference Mode** - Find games from video titles using Steam search:
```bash
python scraper/scraper.py infer-games
```

The scraper will:
- Fetch videos from configured YouTube channels
- Extract Steam/Itch.io/CrazyGames links from descriptions
- **Infer games from video titles when links are missing**
- Fetch comprehensive game metadata from all platforms
- **Extract social preview images (header images) for all platforms**
- Detect and fetch demo/full game relationships
- **Handle insufficient reviews and coming soon games gracefully**
- **Check data quality and identify missing metadata**
- Save data to separate files:
  - `data/videos-{channel}.json` - YouTube video data per channel
  - `data/steam_games.json` - Steam game data (including demos)
  - `data/other_games.json` - Itch.io and CrazyGames metadata

### Viewing the Web Interface

1. Open `index.html` in a web browser
2. Or serve it with a local web server:
   ```bash
   python -m http.server 8000
   # Visit http://localhost:8000/
   ```

## GitHub Actions Setup

The project can be automated with GitHub Actions to:
1. Run the scraper periodically
2. Commit updated data
3. Deploy to GitHub Pages

See `.github/workflows/scrape.yml` for the workflow configuration.

## Data Structure

The scraper saves data in two separate files:

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