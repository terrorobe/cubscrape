/**
 * Advanced discriminated union types for platform-specific game data
 * Provides compile-time type safety for platform-specific properties and operations
 */

import type { PlatformId } from './database.js'

/**
 * Base game properties shared across all platforms
 */
interface BaseGameData {
  id: number
  game_key: string
  name: string
  coming_soon: boolean
  is_early_access: boolean
  is_demo: boolean
  is_free: boolean
  release_date?: string
  planned_release_date?: string
  release_date_sortable?: number
  header_image?: string
  last_updated?: string
  video_count: number
  latest_video_date?: string
  unique_channels: string[]
  genres: string[]
  tags: string[]
  developers: string[]
  publishers: string[]
  is_absorbed: boolean
  absorbed_into?: string
}

/**
 * Steam-specific game data with Steam platform features
 */
export interface SteamGameData extends BaseGameData {
  platform: 'steam'
  steam_app_id: string
  steam_url: string
  // Steam-specific pricing (supports multiple currencies)
  price_eur?: number
  price_usd?: number
  // Steam review system
  positive_review_percentage?: number
  review_count?: number
  review_summary?: string
  review_summary_priority?: number
  recent_review_percentage?: number
  recent_review_count?: number
  recent_review_summary?: string
  insufficient_reviews: boolean
  review_tooltip?: string
  is_inferred_summary: boolean
  // Steam demo support
  demo_steam_app_id?: string
  demo_steam_url?: string
  // Other platforms are optional
  itch_url?: string
  crazygames_url?: string
}

/**
 * Itch.io-specific game data with Itch platform features
 */
export interface ItchGameData extends BaseGameData {
  platform: 'itch'
  itch_url: string
  // Itch pricing (typically USD-based)
  price_usd?: number
  // No native review system on Itch
  positive_review_percentage?: never
  review_count?: never
  review_summary?: never
  review_summary_priority?: never
  recent_review_percentage?: never
  recent_review_count?: never
  recent_review_summary?: never
  insufficient_reviews: false
  review_tooltip?: never
  is_inferred_summary: false
  // No demo system
  demo_steam_app_id?: never
  demo_steam_url?: never
  // Steam integration possible
  steam_app_id?: string
  steam_url?: string
  price_eur?: number
  // CrazyGames unlikely but possible
  crazygames_url?: string
}

/**
 * CrazyGames-specific game data with CrazyGames platform features
 */
export interface CrazyGamesData extends BaseGameData {
  platform: 'crazygames'
  crazygames_url: string
  // Free-to-play web games only
  is_free: true
  price_eur?: never
  price_usd?: never
  // No review system
  positive_review_percentage?: never
  review_count?: never
  review_summary?: never
  review_summary_priority?: never
  recent_review_percentage?: never
  recent_review_count?: never
  recent_review_summary?: never
  insufficient_reviews: false
  review_tooltip?: never
  is_inferred_summary: false
  // No demo system (games are already playable)
  demo_steam_app_id?: never
  demo_steam_url?: never
  // May have Steam versions
  steam_app_id?: string
  steam_url?: string
  itch_url?: string
}

/**
 * Discriminated union of all platform-specific game data
 */
export type PlatformGameData = SteamGameData | ItchGameData | CrazyGamesData

/**
 * Platform-specific URL mappings
 */
export type PlatformUrls = {
  steam: { steam_url: string; steam_app_id: string }
  itch: { itch_url: string }
  crazygames: { crazygames_url: string }
}

/**
 * Platform-specific pricing information
 */
export type PlatformPricing = {
  steam: {
    price_eur?: number
    price_usd?: number
    currency_support: ['EUR', 'USD']
  }
  itch: {
    price_usd?: number
    currency_support: ['USD']
  }
  crazygames: {
    price_eur?: never
    price_usd?: never
    currency_support: never
    is_free: true
  }
}

/**
 * Platform-specific review systems
 */
export type PlatformReviews = {
  steam: {
    has_reviews: true
    positive_review_percentage?: number
    review_count?: number
    review_summary?: string
    recent_reviews: boolean
  }
  itch: {
    has_reviews: false
    positive_review_percentage?: never
    review_count?: never
    review_summary?: never
    recent_reviews: false
  }
  crazygames: {
    has_reviews: false
    positive_review_percentage?: never
    review_count?: never
    review_summary?: never
    recent_reviews: false
  }
}

/**
 * Platform feature support matrix
 */
export type PlatformFeatures = {
  steam: {
    pricing: true
    reviews: true
    demos: true
    early_access: true
    coming_soon: true
    multi_currency: true
  }
  itch: {
    pricing: true
    reviews: false
    demos: false
    early_access: true
    coming_soon: true
    multi_currency: false
  }
  crazygames: {
    pricing: false
    reviews: false
    demos: false
    early_access: false
    coming_soon: false
    multi_currency: false
  }
}

/**
 * Type-safe platform feature checker
 */
export function hasPlatformFeature<
  P extends PlatformId,
  F extends keyof PlatformFeatures[P],
>(platform: P, feature: F): PlatformFeatures[P][F] {
  const features: PlatformFeatures = {
    steam: {
      pricing: true,
      reviews: true,
      demos: true,
      early_access: true,
      coming_soon: true,
      multi_currency: true,
    },
    itch: {
      pricing: true,
      reviews: false,
      demos: false,
      early_access: true,
      coming_soon: true,
      multi_currency: false,
    },
    crazygames: {
      pricing: false,
      reviews: false,
      demos: false,
      early_access: false,
      coming_soon: false,
      multi_currency: false,
    },
  }

  return features[platform][feature]
}

/**
 * Type guards for platform-specific game data
 */
export function isSteamGame(game: PlatformGameData): game is SteamGameData {
  return game.platform === 'steam'
}

export function isItchGame(game: PlatformGameData): game is ItchGameData {
  return game.platform === 'itch'
}

export function isCrazyGamesGame(
  game: PlatformGameData,
): game is CrazyGamesData {
  return game.platform === 'crazygames'
}

/**
 * Return types for platform URL extraction
 */
type SteamUrlResult = { platform: 'steam'; url: string; app_id: string }
type ItchUrlResult = { platform: 'itch'; url: string }
type CrazyGamesUrlResult = { platform: 'crazygames'; url: string }

/**
 * Type-safe platform URL extractor - function overloads for better type inference
 */
export function getPlatformUrl(game: SteamGameData): SteamUrlResult
export function getPlatformUrl(game: ItchGameData): ItchUrlResult
export function getPlatformUrl(game: CrazyGamesData): CrazyGamesUrlResult
export function getPlatformUrl(
  game: PlatformGameData,
): SteamUrlResult | ItchUrlResult | CrazyGamesUrlResult {
  if (isSteamGame(game)) {
    return {
      platform: 'steam',
      url: game.steam_url,
      app_id: game.steam_app_id,
    }
  }

  if (isItchGame(game)) {
    return {
      platform: 'itch',
      url: game.itch_url,
    }
  }

  if (isCrazyGamesGame(game)) {
    return {
      platform: 'crazygames',
      url: game.crazygames_url,
    }
  }

  // This should never happen due to discriminated union, but we need exhaustive checking
  // TypeScript ensures all cases are handled above
  throw new Error(
    `Unknown platform: ${(game as { platform: string }).platform}`,
  )
}

/**
 * Return types for platform pricing extraction
 */
type SteamPricingResult = {
  currencies: ['EUR', 'USD']
  price_eur?: number
  price_usd?: number
}
type ItchPricingResult = {
  currencies: ['USD']
  price_usd?: number
}
type CrazyGamesPricingResult = {
  currencies: never
  is_free: true
}

/**
 * Type-safe pricing extractor with currency support - function overloads for better type inference
 */
export function getPlatformPricing(game: SteamGameData): SteamPricingResult
export function getPlatformPricing(game: ItchGameData): ItchPricingResult
export function getPlatformPricing(
  game: CrazyGamesData,
): CrazyGamesPricingResult
export function getPlatformPricing(
  game: PlatformGameData,
): SteamPricingResult | ItchPricingResult | CrazyGamesPricingResult {
  if (isSteamGame(game)) {
    return {
      currencies: ['EUR', 'USD'],
      price_eur: game.price_eur,
      price_usd: game.price_usd,
    }
  }

  if (isItchGame(game)) {
    return {
      currencies: ['USD'],
      price_usd: game.price_usd,
    }
  }

  if (isCrazyGamesGame(game)) {
    return {
      currencies: [] as never,
      is_free: true,
    }
  }

  // This should never happen due to discriminated union, but we need exhaustive checking
  // TypeScript ensures all cases are handled above
  throw new Error(
    `Unknown platform: ${(game as { platform: string }).platform}`,
  )
}

/**
 * Cross-platform game collection type
 */
export interface CrossPlatformGame {
  primary: PlatformGameData
  alternates: Partial<Record<PlatformId, PlatformGameData>>
  unified_name: string
  all_platforms: PlatformId[]
}

/**
 * Platform-specific component props helper
 */
export type PlatformComponentProps<P extends PlatformId> = {
  game: Extract<PlatformGameData, { platform: P }>
  features: PlatformFeatures[P]
}

/**
 * Utility type to extract platform-specific properties
 */
export type ExtractPlatformProps<
  T extends PlatformGameData,
  K extends keyof T,
> = Pick<T, K>

/**
 * Platform validation utilities
 */
export const PlatformValidation = {
  /**
   * Validate Steam-specific data
   */
  validateSteam(data: Partial<SteamGameData>): data is SteamGameData {
    return !!(
      data.platform === 'steam' &&
      data.steam_url &&
      data.steam_app_id &&
      data.name &&
      typeof data.is_free === 'boolean'
    )
  },

  /**
   * Validate Itch-specific data
   */
  validateItch(data: Partial<ItchGameData>): data is ItchGameData {
    return !!(
      data.platform === 'itch' &&
      data.itch_url &&
      data.name &&
      typeof data.is_free === 'boolean'
    )
  },

  /**
   * Validate CrazyGames-specific data
   */
  validateCrazyGames(data: Partial<CrazyGamesData>): data is CrazyGamesData {
    return !!(
      data.platform === 'crazygames' &&
      data.crazygames_url &&
      data.name &&
      data.is_free === true
    )
  },

  /**
   * Validate any platform game data
   */
  validatePlatformGame(data: unknown): data is PlatformGameData {
    // Type guard: check if data is an object with a platform property
    if (typeof data !== 'object' || data === null || !('platform' in data)) {
      return false
    }

    const gameData = data as { platform: unknown }

    if (gameData.platform === 'steam') {
      return this.validateSteam({ ...gameData, platform: 'steam' as const })
    }
    if (gameData.platform === 'itch') {
      return this.validateItch({ ...gameData, platform: 'itch' as const })
    }
    if (gameData.platform === 'crazygames') {
      return this.validateCrazyGames({
        ...gameData,
        platform: 'crazygames' as const,
      })
    }
    return false
  },
} as const
