/**
 * Central configuration module that exports all config modules
 * @module config
 */

// Export all configuration modules
export * from './constants'
export * from './theme'
export * from './platforms'

// Re-export as named groups for convenient access
import * as constants from './constants'
import * as theme from './theme'
import * as platforms from './platforms'

export const CONFIG = {
  ...constants,
  theme,
  platforms,
} as const

/**
 * Tag logic type for filters
 */
export type TagLogic = 'and' | 'or'

/**
 * Release status filter options
 */
export type ReleaseStatus = 'all' | 'released' | 'unreleased' | 'early-access'

/**
 * Platform filter options
 */
export type PlatformFilter = 'all' | 'steam' | 'itch' | 'crazygames' | 'other'

/**
 * Price filter configuration
 */
export interface PriceFilter {
  minPrice: number
  maxPrice: number
  includeFree: boolean
}

/**
 * Filter configuration interface
 */
export interface FilterConfig {
  channel: string
  selectedChannels: string[]
  tag: string
  selectedTags: string[]
  tagLogic: TagLogic
  releaseStatus: ReleaseStatus
  platform: PlatformFilter
  rating: string
  priceFilter: PriceFilter
  sortBy: string
  sortSpec: string
}

/**
 * Game statistics interface
 */
export interface GameStats {
  totalGames: number
  freeGames: number
  maxPrice: number
}

/**
 * Application metadata interface
 */
export interface AppMetadata {
  title: string
  subtitle: string
  description: string
}

/**
 * Default filter configuration
 */
export const DEFAULT_FILTERS: FilterConfig = {
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
export const DEFAULT_GAME_STATS: GameStats = {
  totalGames: 0,
  freeGames: 0,
  maxPrice: constants.PRICING.DEFAULT_MAX_PRICE,
}

/**
 * Application metadata
 */
export const APP_METADATA: AppMetadata = {
  title: 'Curated Steam Games',
  subtitle: 'Discovered from YouTube Gaming Channels',
  description: 'Browse Steam games featured by YouTube gaming channels',
}

/**
 * Get configuration value with fallback
 */
export function getConfig<T = any>(path: string, defaultValue: T): T {
  const keys = path.split('.')
  let value: any = CONFIG

  for (const key of keys) {
    if (value && typeof value === 'object' && key in value) {
      value = value[key]
    } else {
      return defaultValue
    }
  }

  return value
}

// Type exports for external use
export type ConfigType = typeof CONFIG
