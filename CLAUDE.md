# Claude Development Notes

## Important Development Practices

- **Running Background Processes**: Use `nohup <command> > <logfile> 2>&1 &` for any long-running process (web servers, etc.) to prevent terminal blocking. Check with `tail <logfile>` to verify it started.

## Documentation Overview

- **README.md** - Project overview, setup instructions, and usage
- **docs/ARCHITECTURE.md** - System architecture, data flow, and component design  
- **docs/IMPLEMENTATION_NOTES.md** - Detailed implementation notes and technical decisions
- **docs/FAVICON.md** - Favicon generation and design documentation
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
uv run basedpyright
```

### Development Workflow

1. **Initial setup**: `uv sync --extra dev`
2. **Run scraper**: `cubscrape cron` or `uv run python -m scraper.cli_commands cron`
3. **Add dependencies**: Edit `pyproject.toml` then run `uv sync`
4. **Run linters**: 
   - Python: `uv run ruff check --fix`
   - Python types: `uv run basedpyright`
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
- basedpyright - Static type checker (fork of Pyright with additional features)

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
- **`src/`** - Vue.js application source code
- **`src/App.vue`** - Main application component
- **`src/main.js`** - Application entry point
- **`src/components/`** - Vue components (GameCard, GameFilters, etc.)
- **`src/utils/`** - Utility modules (databaseManager, performanceMonitor, etc.)
- **`src/style.css`** - Global styling

### Steam Refresh Intervals:
Steam games are updated using age-based intervals:
- **New games** (< 30 days): Daily refresh
- **Recent games** (< 365 days): Weekly refresh  
- **Older games** (≥ 365 days): Monthly refresh

## Vue.js Environment Setup

This project uses **Vue.js 3** with **Vite** for the web interface, **npm** for dependency management, and **ESLint** for code linting.

### Key Files
- `package.json` - Project configuration and dependencies
- `eslint.config.js` - ESLint configuration for code quality
- `vite.config.js` - Vite build configuration
- `src/main.js` - Vue application entry point
- `src/App.vue` - Root application component

### Development Commands

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Run ESLint to check code quality
npx eslint src/

# Fix auto-fixable ESLint issues
npx eslint src/ --fix
```

### Vue.js Development Workflow

1. **Development**: Run `npm run dev` to start the Vite dev server with HMR
2. **Linting**: Run `npx eslint src/` to check for issues
3. **Auto-fix**: Use `npx eslint src/ --fix` to automatically fix many issues
4. **Building**: Run `npm run build` for production builds

### Frontend Dependencies

**Vue.js ecosystem**:
- vue - Progressive JavaScript framework
- vite - Fast build tool and dev server

**Development dependencies**:
- eslint - JavaScript/Vue linter for code quality and consistency

### ESLint Configuration
The project uses ESLint configured for Vue.js that enforces:
- **Vue.js best practices**: Proper component structure and composition API usage
- **Code quality**: No console statements (warnings), no debugger, consistent variable declarations
- **Modern JavaScript**: ES6+ features, proper async/await usage

## Production Deployment

- **GitHub Pages URL**: https://terrorobe.github.io/cubscrape/
- **Database compression**: GitHub Pages automatically serves `games.db` with gzip (3MB → ~655KB)

## Development Issues

### JSON Data Analysis
- **Prefer `jq` over `grep`** when analyzing JSON files like `steam_games.json`
- `grep` can give misleading results due to JSON structure complexity
- **Example**: Use `jq '.games["2651220"]' data/steam_games.json` instead of `grep -A 20 "2651220" data/steam_games.json`
- For finding games by name: `jq -r '.games | to_entries[] | select(.value.name | contains("Blacksmith")) | .key + ": " + .value.name' data/steam_games.json`

### Favicon Management
- **Source file**: `public/favicon.svg` with purple-to-blue gradient and optically-centered play triangle
- **Regeneration**: Use `resvg` for high-quality PNG generation (preserves gradients)
- **Documentation**: See `docs/FAVICON.md` for complete regeneration instructions
- **Quality**: Always use `resvg` instead of ImageMagick for PNG conversion to maintain gradient quality

