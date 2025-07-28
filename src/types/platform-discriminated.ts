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
  price_final?: number
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
  price_final?: number
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
  price_final?: never
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
    price_final?: number
    currency_support: ['EUR', 'USD']
  }
  itch: {
    price_usd?: number
    price_final?: number
    currency_support: ['USD']
  }
  crazygames: {
    price_eur?: never
    price_usd?: never
    price_final?: never
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
 * Type-safe platform URL extractor
 */
export function getPlatformUrl<T extends PlatformGameData>(
  game: T,
): T extends SteamGameData
  ? { platform: 'steam'; url: string; app_id: string }
  : T extends ItchGameData
    ? { platform: 'itch'; url: string }
    : T extends CrazyGamesData
      ? { platform: 'crazygames'; url: string }
      : never {
  if (isSteamGame(game)) {
    return {
      platform: 'steam',
      url: game.steam_url,
      app_id: game.steam_app_id,
    } as any
  }

  if (isItchGame(game)) {
    return {
      platform: 'itch',
      url: game.itch_url,
    } as any
  }

  if (isCrazyGamesGame(game)) {
    return {
      platform: 'crazygames',
      url: game.crazygames_url,
    } as any
  }

  throw new Error(`Unknown platform: ${(game as any).platform}`)
}

/**
 * Type-safe pricing extractor with currency support
 */
export function getPlatformPricing<T extends PlatformGameData>(
  game: T,
): T extends SteamGameData
  ? {
      currencies: ['EUR', 'USD']
      price_eur?: number
      price_usd?: number
      price_final?: number
    }
  : T extends ItchGameData
    ? { currencies: ['USD']; price_usd?: number; price_final?: number }
    : T extends CrazyGamesData
      ? { currencies: never; is_free: true }
      : never {
  if (isSteamGame(game)) {
    return {
      currencies: ['EUR', 'USD'],
      price_eur: game.price_eur,
      price_usd: game.price_usd,
      price_final: game.price_final,
    } as any
  }

  if (isItchGame(game)) {
    return {
      currencies: ['USD'],
      price_usd: game.price_usd,
      price_final: game.price_final,
    } as any
  }

  if (isCrazyGamesGame(game)) {
    return {
      currencies: [] as never,
      is_free: true,
    } as any
  }

  throw new Error(`Unknown platform: ${(game as any).platform}`)
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
  validatePlatformGame(data: any): data is PlatformGameData {
    if (data.platform === 'steam') {
      return this.validateSteam(data)
    }
    if (data.platform === 'itch') {
      return this.validateItch(data)
    }
    if (data.platform === 'crazygames') {
      return this.validateCrazyGames(data)
    }
    return false
  },
} as const
