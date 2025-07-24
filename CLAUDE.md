# Claude Development Notes

## Important Development Practices

- **Running Background Processes**: Use `nohup <command> > <logfile> 2>&1 &` for any long-running process (web servers, etc.) to prevent terminal blocking. Check with `tail <logfile>` to verify it started.

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
uv sync --extra dev

# Run the scraper
cubscrape cron
cubscrape backfill --channel dextag
cubscrape --help

# Alternative module execution
uv run python -m scraper.cli_commands cron

# Development tools
uv run ruff check
uv run mypy .
```

### Development Workflow

1. **Initial setup**: `uv sync --extra dev`
2. **Run scraper**: `cubscrape cron` or `uv run python -m scraper.cli_commands cron`
3. **Add dependencies**: Edit `pyproject.toml` then run `uv sync`
4. **Run linters**: 
   - Python: `uv run ruff check --fix`
   - Python types: `uv run mypy .`
   - JavaScript/Vue: `npx eslint . --fix`

## Web Development Environment

### Commands
- **Start dev server**: `npm run dev` (prevents multiple instances with lock file)
- **Stop dev server**: `npm run stop-dev` or Ctrl+C
- **Build**: `npm run build`

### Lock File System
- **Lock file**: `data/.dev-server.lock` prevents concurrent dev server instances
- **Child process cleanup**: Automatically kills Vite when parent process dies
- **Process monitoring**: Handles manual kills of either parent or child processes

### Database Management
- **Development**: Automatic database reloading when JSON files change via Vite HMR
- **Production**: Timer-based checking every 10 minutes for database updates
- **Status display**: Shows database generation time and last check time with relative timestamps

### Dependencies

**Runtime dependencies** (in `[project.dependencies]`):
- yt-dlp - YouTube video metadata extraction
- requests - HTTP client
- beautifulsoup4 - HTML parsing
- lxml - XML/HTML parser

**Development dependencies** (in `[project.optional-dependencies.dev]`):
- ruff - Python linter and formatter
- mypy - Static type checker

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
- **`steam_updater.py`** - Steam data orchestration and multi-channel updates
- **Platform fetchers**: `steam_fetcher.py`, `itch_fetcher.py`, `crazygames_fetcher.py`
- **`base_fetcher.py`** - BeautifulSoup type-safe helper methods

### Web Interface:
- **`script.js`** - Refactored with utility functions and modular templates
- **`index.html`** - Game discovery interface
- **`style.css`** - Styling

### Steam Refresh Intervals:
Steam games are updated using age-based intervals:
- **New games** (< 30 days): Daily refresh
- **Recent games** (< 365 days): Weekly refresh  
- **Older games** (≥ 365 days): Monthly refresh

## JavaScript Environment Setup

This project uses **npm** for JavaScript dependency management and ESLint for code linting.

### Key Files
- `package.json` - JavaScript project configuration and dependencies
- `eslint.config.js` - ESLint configuration for code quality
- `script.js` - Main JavaScript file for the web interface

### JavaScript Commands

```bash
# Install JavaScript dependencies
npm install

# Run ESLint to check code quality
npx eslint script.js

# Fix auto-fixable ESLint issues
npx eslint script.js --fix

# Add npm scripts to package.json for common tasks
npm run lint    # (after adding lint script)
```

### JavaScript Development Workflow

1. **Linting**: Run `npx eslint script.js` to check for issues
2. **Auto-fix**: Use `npx eslint script.js --fix` to automatically fix many issues
3. **Manual fixes**: Address remaining issues like missing braces, const usage, etc.

### JavaScript Dependencies

**Development dependencies**:
- eslint - JavaScript linter for code quality and consistency

### ESLint Configuration
The project uses a custom ESLint configuration that enforces:
- **Code quality**: No console statements (warnings), no debugger, consistent variable declarations
- **Best practices**: Prefer const over let, require curly braces for conditionals
- **Code style**: 4-space indentation, single quotes, semicolons required

## Development Issues

### JSON Data Analysis
- **Prefer `jq` over `grep`** when analyzing JSON files like `steam_games.json`
- `grep` can give misleading results due to JSON structure complexity
- **Example**: Use `jq '.games["2651220"]' data/steam_games.json` instead of `grep -A 20 "2651220" data/steam_games.json`
- For finding games by name: `jq -r '.games | to_entries[] | select(.value.name | contains("Blacksmith")) | .key + ": " + .value.name' data/steam_games.json`

