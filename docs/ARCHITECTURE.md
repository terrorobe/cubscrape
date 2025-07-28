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
YouTube Channel → Video Extraction → Steam/Itch Link Detection → Steam API + Web Scraping → Demo/Full Game Detection → JSON Storage → SQLite Database → Web Interface
```

## File Structure

```
/scraper/
  scraper.py          # Main scraper using modular components
  steam_fetcher.py    # Steam-specific data fetching and parsing
  steam_updater.py    # Steam data orchestration and multi-channel updates
  itch_fetcher.py     # Itch.io data fetching and parsing
  crazygames_fetcher.py # CrazyGames data fetching and parsing
  youtube_extractor.py # YouTube video metadata extraction
  game_inference.py   # Game name inference and Steam matching
  data_manager.py     # Data loading, saving, and serialization
  database_manager.py # SQLite database operations and schema management
  config_manager.py   # Configuration loading and management
  data_quality.py     # Data quality checking and reporting
  models.py           # Structured dataclasses for type safety
  utils.py            # Shared utility functions
  __init__.py         # Python package initialization
  # Python dependencies managed by uv (see pyproject.toml)
  
/data/
  videos-{channel}.json # Per-channel YouTube video metadata (data source for database)
  steam_games.json    # Steam game data with detailed review information (data source for database)
  other_games.json    # Itch.io and CrazyGames metadata (data source for database)
  games.db            # SQLite database - primary data source for web interface
  schema.sql          # Database schema definition and indexes
  
/src/ (TypeScript Frontend)
  main.ts             # Vue.js application entry point (TypeScript)
  App.vue             # Main application component with TypeScript
  style.css           # Global styling with dark theme
  components/         # Vue components with TypeScript support
  config/             # Centralized configuration system (TypeScript)
    index.ts          # Main configuration exports and utilities
    constants.ts      # Magic numbers, UI limits, and thresholds
    theme.ts          # Colors, spacing, timing, and visual tokens  
    platforms.ts      # Platform-specific configurations and logic
  utils/              # Utility modules (TypeScript with type safety)
  composables/        # Vue composition functions (TypeScript)
  types/              # TypeScript type definitions
    database.ts       # Database schema types
    vue-shims.d.ts    # Vue TypeScript declarations
  
/.github/workflows/
  scrape.yml          # Automated scraping workflow
  pages-with-db.yml   # GitHub Pages deployment with database generation
```

## Key Components

### Video Processing (`process_videos`)
- Uses yt-dlp to fetch video metadata without API keys
- Extracts Steam/Itch.io links using regex patterns
- Implements smart pagination to skip known videos
- Stores immutable video data with game link references

### Steam Data Processing (`update_steam_data`)
- Fetches comprehensive game data from Steam API and store pages
- Extracts detailed review metrics including summaries and recent reviews
- Tracks both overall and recent review percentages, counts, and summaries
- Handles insufficient review cases with appropriate flags
- Implements staleness detection (default: 7 days)
- Handles age-gated content and review parsing

### Database Storage (`database_manager.py`)
- SQLite database with normalized schema for games and videos
- JSON files serve as data sources that populate the database
- Web interface queries SQLite database directly for performance
- Comprehensive game table with review metrics, pricing, and metadata
- Separate game_videos table linking videos to games
- Performance indexes on key filtering columns (platform, rating, price)
- Schema versioning through `schema.sql` file

### Web Interface
- Queries SQLite database directly for game and video data
- Intelligent game consolidation (eliminates duplicates)
- Smart card selection (demo cards for unreleased games)
- Provides filtering by platform, rating, release status, tags
- Displays comprehensive game information with review counts
- Optimized for game discovery workflow with database-powered performance

### Configuration System (`src/config/`)
- **Centralized Configuration**: All hardcoded values moved to dedicated configuration modules
- **Theme System**: Consistent colors, spacing, and timing tokens in `theme.js`
- **Constants Management**: Magic numbers, UI limits, and thresholds in `constants.js`
- **Platform Abstraction**: Platform-specific logic centralized in `platforms.js`
- **Type Safety**: JSDoc documentation for all configuration properties
- **Maintainability**: Single source of truth eliminates scattered hardcoded values

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

### Automated Scraping (`scrape.yml`)
- **Automated Scraping**: Runs on schedule or manual trigger
- **Data Persistence**: Commits updated JSON files
- **Environment Management**: Uses repository secrets for configuration

### GitHub Pages Deployment (`pages-with-db.yml`)
- **Database Generation**: Creates SQLite database from JSON data sources during deployment
- **Triggered On**: JSON data changes in data/ directory
- **GitHub Pages**: Automatically deploys web interface with database
- **Performance**: Web interface queries SQLite database directly for optimal performance

## TypeScript Architecture

The frontend has been fully migrated to TypeScript, providing comprehensive type safety and enhanced developer experience across all components.

### Type System Design

**Core Type Philosophy**:
- **Database-First Types**: All data types derive from SQLite schema, ensuring frontend-backend consistency
- **Strict Type Safety**: Zero tolerance for `any` types, comprehensive null checking
- **Vue Integration**: Full TypeScript support for Vue 3 Composition API with proper reactivity typing
- **Configuration Types**: Centralized, strongly-typed configuration system

### Type Structure

```typescript
// Database types generated from SQLite schema
interface Game {
  steam_app_id: string;
  name: string;
  rating: number;
  platform: 'steam' | 'itch' | 'crazygames';
  // ... comprehensive game properties
}

// Vue component props with strict typing
interface GameCardProps {
  game: Game;
  showVideo?: boolean;
  compactMode?: boolean;
}

// Configuration with JSDoc documentation
interface ThemeConfig {
  /** Primary application colors */
  colors: {
    primary: string;
    secondary: string;
    // ... type-safe color palette
  };
}
```

### Advanced TypeScript Features

**Generic Type Utilities**:
- **Database Operations**: Generic query builders with compile-time SQL validation
- **Reactive Data**: Vue 3 reactivity with preserved TypeScript inference
- **Component Props**: Conditional types for dynamic prop validation
- **Configuration System**: Template literal types for compile-time string validation

**Error Handling Patterns**:
- **Result Types**: Explicit error handling with `Result<T, E>` patterns
- **Type Guards**: Runtime type validation with compile-time guarantees
- **Null Safety**: Comprehensive optional chaining and nullish coalescing

### Integration Patterns

**Vue Component Architecture**:
```typescript
<script setup lang="ts">
// Compile-time prop validation
interface Props {
  games: Game[];
  filters: FilterState;
}
const props = defineProps<Props>();

// Type-safe composables
const { filteredGames, loading } = useGameFiltering(props.games);
</script>
```

**Database Layer**:
```typescript
// Type-safe database operations
class DatabaseManager {
  async getGames(filters: GameFilters): Promise<Game[]> {
    // SQLite queries with TypeScript validation
  }
}
```

**Configuration System**:
```typescript
// Central configuration with comprehensive types
export const CONFIG = {
  ui: {
    pagination: { defaultPageSize: 20 } as const,
    filters: { maxTags: 50 } as const
  }
} satisfies AppConfig;
```

### Development Workflow Integration

**Type Checking Pipeline**:
- **Build-time**: Vite TypeScript plugin validates all code during development
- **IDE Integration**: Full IntelliSense with error detection and auto-completion
- **Component Validation**: Vue-specific TypeScript checking with `vue-tsc`
- **Configuration Validation**: Compile-time validation of all configuration properties

**Migration Benefits**:
- **Bug Prevention**: Catches type mismatches and null reference errors at compile time
- **Refactoring Safety**: Confident large-scale code changes with comprehensive type checking
- **Documentation**: Types serve as living documentation for component interfaces
- **Developer Experience**: Enhanced IDE support with intelligent code completion

The TypeScript architecture maintains the existing component structure while adding a comprehensive type layer that prevents common JavaScript errors and improves long-term maintainability.

## Component Architecture

### Filter System Design

The filtering system uses a component library with consistent patterns and centralized state management.

**Core Components**:

1. **GameFilters.vue** - Main orchestrator
   - Coordinates all filter components
   - Handles desktop/mobile layouts
   - Provides 400ms debounced updates
   - Manages URL synchronization

2. **Multi-Select Filters**
   - `TagFilterMulti.vue` - Tag selection with AND/OR logic
   - `ChannelFilterMulti.vue` - Channel selection with search
   - Progressive loading for large datasets
   - Consistent dropdown patterns

3. **Range Filters**
   - `PriceFilter.vue` - Dual-range slider with presets
   - `TimeFilterSimple.vue` - Time-based filtering
   - `SortingOptions.vue` - Advanced sorting options

4. **Mobile Components**
   - `MobileFilterModal.vue` - Bottom sheet container
   - Touch-optimized with 44px targets
   - Swipe gestures for dismissal

5. **State Display**
   - `AppliedFiltersBar.vue` - Active filter chips
   - `FilterPresets.vue` - Preset management
   - `SortIndicator.vue` - Sort state indicator

### Design System

**Consistent Patterns**:
```css
/* Shared component classes */
.filter-input { /* Consistent input styling */ }
.filter-chip { /* Tag/chip styling */ }
.filter-dropdown { /* Dropdown containers */ }
```

**Communication**:
- Event-based with consistent naming (`filters-changed`, `channels-changed`)
- Props accept initial state and data with counts
- Debounced updates for performance

**Mobile Strategy**:
- Breakpoint at 768px (`md:` prefix)
- Bottom sheet pattern for mobile
- Horizontal scrolling for filter chips
- Progressive enhancement approach