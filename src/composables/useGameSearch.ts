import { ref, watch, onUnmounted, type Ref } from 'vue'
import { debug } from '../utils/debug'

/**
 * Search configuration interface
 */
export interface SearchConfig {
  debounceDelay?: number
}

/**
 * Search state interface
 */
export interface SearchState {
  searchQuery: string
  searchInVideoTitles: boolean
  debouncedSearchQuery: string
}

/**
 * Search SQL query parameters interface
 */
export interface SearchQueryParams {
  query: string
  params: (string | number)[]
}

/**
 * Return type for the useGameSearch composable
 */
export interface UseGameSearchReturn {
  // Reactive state
  searchQuery: Ref<string>
  searchInVideoTitles: Ref<boolean>
  debouncedSearchQuery: Ref<string>

  // Methods
  buildSearchQuery: (
    searchTerm: string,
    searchInVideoTitles: boolean,
  ) => SearchQueryParams
  resetSearch: () => void

  // State getters
  hasActiveSearch: () => boolean
  getSearchState: () => SearchState
  setSearchState: (state: Partial<SearchState>) => void
}

/**
 * Game search composable that handles search state management and query building
 *
 * Features:
 * - Debounced search input handling
 * - Search in game names and/or video titles
 * - SQL query building for search filters
 * - Proper cleanup on component unmount
 *
 * @param config - Optional configuration for search behavior
 * @param onSearchChange - Callback function called when search state changes
 * @returns Search state and methods
 */
export function useGameSearch(
  config: SearchConfig = {},
  onSearchChange?: (state: SearchState) => void,
): UseGameSearchReturn {
  const { debounceDelay = 300 } = config

  // Reactive search state
  const searchQuery = ref('')
  const searchInVideoTitles = ref(false)
  const debouncedSearchQuery = ref('')

  // Debounce timer reference
  let searchDebounceTimer: NodeJS.Timeout | null = null

  /**
   * Cleanup debounce timer
   */
  const clearDebounceTimer = (): void => {
    if (searchDebounceTimer) {
      clearTimeout(searchDebounceTimer)
      searchDebounceTimer = null
    }
  }

  /**
   * Update debounced search query with debouncing
   */
  const updateDebouncedQuery = (newQuery: string): void => {
    clearDebounceTimer()

    searchDebounceTimer = setTimeout(() => {
      debouncedSearchQuery.value = newQuery

      // Notify parent component of search changes
      if (onSearchChange) {
        onSearchChange({
          searchQuery: newQuery,
          searchInVideoTitles: searchInVideoTitles.value,
          debouncedSearchQuery: newQuery,
        })
      }

      debug.log('Search query debounced:', newQuery)
    }, debounceDelay)
  }

  // Watch for search query changes and debounce
  watch(searchQuery, (newQuery) => {
    debug.log('Search query changed:', newQuery)
    updateDebouncedQuery(newQuery)
  })

  // Watch for search in video titles toggle
  watch(searchInVideoTitles, (newValue) => {
    debug.log('Search in video titles changed:', newValue)

    // Notify parent component immediately for toggle changes
    if (onSearchChange) {
      onSearchChange({
        searchQuery: searchQuery.value,
        searchInVideoTitles: newValue,
        debouncedSearchQuery: debouncedSearchQuery.value,
      })
    }
  })

  /**
   * Build SQL query components for search filtering
   *
   * @param searchTerm - The search term to filter by
   * @param searchInVideoTitles - Whether to include video title search
   * @returns Object with SQL query fragment and parameters
   */
  const buildSearchQuery = (
    searchTerm: string,
    searchInVideoTitles: boolean,
  ): SearchQueryParams => {
    const trimmedTerm = searchTerm.trim()

    if (!trimmedTerm) {
      return { query: '', params: [] }
    }

    if (searchInVideoTitles) {
      // Search in both game names and video titles using LIKE
      return {
        query: ' AND (g.name LIKE ? OR gv.video_title LIKE ?)',
        params: [`%${trimmedTerm}%`, `%${trimmedTerm}%`],
      }
    } else {
      // Search only in game names using LIKE
      return {
        query: ' AND g.name LIKE ?',
        params: [`%${trimmedTerm}%`],
      }
    }
  }

  /**
   * Reset all search state
   */
  const resetSearch = (): void => {
    clearDebounceTimer()
    searchQuery.value = ''
    searchInVideoTitles.value = false
    debouncedSearchQuery.value = ''

    debug.log('Search state reset')
  }

  /**
   * Check if there's an active search
   */
  const hasActiveSearch = (): boolean =>
    debouncedSearchQuery.value.trim().length > 0

  /**
   * Get current search state
   */
  const getSearchState = (): SearchState => ({
    searchQuery: searchQuery.value,
    searchInVideoTitles: searchInVideoTitles.value,
    debouncedSearchQuery: debouncedSearchQuery.value,
  })

  /**
   * Set search state (useful for URL state restoration)
   */
  const setSearchState = (state: Partial<SearchState>): void => {
    if (state.searchQuery !== undefined) {
      searchQuery.value = state.searchQuery
    }
    if (state.searchInVideoTitles !== undefined) {
      searchInVideoTitles.value = state.searchInVideoTitles
    }
    if (state.debouncedSearchQuery !== undefined) {
      debouncedSearchQuery.value = state.debouncedSearchQuery
    }

    debug.log('Search state updated:', state)
  }

  // Cleanup on component unmount
  onUnmounted(() => {
    clearDebounceTimer()
    debug.log('Search composable cleanup completed')
  })

  return {
    // Reactive state
    searchQuery,
    searchInVideoTitles,
    debouncedSearchQuery,

    // Methods
    buildSearchQuery,
    resetSearch,

    // State management
    hasActiveSearch,
    getSearchState,
    setSearchState,
  }
}
