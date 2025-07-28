/**
 * Central configuration module that exports all config modules
 * @module config
 */

// Export all configuration modules
export * from './constants.js'
export * from './theme.js'
export * from './platforms.js'

// Re-export as named groups for convenient access
import * as constants from './constants.js'
import * as theme from './theme.js'
import * as platforms from './platforms.js'

export const CONFIG = {
  ...constants,
  theme,
  platforms,
}

/**
 * Default filter configuration
 */
export const DEFAULT_FILTERS = {
  channel: '',
  selectedChannels: [],
  tag: '',
  selectedTags: [],
  tagLogic: 'and',
  releaseStatus: 'all',
  platform: 'all',
  rating: '0',
  priceFilter: {
    minPrice: constants.PRICING.MIN_PRICE,
    maxPrice: constants.PRICING.DEFAULT_MAX_PRICE,
    includeFree: true,
  },
  sortBy: 'relevance',
  sortSpec: 'relevance',
}

/**
 * Default game stats
 */
export const DEFAULT_GAME_STATS = {
  totalGames: 0,
  freeGames: 0,
  maxPrice: constants.PRICING.DEFAULT_MAX_PRICE,
}

/**
 * Application metadata
 */
export const APP_METADATA = {
  title: 'Curated Steam Games',
  subtitle: 'Discovered from YouTube Gaming Channels',
  description: 'Browse Steam games featured by YouTube gaming channels',
}

/**
 * Get configuration value with fallback
 * @param {string} path - Dot-notation path to config value
 * @param {*} defaultValue - Default value if path not found
 * @returns {*} Configuration value or default
 */
export function getConfig(path, defaultValue) {
  const keys = path.split('.')
  let value = CONFIG

  for (const key of keys) {
    if (value && typeof value === 'object' && key in value) {
      value = value[key]
    } else {
      return defaultValue
    }
  }

  return value
}
