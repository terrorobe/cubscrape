# CubScrape - YouTube to Steam Game Discovery

A tool that scrapes YouTube gaming channels to discover Steam games, fetches their metadata, and presents them in a filterable web interface.

## Features

- **YouTube Integration**: Fetches videos from channels using yt-dlp (no API key required)
- **Multi-Platform Support**: Extracts both Steam and Itch.io game links from descriptions
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
  - Filters by platform, release status, rating, tags
  - Sortable by rating, date, or name
  - Shows both overall and recent review data

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

4. Configure environment variables:
   ```bash
   # Edit .env with your YouTube channel URL
   # The .env file is already present with example configuration
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

# Run the scraper from project root
python scraper/scraper.py
```

The scraper will:
- Fetch recent videos from the configured YouTube channel
- Extract Steam/Itch links from descriptions
- Fetch comprehensive game data from Steam
- Detect and fetch demo/full game relationships
- Save data to separate files:
  - `data/videos.json` - YouTube video data
  - `data/steam_games.json` - Steam game data (including demos)

### Update Modes

```bash
# Update only videos (incremental, fetches new videos only)
python scraper/scraper.py --mode videos --max-new 10

# Update only Steam data (refreshes stale game data)
python scraper/scraper.py --mode steam --max-steam-updates 5 --steam-stale-days 7

# Update both (default)
python scraper/scraper.py --mode both

# Examples:
python scraper/scraper.py --max-new 20  # Get 20 new videos + update stale Steam data
python scraper/scraper.py --mode steam --steam-stale-days 0  # Force refresh all Steam data
```

### Viewing the Web Interface

1. Open `web/index.html` in a web browser
2. Or serve it with a local web server:
   ```bash
   python -m http.server 8000
   # Visit http://localhost:8000/web/
   ```

## GitHub Actions Setup

The project can be automated with GitHub Actions to:
1. Run the scraper periodically
2. Commit updated data
3. Deploy to GitHub Pages

See `.github/workflows/scrape.yml` for the workflow configuration.

## Data Structure

The scraper saves data in two separate files:

**videos.json** - YouTube video data:
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