# Claude Development Notes

## Documentation Overview

- **README.md** - Project overview, setup instructions, and usage
- **ARCHITECTURE.md** - System architecture, data flow, and component design  
- **IMPLEMENTATION_NOTES.md** - Detailed implementation notes and technical decisions
- **CLAUDE.md** - This file: Development environment and workflow notes

## Python Environment Setup

This project uses **uv** for Python dependency management and virtual environment handling.

### Key Files
- `pyproject.toml` - Project configuration and dependency specifications with version ranges
- `uv.lock` - Locked exact versions for reproducible builds (committed to git)
- `.venv/` - Virtual environment directory (not committed)

### Environment Commands

```bash
# Install dependencies and create/activate virtual environment
uv sync

# Install with development dependencies (includes ruff linter)
uv sync --extra dev

# Update packages to latest versions within constraints
uv sync --upgrade --extra dev

# Run commands in the virtual environment
uv run python scraper/scraper.py
uv run ruff check

# Check installed packages
uv pip list
```

### Development Workflow

1. **Initial setup**: `uv sync --extra dev`
2. **Add dependencies**: Edit `pyproject.toml` then run `uv sync`
3. **Update packages**: `uv sync --upgrade --extra dev`
4. **Run linter**: `uv run ruff check` (or `uv run ruff check --fix`)
5. **Run scripts**: `uv run python scraper/scraper.py cron`

### Dependencies

**Runtime dependencies** (in `[project.dependencies]`):
- yt-dlp - YouTube video metadata extraction
- requests - HTTP client
- beautifulsoup4 - HTML parsing
- lxml - XML/HTML parser

**Development dependencies** (in `[project.optional-dependencies.dev]`):
- ruff - Python linter and formatter

### Notes
- Always commit `uv.lock` for reproducible builds
- Use version ranges (>=) in `pyproject.toml`, not exact pins (==)
- The virtual environment is automatically activated when using `uv run`
- No need to manually activate/deactivate the virtual environment

## Codebase Architecture

The scraper has been refactored into modular components:

### Core Modules (`scraper/` directory):
- **`scraper.py`** - Main orchestration and CLI interface
- **`data_manager.py`** - Data loading, saving, and serialization
- **`youtube_extractor.py`** - YouTube video metadata extraction
- **`game_inference.py`** - Game name inference and Steam matching
- **`data_quality.py`** - Data quality checking and reporting
- **`config_manager.py`** - Configuration loading and management
- **`models.py`** - Data structures (VideoData, SteamGameData, etc.)
- **`utils.py`** - Utility functions
- **Platform fetchers**: `steam_fetcher.py`, `itch_fetcher.py`, `crazygames_fetcher.py`

### Web Interface:
- **`script.js`** - Refactored with utility functions and modular templates
- **`index.html`** - Game discovery interface
- **`style.css`** - Styling

### Steam Refresh Intervals:
Steam games are updated using age-based intervals:
- **New games** (< 30 days): Daily refresh
- **Recent games** (< 365 days): Weekly refresh  
- **Older games** (≥ 365 days): Monthly refresh