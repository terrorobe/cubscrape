/**
 * Platform-specific configurations and registry
 * @module config/platforms
 */

/**
 * Platform registry with metadata and configuration
 */
export const PLATFORMS = {
  steam: {
    id: 'steam',
    name: 'Steam',
    displayName: 'Steam',
    icon: 'S',
    urlPattern: /^https?:\/\/(store\.)?steampowered\.com/,
    storeUrlPrefix: 'https://store.steampowered.com/app/',
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
}

/**
 * YouTube platform configuration
 */
export const YOUTUBE_CONFIG = {
  urlPatterns: [
    /^https?:\/\/(www\.)?youtube\.com\/watch\?v=/,
    /^https?:\/\/youtu\.be\//,
  ],
  embedUrlPrefix: 'https://www.youtube.com/embed/',
  thumbnailUrl: (videoId) =>
    `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`,
}

/**
 * Get platform configuration by ID
 * @param {string} platformId - The platform identifier
 * @returns {Object|null} Platform configuration or null if not found
 */
export function getPlatformConfig(platformId) {
  return PLATFORMS[platformId] || null
}

/**
 * Get platform display name
 * @param {string} platformId - The platform identifier
 * @returns {string} Display name or the platformId if not found
 */
export function getPlatformDisplayName(platformId) {
  const platform = getPlatformConfig(platformId)
  return platform?.displayName || platformId
}

/**
 * Get platform icon
 * @param {string} platformId - The platform identifier
 * @returns {string} Icon character or first letter of platform name
 */
export function getPlatformIcon(platformId) {
  const platform = getPlatformConfig(platformId)
  return platform?.icon || platformId.charAt(0).toUpperCase()
}

/**
 * Check if a URL matches a platform's pattern
 * @param {string} url - The URL to check
 * @param {string} platformId - The platform identifier
 * @returns {boolean} True if URL matches platform pattern
 */
export function isPlatformUrl(url, platformId) {
  const platform = getPlatformConfig(platformId)
  return platform?.urlPattern?.test(url) || false
}

/**
 * Get available platforms for a game
 * @param {Object} game - The game object
 * @returns {Array} Array of platform configurations
 */
export function getAvailablePlatforms(game) {
  const platforms = []

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
 * @param {string} url - YouTube URL
 * @returns {string|null} Video ID or null if not a valid YouTube URL
 */
export function extractYouTubeVideoId(url) {
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

/**
 * Platform filter options for UI
 */
export const PLATFORM_FILTER_OPTIONS = [
  { value: 'all', label: 'All Platforms' },
  { value: 'steam', label: 'Steam', icon: 'S' },
  { value: 'itch', label: 'Itch.io', icon: 'I' },
  { value: 'crazygames', label: 'CrazyGames', icon: 'C' },
  { value: 'other', label: 'Other Platforms' },
]
