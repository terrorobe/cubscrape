# Configuration Architecture

This directory contains the centralized configuration system for the Curated Steam Games application. All magic numbers, hardcoded values, and theme-related constants have been extracted into well-organized, documented modules.

## Structure

```
src/config/
├── index.js        # Main export file and configuration helpers
├── constants.js    # Application constants and magic numbers
├── theme.js        # Colors, visual design tokens, and styling
├── platforms.js    # Platform-specific configurations
└── README.md       # This file
```

## Modules

### constants.js
Contains all application-wide constants including:
- **TIMING**: All duration and interval values (debounce delays, animations, etc.)
- **PRICING**: Price-related constants and defaults
- **RATINGS**: Rating thresholds and filter options
- **PROGRESSIVE_LOADING**: Configuration for lazy loading
- **LAYOUT**: Responsive design breakpoints and dimensions
- **ANIMATIONS**: Transition duration scales
- **SORT_SPECS**: SQL ordering logic for different sort options

### theme.js
Manages visual design tokens:
- **RATING_COLORS**: Comprehensive rating color system with HSL values
- **PLATFORM_COLORS**: Platform-specific color schemes
- **TRANSITIONS**: CSS transition timing functions
- **OPACITY**: Opacity values for different UI states
- **Z_INDEX**: Layering system for UI elements
- **BORDERS**: Border radius design tokens
- **SHADOWS**: Shadow definitions
- Helper functions like `getRatingColor()` for dynamic styling

### platforms.js
Platform registry and utilities:
- **PLATFORMS**: Complete platform configurations (Steam, Itch.io, CrazyGames)
- **YOUTUBE_CONFIG**: YouTube-specific settings
- Helper functions for platform operations
- Platform filter options for UI components

### index.js
Main configuration export:
- Re-exports all modules for convenient access
- **CONFIG** object containing all configuration
- **DEFAULT_FILTERS**: Default filter state
- **DEFAULT_GAME_STATS**: Default statistics object
- **APP_METADATA**: Application title and descriptions
- `getConfig()` helper for safe configuration access

## Usage

### Basic Import
```javascript
// Import specific values
import { TIMING, PRICING } from '@/config/constants'
import { getRatingColor } from '@/config/theme'
import { getAvailablePlatforms } from '@/config/platforms'

// Import everything
import { CONFIG } from '@/config'
```

### Common Patterns

#### Replace Magic Numbers
```javascript
// Before
setTimeout(() => { /* ... */ }, 6000)

// After
import { TIMING } from '@/config/constants'
setTimeout(() => { /* ... */ }, TIMING.GAME_HIGHLIGHT_DURATION)
```

#### Use Theme Helpers
```javascript
// Before
if (percentage >= 80) {
  return { backgroundColor: 'hsl(120, 70%, 40%)' }
}

// After
import { getRatingColor } from '@/config/theme'
const ratingColor = getRatingColor(percentage, reviewSummary)
return { backgroundColor: ratingColor.background }
```

#### Platform Operations
```javascript
// Before
if (game.steam_url && !game.is_absorbed) {
  platforms.push({ name: 'steam', icon: 'S', url: game.steam_url })
}

// After
import { getAvailablePlatforms } from '@/config/platforms'
const platforms = getAvailablePlatforms(game)
```

## Migration Guide

When refactoring existing code:

1. **Identify hardcoded values** in your component
2. **Find the appropriate config module** (constants, theme, or platforms)
3. **Import the specific value or helper function**
4. **Replace the hardcoded value** with the configuration reference
5. **Test thoroughly** to ensure behavior remains consistent

## Best Practices

1. **Import only what you need** to keep bundles small
2. **Use helper functions** when available (e.g., `getRatingColor`)
3. **Maintain backward compatibility** when updating values
4. **Document any new additions** with JSDoc comments
5. **Group related values** logically within modules
6. **Use descriptive names** that clearly indicate the value's purpose

## Adding New Configuration

When adding new configuration values:

1. Determine the appropriate module based on the value's purpose
2. Add the value with a descriptive constant name
3. Include JSDoc documentation explaining the value's use
4. Update this README if adding new categories
5. Consider if a helper function would be useful

Example:
```javascript
/**
 * Maximum number of search results to display
 */
export const SEARCH_MAX_RESULTS = 100
```

## Future Enhancements

- Add environment-specific overrides
- Implement runtime configuration updates
- Add configuration validation
- Create configuration UI for admin users
- Support for A/B testing different values