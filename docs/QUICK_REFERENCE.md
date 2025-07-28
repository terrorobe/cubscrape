# Quick Reference

## Essential Commands

### Development
```bash
# Start development
npm run dev

# Python scraper
cubscrape cron
cubscrape backfill --channel olexa --max-new 5

# Linting
uv run ruff check --fix
npx eslint src/ --fix

# Type checking
npx tsc --noEmit
npm run type-check
```

### Production
```bash
# Build for deployment
npm run build
cubscrape build-db
```

## Key File Locations

### Data & Database
- `data/games.db` - Primary SQLite database
- `data/steam_games.json` - Steam game metadata  
- `data/videos-{channel}.json` - YouTube video data
- `data/schema.sql` - Database schema

### Configuration
- `src/config/constants.ts` - UI limits, thresholds
- `src/config/theme.ts` - Colors, spacing, timing
- `src/config/platforms.ts` - Platform-specific configs
- `pyproject.toml` - Python dependencies
- `package.json` - Node.js dependencies

### Core Components
- `src/App.vue` - Main application
- `src/components/GameFilters.vue` - Filter orchestrator
- `src/components/GameCard.vue` - Game display
- `src/utils/databaseManager.ts` - SQLite operations

## Common Data Operations

### JSON Analysis (Use jq, not grep)
```bash
# Find game by ID
jq '.games["2651220"]' data/steam_games.json

# Find games by name
jq -r '.games | to_entries[] | select(.value.name | contains("Blacksmith")) | .key + ": " + .value.name' data/steam_games.json

# Count total games
jq '.games | length' data/steam_games.json
```

### Database Schema
```sql
-- Main tables
games              -- Game metadata (Steam, Itch, CrazyGames)
game_videos        -- Video-to-game relationships

-- Key columns
steam_app_id       -- Steam game identifier
platform           -- 'steam' | 'itch' | 'crazygames'  
positive_review_percentage  -- Review rating
price_final        -- Price in cents
is_free            -- Boolean free flag
```

## TypeScript Patterns

### Component Props
```typescript
interface Props {
  games: Game[]
  showVideo?: boolean
}
const props = defineProps<Props>()
```

### Database Types
```typescript
interface GameRecord {
  id: number
  name: string
  platform: 'steam' | 'itch' | 'crazygames'
  steam_app_id?: string
  positive_review_percentage?: number
}
```

## Debugging Tips

### Performance Issues
- Check `src/utils/performanceMonitor.ts` for metrics
- Database queries logged in browser console
- Use Vue DevTools for component performance

### Data Issues
```bash
# Check data quality
cubscrape data-quality

# Test single game fetch
cubscrape single-app --app-id 3586420

# Interactive game resolution
cubscrape infer-games
```

### Build Issues
- TypeScript errors: `npx tsc --noEmit`
- Vue component errors: `npx vue-tsc --noEmit`
- ESLint issues: `npx eslint src/ --fix`

## URLs & Deployment

- **Production**: https://terrorobe.github.io/cubscrape/
- **CI/CD**: `.github/workflows/pages-with-db.yml`
