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
YouTube Channel → Video Extraction → Steam/Itch Link Detection → Steam API + Web Scraping → Demo/Full Game Detection → JSON Storage → Smart Card Selection → Web View
```

## File Structure

```
/scraper/
  scraper.py          # Main scraper using modular components
  steam_fetcher.py    # Steam-specific data fetching and parsing
  itch_fetcher.py     # Itch.io data fetching and parsing
  crazygames_fetcher.py # CrazyGames data fetching and parsing
  models.py           # Structured dataclasses for type safety
  utils.py            # Shared utility functions
  requirements.txt    # Python dependencies (yt-dlp, requests, beautifulsoup4)
  
/data/
  videos-{channel}.json # Per-channel YouTube video metadata with game links
  steam_games.json    # Steam game data with review scores
  other_games.json    # Itch.io and CrazyGames metadata
  
/web/
  index.html          # Main web interface
  script.js           # Client-side data loading and filtering
  style.css           # Dark theme styling
  
/.github/workflows/
  scrape.yml          # Automated scraping workflow
```

## Key Components

### Video Processing (`process_videos`)
- Uses yt-dlp to fetch video metadata without API keys
- Extracts Steam/Itch.io links using regex patterns
- Implements smart pagination to skip known videos
- Stores immutable video data with game link references

### Steam Data Processing (`update_steam_data`)
- Fetches comprehensive game data from Steam API and store pages
- Extracts both overall and recent review metrics
- Implements staleness detection (default: 7 days)
- Handles age-gated content and review parsing

### Web Interface
- Loads separate JSON files and combines client-side
- Intelligent game consolidation (eliminates duplicates)
- Smart card selection (demo cards for unreleased games)
- Provides filtering by platform, rating, release status, tags
- Displays comprehensive game information with review counts
- Optimized for game discovery workflow

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

- **Automated Scraping**: Runs on schedule or manual trigger
- **Data Persistence**: Commits updated JSON files
- **GitHub Pages**: Automatically deploys web interface
- **Environment Management**: Uses repository secrets for configuration