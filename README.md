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
- Node.js 20+
- npm (comes with Node.js)
- direnv (recommended for automatic environment loading)

### Installation

1. Clone the repository
2. Install Python dependencies:
   ```bash
   uv sync --extra dev
   ```
   This creates a virtual environment and installs all dependencies including development tools.

3. Install JavaScript dependencies:
   ```bash
   npm install
   ```
   
   **TypeScript Support**: The frontend has been migrated to TypeScript for improved type safety and developer experience. All Vue components and utilities now use TypeScript with strict type checking.

4. Configure channels and options:
   ```bash
   # Edit config.json to configure YouTube channels and scraper options
   ```
   
   **Configuration Options**:
   - **channels**: YouTube channels to scrape with URLs and enabled status
   - **skip_steam_matching**: List of game names to exclude from Steam matching (e.g., "League of Legends")


### Processing Modes

Note: If `cubscrape` command is not available in your PATH, prefix all commands with `uv run`.

**Backfill Mode** - Process a specific channel with full options:
```bash
cubscrape backfill --channel idlecub --max-new 20
cubscrape backfill --channel dextag --max-steam-updates 10
cubscrape backfill --channel olexa --max-new 50
```

Note: Steam games now use age-based refresh intervals automatically:
- Games < 30 days old: Daily refresh
- Games < 365 days old: Weekly refresh  
- Games ≥ 365 days old: Monthly refresh

**Cron Mode** - Process recent videos from all enabled channels:
```bash
cubscrape cron
```

**Reprocess Mode** - Reprocess existing videos to extract new game links:
```bash
cubscrape reprocess --channel idlecub
```

**Single App Mode** - Fetch specific Steam game data:
```bash
cubscrape single-app --app-id 123456
```

**Data Quality Mode** - Check data integrity and completeness:
```bash
cubscrape data-quality
# Identifies missing Steam games referenced in videos
```

**Game Inference Mode** - Find games from video titles and resolve missing Steam games:
```bash
cubscrape infer-games
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

The web interface is built with Vue 3, Vite, and Tailwind CSS.

#### Development Mode
```bash
# Start dev server (automatically builds DB if needed)
npm run dev

# Or skip DB check and just run Vite
npm run dev:vite
```
Visit http://localhost:5173/

#### Production Build
```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

#### Database Setup
The Vue app expects a SQLite database at `/data/games.db`:
```bash
# Build the SQLite database
cubscrape build-db
# OR
npm run build-db
```

#### Other Commands
```bash
# Lint and format code
npm run lint
npm run lint:fix
npm run format
npm run format:check

# TypeScript type checking (added during TypeScript migration)
npx tsc --noEmit           # Check types without emitting files
npx vue-tsc --noEmit       # Vue component type checking
```

## TypeScript Migration

The frontend codebase has been fully migrated to TypeScript for enhanced type safety and developer experience. Key aspects of the TypeScript implementation:

### Type System Features
- **Strict Type Checking**: Comprehensive type definitions for all data structures
- **Database Types**: Auto-generated types from SQLite schema for type-safe database operations
- **Vue Integration**: Full TypeScript support for Vue 3 components with Composition API
- **Configuration Types**: Strongly typed configuration system with JSDoc documentation

### Key Type Definitions
- **Database Schema**: `/src/types/database.ts` - Generated types matching SQLite database structure
- **Vue Components**: All `.vue` files use TypeScript with `<script setup lang="ts">`
- **Utilities**: Type-safe utilities in `/src/utils/` with proper error handling
- **Configuration**: Centralized configuration in `/src/config/` with comprehensive type annotations

### Development Workflow
- **Type Checking**: `npx tsc --noEmit` for TypeScript validation
- **Vue Types**: `npx vue-tsc --noEmit` for Vue component type checking
- **IDE Support**: Full IntelliSense and error detection in modern IDEs
- **Build Integration**: Vite handles TypeScript compilation automatically

The migration maintains full backward compatibility while adding type safety that catches errors at compile time and improves code maintainability.

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