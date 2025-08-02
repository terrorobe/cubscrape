import { ref, nextTick, computed, type Ref, type ComputedRef } from 'vue'
import { debug } from '../utils/debug'
import { TIMING } from '../config/index'
import type { Database } from 'sql.js'
import type { SortSpec } from '../types/sorting'
import type { TimeFilterConfig } from '../types/timeFilter'

// Types for the composable
export interface AppGameData {
  id: number
  name: string
  steam_app_id?: string | null
  itch_url?: string | null
  crazygames_url?: string | null
  [key: string]: unknown
}

export interface AppFilters {
  platform: string
  releaseStatus: string
  rating: string
  sortBy: string
  currency: string
  crossPlatform: boolean
  hiddenGems: boolean
  selectedTags: string[]
  tagLogic: 'and' | 'or'
  selectedChannels: string[]
  sortSpec: SortSpec
  timeFilter: TimeFilterConfig
  priceFilter: { minPrice: number; maxPrice: number }
  searchQuery: string
  searchInVideoTitles: boolean
}

export interface DeepLinkingOptions {
  filteredGames: Ref<AppGameData[]>
  filters: Ref<AppFilters>
  executeQuery: (db: Database) => void
  getDb: () => Database | null
  currentPage?: Ref<number>
  pageSize?: Ref<number>
}

// Interface for toast notifications (compatible with existing notification system)
export interface ToastNotification {
  show: (message: string, type?: 'success' | 'error' | 'info') => void
}

// Preset filter configurations for easy sharing
export interface FilterPreset {
  name: string
  description: string
  filters: Partial<AppFilters>
}

/**
 * Composable for handling deep linking functionality
 * Manages URL fragment parsing, game scrolling, highlighting, and share link generation
 */
export function useDeepLinking(options: DeepLinkingOptions) {
  const { filteredGames, filters, executeQuery, getDb, currentPage, pageSize } =
    options

  // Reactive state for highlighting
  const highlightedGameId: Ref<number | null> = ref(null)

  /**
   * Process URL fragment for deep linking to specific games
   * Supports both old and new deeplink formats:
   * - Old: #steam-123456 or #itch-game-slug
   * - New: #steam-123456-Game-Name or #itch-game-slug-Game-Name
   */
  const processDeeplink = async (): Promise<void> => {
    const { hash } = window.location
    if (!hash || hash.length <= 1) {
      return
    }

    // Wait for next frame to ensure DOM is ready
    await new Promise((resolve) => requestAnimationFrame(resolve))

    // Parse deeplink format:
    // Old format: #steam-123456 or #itch-game-slug
    // New format: #steam-123456-Game-Name or #itch-game-slug-Game-Name
    const deeplinkParts = hash.substring(1).split('-')
    if (deeplinkParts.length < 2) {
      return
    }

    const platform = deeplinkParts[0]
    let gameId

    // For Steam, the ID is numeric, so we can detect where it ends
    if (platform === 'steam') {
      // Find the first non-numeric part after platform
      let idEndIndex = 1
      while (
        idEndIndex < deeplinkParts.length &&
        /^\d+$/.test(deeplinkParts[idEndIndex])
      ) {
        idEndIndex++
      }
      gameId = deeplinkParts.slice(1, idEndIndex).join('-')
    } else {
      // For other platforms, we need to be more careful
      // The game ID could contain hyphens, so we look for a part that looks like a slugified name
      // As a heuristic, if we have more than 2 parts, assume the last parts are the name slug
      // This maintains backward compatibility with old URLs
      if (deeplinkParts.length === 2) {
        // Old format: just platform and ID
        gameId = deeplinkParts[1]
      } else {
        // New format: try to intelligently split
        // For now, assume single-part IDs (can be refined based on platform patterns)
        gameId = deeplinkParts[1]
      }
    }

    // Find and scroll to the game
    await scrollToGame(platform, gameId)
  }

  /**
   * Scroll to a specific game by platform and ID
   * Handles virtual scrolling and pagination systems
   */
  const scrollToGame = async (
    platform: string,
    gameId: string,
  ): Promise<void> => {
    // Find the game in our current filtered list
    let targetGame = null

    if (platform === 'steam') {
      targetGame = filteredGames.value.find(
        (game) => game.steam_app_id && game.steam_app_id.toString() === gameId,
      )
    } else if (platform === 'itch') {
      targetGame = filteredGames.value.find((game) =>
        game.itch_url?.includes(`${gameId}.itch.io`),
      )
    } else if (platform === 'crazygames') {
      targetGame = filteredGames.value.find((game) =>
        game.crazygames_url?.includes(`crazygames.com/game/${gameId}`),
      )
    }

    if (!targetGame) {
      debug.warn('Game not found:', platform, gameId)
      // Try to adjust filters to show the game
      await tryToShowGame(platform, gameId)
      return
    }

    // Highlight the game
    highlightGame(targetGame)

    // Wait for next tick to ensure the game card is rendered
    await nextTick()

    // Find the game card element and scroll to it
    const gameCards = document.querySelectorAll('.game-card')
    for (const card of gameCards) {
      // Find the card by checking if it contains our target game data
      const cardTitle = card.querySelector('h3')?.textContent
      if (cardTitle === targetGame.name) {
        card.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
        })
        break
      }
    }
  }

  /**
   * Attempt to show a game that's not currently visible by adjusting filters
   * This is a fallback when the game isn't found in current results
   */
  const tryToShowGame = async (
    platform: string,
    gameId: string,
  ): Promise<void> => {
    // If we can't find the game, it might be filtered out
    // Try setting platform filter and clearing others
    if (
      platform === 'steam' ||
      platform === 'itch' ||
      platform === 'crazygames'
    ) {
      const newFilters: AppFilters = {
        platform,
        releaseStatus: 'all',
        rating: '0',
        sortBy: filters.value.sortBy,
        currency: filters.value.currency,
        crossPlatform: false,
        hiddenGems: false,
        selectedTags: [],
        tagLogic: 'and',
        selectedChannels: [],
        sortSpec: null,
        timeFilter: {
          type: null,
          preset: null,
          startDate: null,
          endDate: null,
          smartLogic: null,
        },
        priceFilter: { minPrice: 0, maxPrice: 1000 },
        searchQuery: filters.value.searchQuery,
        searchInVideoTitles: filters.value.searchInVideoTitles,
      }

      // Update filters
      filters.value = { ...filters.value, ...newFilters }

      // Re-execute query with new filters
      const db = getDb()
      if (db) {
        executeQuery(db)
      }

      // Wait a moment then try again
      await new Promise((resolve) =>
        setTimeout(resolve, TIMING.SCROLL_RETRY_DELAY),
      )
      await scrollToGame(platform, gameId)
    }
  }

  /**
   * Highlight a specific game with visual effects
   * Auto-fades after configured duration
   */
  const highlightGame = (game: AppGameData): void => {
    // Clear any existing highlights
    clearHighlight()

    // Set highlighted game
    highlightedGameId.value = game.id

    // Set up auto-fade after configured duration
    setTimeout(() => {
      if (highlightedGameId.value === game.id) {
        // Start fade-out process
        highlightedGameId.value = null
      }
    }, TIMING.GAME_HIGHLIGHT_DURATION)
  }

  /**
   * Clear any active game highlighting
   */
  const clearHighlight = (): void => {
    highlightedGameId.value = null
  }

  // ============================================================================
  // SHARE LINK FUNCTIONALITY
  // ============================================================================

  /**
   * Generate a shareable link with current filter state
   * Creates a URL that includes all active filters and pagination
   */
  const shareableLink: ComputedRef<string> = computed(() => {
    const baseUrl = window.location.origin + window.location.pathname
    const url = new URL(baseUrl)

    // Add filter parameters to URL
    const currentFilters = filters.value

    // Only add non-default values to keep URLs clean
    if (currentFilters.releaseStatus !== 'all') {
      url.searchParams.set('release', currentFilters.releaseStatus)
    }
    if (currentFilters.platform !== 'all') {
      url.searchParams.set('platform', currentFilters.platform)
    }
    if (currentFilters.rating !== '0') {
      url.searchParams.set('rating', currentFilters.rating)
    }
    if (currentFilters.crossPlatform) {
      url.searchParams.set('crossPlatform', 'true')
    }
    if (currentFilters.hiddenGems) {
      url.searchParams.set('hiddenGems', 'true')
    }
    if (currentFilters.selectedTags.length > 0) {
      url.searchParams.set('tags', currentFilters.selectedTags.join(','))
      if (
        currentFilters.selectedTags.length > 1 &&
        currentFilters.tagLogic !== 'and'
      ) {
        url.searchParams.set('tagLogic', currentFilters.tagLogic)
      }
    }
    if (currentFilters.selectedChannels.length > 0) {
      url.searchParams.set(
        'channels',
        currentFilters.selectedChannels.join(','),
      )
    }
    if (currentFilters.sortBy !== 'date') {
      url.searchParams.set('sort', currentFilters.sortBy)
    }
    if (currentFilters.currency !== 'eur') {
      url.searchParams.set('currency', currentFilters.currency)
    }

    // Add time filter parameters
    if (currentFilters.timeFilter?.type) {
      url.searchParams.set('timeType', currentFilters.timeFilter.type)
      if (currentFilters.timeFilter.preset) {
        url.searchParams.set('timePreset', currentFilters.timeFilter.preset)
      }
      if (currentFilters.timeFilter.startDate) {
        url.searchParams.set('timeStart', currentFilters.timeFilter.startDate)
      }
      if (currentFilters.timeFilter.endDate) {
        url.searchParams.set('timeEnd', currentFilters.timeFilter.endDate)
      }
      if (currentFilters.timeFilter.smartLogic) {
        url.searchParams.set('timeLogic', currentFilters.timeFilter.smartLogic)
      }
    }

    // Add price filter parameters
    if (currentFilters.priceFilter) {
      if (currentFilters.priceFilter.minPrice > 0) {
        url.searchParams.set(
          'priceMin',
          currentFilters.priceFilter.minPrice.toString(),
        )
      }
      if (currentFilters.priceFilter.maxPrice < 1000) {
        url.searchParams.set(
          'priceMax',
          currentFilters.priceFilter.maxPrice.toString(),
        )
      }
    }

    // Add search parameters
    if (currentFilters.searchQuery?.trim()) {
      url.searchParams.set('search', currentFilters.searchQuery.trim())
    }
    if (currentFilters.searchInVideoTitles) {
      url.searchParams.set('searchVideos', 'true')
    }

    // Add pagination parameters
    if (currentPage?.value && currentPage.value > 1) {
      url.searchParams.set('page', currentPage.value.toString())
    }
    if (pageSize?.value && pageSize.value !== 150) {
      url.searchParams.set('size', pageSize.value.toString())
    }

    return url.toString()
  })

  /**
   * Generate a shareable link for a specific game
   * Creates a deep link that will scroll to and highlight the game
   */
  const generateGameLink = (game: AppGameData): string => {
    const baseUrl = shareableLink.value
    const url = new URL(baseUrl)

    // Generate game-specific hash fragment
    let gameFragment = ''
    if (game.steam_app_id) {
      gameFragment = `steam-${game.steam_app_id}`
    } else if (game.itch_url) {
      // Extract game slug from itch.io URL
      const match = game.itch_url.match(/(\w+)\.itch\.io/)
      if (match) {
        gameFragment = `itch-${match[1]}`
      }
    } else if (game.crazygames_url) {
      // Extract game slug from CrazyGames URL
      const match = game.crazygames_url.match(/crazygames\.com\/game\/([^/]+)/)
      if (match) {
        gameFragment = `crazygames-${match[1]}`
      }
    }

    // Add sanitized game name to make URL more descriptive
    if (gameFragment && game.name) {
      const sanitizedName = game.name
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '')

      if (sanitizedName) {
        gameFragment += `-${sanitizedName}`
      }
    }

    if (gameFragment) {
      url.hash = `#${gameFragment}`
    }

    return url.toString()
  }

  /**
   * Copy a link to the clipboard and show user feedback
   * Uses modern clipboard API with fallback for older browsers
   */
  const copyShareLink = async (
    linkToCopy?: string,
    customMessage?: string,
  ): Promise<boolean> => {
    const link = linkToCopy ?? shareableLink.value
    const _message = customMessage ?? 'Share link copied to clipboard!'

    try {
      // Modern clipboard API (preferred)
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(link)
        debug.log('✅ Link copied using clipboard API:', link)
      } else {
        // Fallback for older browsers or non-HTTPS contexts
        const textArea = document.createElement('textarea')
        textArea.value = link
        textArea.style.position = 'fixed'
        textArea.style.left = '-999999px'
        textArea.style.top = '-999999px'
        document.body.appendChild(textArea)
        textArea.focus()
        textArea.select()

        const successful = document.execCommand('copy')
        document.body.removeChild(textArea)

        if (!successful) {
          throw new Error('Failed to copy using fallback method')
        }

        debug.log('✅ Link copied using fallback method:', link)
      }

      // Show success notification (this will be handled by the caller)
      // We return true to indicate success so the caller can show appropriate feedback
      return true
    } catch (error) {
      debug.error('❌ Failed to copy link to clipboard:', error)

      // For clipboard failures, we can still show the link to the user
      // The caller should handle showing the error message
      return false
    }
  }

  /**
   * Copy the current filter state as a shareable link
   */
  const copyCurrentFiltersLink = async (): Promise<boolean> =>
    copyShareLink(shareableLink.value, 'Current filters copied to clipboard!')

  /**
   * Copy a game-specific link
   */
  const copyGameLink = async (game: AppGameData): Promise<boolean> => {
    const gameLink = generateGameLink(game)
    return copyShareLink(
      gameLink,
      `Link to "${game.name}" copied to clipboard!`,
    )
  }

  // ============================================================================
  // PRESET SHARING FUNCTIONALITY
  // ============================================================================

  /**
   * Predefined filter presets for common use cases
   */
  const filterPresets: FilterPreset[] = [
    {
      name: 'Free Games',
      description: 'Show only free games',
      filters: {
        priceFilter: { minPrice: 0, maxPrice: 0 },
        platform: 'all',
        releaseStatus: 'all',
      },
    },
    {
      name: 'New Releases',
      description: 'Games released in the last 30 days',
      filters: {
        timeFilter: {
          type: 'release',
          preset: 'last-month',
          startDate: null,
          endDate: null,
          smartLogic: null,
        },
        releaseStatus: 'released',
      },
    },
    {
      name: 'Hidden Gems',
      description: 'Discover underrated games',
      filters: {
        hiddenGems: true,
        rating: '70',
      },
    },
    {
      name: 'High Rated',
      description: 'Games with excellent reviews',
      filters: {
        rating: '90',
        releaseStatus: 'released',
      },
    },
    {
      name: 'Steam Games',
      description: 'Browse Steam catalog',
      filters: {
        platform: 'steam',
        releaseStatus: 'all',
      },
    },
  ]

  /**
   * Generate a shareable link for a specific preset
   */
  const generatePresetLink = (preset: FilterPreset): string => {
    const baseUrl = window.location.origin + window.location.pathname
    const url = new URL(baseUrl)

    // Apply preset filters to URL parameters
    const presetFilters = preset.filters

    Object.entries(presetFilters).forEach(([key, value]) => {
      if (value === null || value === undefined) {
        return
      }

      switch (key) {
        case 'platform':
          if (value !== 'all') {
            url.searchParams.set('platform', value as string)
          }
          break
        case 'releaseStatus':
          if (value !== 'all') {
            url.searchParams.set('release', value as string)
          }
          break
        case 'rating':
          if (value !== '0') {
            url.searchParams.set('rating', value as string)
          }
          break
        case 'hiddenGems':
          if (value) {
            url.searchParams.set('hiddenGems', 'true')
          }
          break
        case 'crossPlatform':
          if (value) {
            url.searchParams.set('crossPlatform', 'true')
          }
          break
        case 'priceFilter': {
          const priceFilter = value as {
            minPrice: number
            maxPrice: number
          }
          if (priceFilter.minPrice > 0) {
            url.searchParams.set('priceMin', priceFilter.minPrice.toString())
          }
          if (priceFilter.maxPrice < 1000) {
            url.searchParams.set('priceMax', priceFilter.maxPrice.toString())
          }
          break
        }
        case 'timeFilter': {
          const timeFilter = value as { type: string; preset: string }
          if (timeFilter.type) {
            url.searchParams.set('timeType', timeFilter.type)
          }
          if (timeFilter.preset) {
            url.searchParams.set('timePreset', timeFilter.preset)
          }
          break
        }
      }
    })

    return url.toString()
  }

  /**
   * Copy a preset link to clipboard
   */
  const copyPresetLink = async (preset: FilterPreset): Promise<boolean> => {
    const presetLink = generatePresetLink(preset)
    return copyShareLink(
      presetLink,
      `"${preset.name}" preset link copied to clipboard!`,
    )
  }

  // Return enhanced composable interface
  return {
    // Original functionality
    highlightedGameId,
    processDeeplink,
    scrollToGame,
    highlightGame,
    clearHighlight,

    // Share link functionality
    shareableLink,
    generateGameLink,
    copyShareLink,
    copyCurrentFiltersLink,
    copyGameLink,

    // Preset functionality
    filterPresets,
    generatePresetLink,
    copyPresetLink,
  }
}
