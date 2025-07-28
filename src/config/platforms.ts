/**
 * Platform-specific configurations and registry
 * @module config/platforms
 */

/**
 * Platform type identifier
 */
export type PlatformId = 'steam' | 'itch' | 'crazygames'

/**
 * Platform color configuration
 */
interface PlatformColors {
  primary: string
  secondary: string
  accent: string
}

/**
 * Platform feature flags
 */
interface PlatformFeatures {
  reviews: boolean
  pricing: boolean
  tags: boolean
  releaseDate: boolean
}

/**
 * Complete platform configuration
 */
export interface PlatformConfig {
  id: PlatformId
  name: string
  displayName: string
  icon: string
  urlPattern: RegExp
  storeUrlPrefix: string
  colors: PlatformColors
  features: PlatformFeatures
  urlField?: string
}

/**
 * Available platform with URL
 */
export interface AvailablePlatform extends PlatformConfig {
  url: string
}

/**
 * Game object interface for platform operations
 */
interface GameForPlatforms {
  steam_url?: string
  itch_url?: string
  crazygames_url?: string
  is_absorbed?: boolean
  platform?: string
}

/**
 * Platform registry with metadata and configuration
 */
export const PLATFORMS: Record<PlatformId, PlatformConfig> = {
  steam: {
    id: 'steam',
    name: 'Steam',
    displayName: 'Steam',
    icon: 'S',
    urlPattern: /^https?:\/\/(store\.)?steampowered\.com/,
    storeUrlPrefix: 'https://store.steampowered.com/app/',
    urlField: 'steam_url',
    colors: {
      primary: '#1b2838',
      secondary: '#66c0f4',
      accent: '#00aeff',
    },
    features: {
      reviews: true,
      pricing: true,
      tags: true,
      releaseDate: true,
    },
  },

  itch: {
    id: 'itch',
    name: 'Itch.io',
    displayName: 'Itch.io',
    icon: 'I',
    urlPattern: /^https?:\/\/.*\.itch\.io/,
    storeUrlPrefix: 'https://itch.io/',
    urlField: 'itch_url',
    colors: {
      primary: '#fa5c5c',
      secondary: '#ff2449',
      accent: '#fa5c5c',
    },
    features: {
      reviews: false,
      pricing: true,
      tags: true,
      releaseDate: true,
    },
  },

  crazygames: {
    id: 'crazygames',
    name: 'CrazyGames',
    displayName: 'CrazyGames',
    icon: 'C',
    urlPattern: /^https?:\/\/(www\.)?crazygames\.com/,
    storeUrlPrefix: 'https://www.crazygames.com/game/',
    urlField: 'crazygames_url',
    colors: {
      primary: '#7b2ff7',
      secondary: '#9747ff',
      accent: '#7b2ff7',
    },
    features: {
      reviews: false,
      pricing: false,
      tags: true,
      releaseDate: false,
    },
  },
} as const

/**
 * YouTube platform configuration
 */
export const YOUTUBE_CONFIG = {
  urlPatterns: [
    /^https?:\/\/(www\.)?youtube\.com\/watch\?v=/,
    /^https?:\/\/youtu\.be\//,
  ],
  embedUrlPrefix: 'https://www.youtube.com/embed/',
  thumbnailUrl: (videoId: string): string =>
    `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`,
} as const

/**
 * Platform filter option for UI
 */
export interface PlatformFilterOption {
  value: string
  label: string
  icon?: string
}

/**
 * Platform filter options for UI
 */
export const PLATFORM_FILTER_OPTIONS: readonly PlatformFilterOption[] = [
  { value: 'all', label: 'All Platforms' },
  { value: 'steam', label: 'Steam', icon: 'S' },
  { value: 'itch', label: 'Itch.io', icon: 'I' },
  { value: 'crazygames', label: 'CrazyGames', icon: 'C' },
  { value: 'other', label: 'Other Platforms' },
] as const

/**
 * Get platform configuration by ID
 */
export function getPlatformConfig(platformId: string): PlatformConfig | null {
  return PLATFORMS[platformId as PlatformId] || null
}

/**
 * Get platform display name
 */
export function getPlatformDisplayName(platformId: string): string {
  const platform = getPlatformConfig(platformId)
  return platform?.displayName || platformId
}

/**
 * Get platform icon
 */
export function getPlatformIcon(platformId: string): string {
  const platform = getPlatformConfig(platformId)
  return platform?.icon || platformId.charAt(0).toUpperCase()
}

/**
 * Check if a URL matches a platform's pattern
 */
export function isPlatformUrl(url: string, platformId: string): boolean {
  const platform = getPlatformConfig(platformId)
  return platform?.urlPattern?.test(url) || false
}

/**
 * Get available platforms for a game
 */
export function getAvailablePlatforms(
  game: GameForPlatforms,
): AvailablePlatform[] {
  const platforms: AvailablePlatform[] = []

  if (game.steam_url && !game.is_absorbed) {
    platforms.push({
      ...PLATFORMS.steam,
      url: game.steam_url,
    })
  }

  if (game.itch_url) {
    platforms.push({
      ...PLATFORMS.itch,
      url: game.itch_url,
    })
  }

  if (game.crazygames_url) {
    platforms.push({
      ...PLATFORMS.crazygames,
      url: game.crazygames_url,
    })
  }

  return platforms
}

/**
 * Extract YouTube video ID from URL
 */
export function extractYouTubeVideoId(url: string): string | null {
  // Check watch URL format
  const watchMatch = url.match(/[?&]v=([^&]+)/)
  if (watchMatch) {
    return watchMatch[1]
  }

  // Check short URL format
  const shortMatch = url.match(/youtu\.be\/([^?]+)/)
  if (shortMatch) {
    return shortMatch[1]
  }

  return null
}

// Type exports for external use
export type PlatformsConfig = typeof PLATFORMS
export type YouTubeConfig = typeof YOUTUBE_CONFIG
