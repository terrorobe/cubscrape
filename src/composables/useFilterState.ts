/**
 * Filter State Management Composable
 *
 * Centralizes all filter-related reactive state, methods, and URL integration.
 * This composable extracts filter management logic from App.vue to improve
 * organization and reusability.
 */

import { ref, type Ref } from 'vue'
import { PRICING } from '../config/index'
import type { SortSpec, SortChangeEvent } from '../types/sorting'
import type {
  TimeFilter,
  PriceFilter,
  QueryFilters,
} from '../services/QueryBuilderService'
import { usePerformanceMonitoring } from '../utils/performanceMonitor'
import { debug } from '../utils/debug'
import type { Database } from 'sql.js'

/**
 * Complete filter state interface matching App.vue's AppFilters
 */
export interface FilterState extends Record<string, unknown> {
  releaseStatus: string
  platform: string
  rating: string
  crossPlatform: boolean
  hiddenGems: boolean
  selectedTags: string[]
  tagLogic: 'and' | 'or'
  selectedChannels: string[]
  sortBy: string
  sortSpec: SortSpec
  currency: 'eur' | 'usd'
  timeFilter: TimeFilter
  priceFilter: PriceFilter
  searchQuery: string
  searchInVideoTitles: boolean
}

/**
 * Filter update callback function type
 */
export type FilterUpdateCallback = (db: Database) => void

/**
 * URL state update callback function type
 */
export type URLStateUpdateCallback = (
  filterValues: FilterState,
  currentPage: Ref<number>,
  pageSize: Ref<number>,
) => void

/**
 * Composable options interface
 */
export interface UseFilterStateOptions {
  executeQuery?: FilterUpdateCallback
  updateURLParams?: URLStateUpdateCallback
  currentPage?: Ref<number>
  pageSize?: Ref<number>
  database?: () => Database | null
}

/**
 * Default filter values
 */
const createDefaultFilters = (): FilterState => ({
  releaseStatus: 'all',
  platform: 'all',
  rating: '0',
  crossPlatform: false,
  hiddenGems: false,
  selectedTags: [], // Multi-select tags
  tagLogic: 'and', // 'and' or 'or'
  selectedChannels: [], // Multi-select channels
  sortBy: 'date',
  sortSpec: null, // Advanced sorting specification
  currency: 'eur',
  // Time-based filtering
  timeFilter: {
    type: null, // 'video', 'release', 'smart'
    preset: null, // preset key or 'custom'
    startDate: null, // YYYY-MM-DD format
    endDate: null, // YYYY-MM-DD format
    smartLogic: null, // for smart filters
  },
  // Price-based filtering
  priceFilter: {
    minPrice: PRICING.MIN_PRICE,
    maxPrice: PRICING.DEFAULT_MAX_PRICE,
  },
  // Search filtering
  searchQuery: '',
  searchInVideoTitles: false,
})

/**
 * Filter State Management Composable
 *
 * Provides centralized management of all filter-related state and operations.
 * Integrates with URL state management and database query execution.
 */
export function useFilterState(options: UseFilterStateOptions = {}) {
  const { monitorFilterUpdate } = usePerformanceMonitoring()

  // Reactive filter state
  const filters: Ref<FilterState> = ref(createDefaultFilters())

  // Destructure options with defaults
  const {
    executeQuery,
    updateURLParams,
    currentPage = ref(1),
    pageSize = ref(150),
    database,
  } = options

  /**
   * Update filters with new values and trigger necessary side effects
   */
  const updateFilters = (
    newFilters: Partial<FilterState>,
    skipQuery = false,
  ): void => {
    monitorFilterUpdate('Complete Filter Update', () => {
      filters.value = { ...filters.value, ...newFilters }

      // Update URL if callback provided
      if (updateURLParams) {
        updateURLParams(filters.value, currentPage, pageSize)
      }

      // Execute query if database available and not skipped
      if (executeQuery && database && !skipQuery) {
        const db = database()
        if (db) {
          executeQuery(db)
        }
      }
    })
  }

  /**
   * Update a specific filter field
   */
  const updateFilter = <K extends keyof FilterState>(
    key: K,
    value: FilterState[K],
  ): void => {
    updateFilters({ [key]: value } as Partial<FilterState>)
  }

  /**
   * Clear all filters to default values
   */
  const clearFilters = (): void => {
    debug.log('🔄 Clearing all filters to defaults')
    const defaultFilters = createDefaultFilters()
    updateFilters(defaultFilters)
  }

  /**
   * Reset only selection filters (tags, channels) while keeping other filters
   */
  const clearSelectionFilters = (): void => {
    debug.log('🔄 Clearing selection filters (tags, channels)')
    updateFilters({
      selectedTags: [],
      selectedChannels: [],
    })
  }

  /**
   * Reset search filters
   */
  const clearSearchFilters = (): void => {
    debug.log('🔄 Clearing search filters')
    updateFilters({
      searchQuery: '',
      searchInVideoTitles: false,
    })
  }

  /**
   * Reset time-based filters
   */
  const clearTimeFilters = (): void => {
    debug.log('🔄 Clearing time filters')
    updateFilters({
      timeFilter: {
        type: null,
        preset: null,
        startDate: null,
        endDate: null,
        smartLogic: null,
      },
    })
  }

  /**
   * Reset price filters to defaults
   */
  const clearPriceFilters = (): void => {
    debug.log('🔄 Clearing price filters')
    updateFilters({
      priceFilter: {
        minPrice: PRICING.MIN_PRICE,
        maxPrice: PRICING.DEFAULT_MAX_PRICE,
      },
    })
  }

  /**
   * Handle tag selection from game cards or other components
   */
  const handleTagClick = (tag: string): void => {
    const currentTags = filters.value.selectedTags || []
    if (!currentTags.includes(tag)) {
      debug.log(`🏷️ Adding tag filter: ${tag}`)
      updateFilter('selectedTags', [...currentTags, tag])
    }
  }

  /**
   * Remove a specific tag from selected tags
   */
  const removeTag = (tag: string): void => {
    const currentTags = filters.value.selectedTags || []
    const newTags = currentTags.filter((t) => t !== tag)
    debug.log(`🏷️ Removing tag filter: ${tag}`)
    updateFilter('selectedTags', newTags)
  }

  /**
   * Handle channel selection
   */
  const handleChannelClick = (channel: string): void => {
    const currentChannels = filters.value.selectedChannels || []
    if (!currentChannels.includes(channel)) {
      debug.log(`📺 Adding channel filter: ${channel}`)
      updateFilter('selectedChannels', [...currentChannels, channel])
    }
  }

  /**
   * Remove a specific channel from selected channels
   */
  const removeChannel = (channel: string): void => {
    const currentChannels = filters.value.selectedChannels || []
    const newChannels = currentChannels.filter((c) => c !== channel)
    debug.log(`📺 Removing channel filter: ${channel}`)
    updateFilter('selectedChannels', newChannels)
  }

  /**
   * Handle sort changes from sorting components
   */
  const handleSortChange = (sortData: SortChangeEvent): void => {
    debug.log('🔀 Updating sort configuration:', sortData)
    updateFilters({
      sortBy: sortData.sortBy,
      sortSpec: sortData.sortSpec,
    })
  }

  /**
   * Set multiple filters at once (useful for URL state loading)
   */
  const setFilters = (newFilters: Partial<FilterState>): void => {
    debug.log('📥 Setting filters from external source:', newFilters)
    filters.value = { ...filters.value, ...newFilters }
  }

  /**
   * Get current filter state (useful for URL state management)
   */
  const getFilters = (): FilterState => ({ ...filters.value })

  /**
   * Check if any filters are active (not at default values)
   */
  const hasActiveFilters = (): boolean => {
    const defaultFilters = createDefaultFilters()
    const current = filters.value

    return (
      current.releaseStatus !== defaultFilters.releaseStatus ||
      current.platform !== defaultFilters.platform ||
      current.rating !== defaultFilters.rating ||
      current.crossPlatform !== defaultFilters.crossPlatform ||
      current.hiddenGems !== defaultFilters.hiddenGems ||
      current.selectedTags.length > 0 ||
      current.selectedChannels.length > 0 ||
      current.sortBy !== defaultFilters.sortBy ||
      current.sortSpec !== defaultFilters.sortSpec ||
      current.currency !== defaultFilters.currency ||
      current.timeFilter.type !== null ||
      current.timeFilter.preset !== null ||
      current.timeFilter.startDate !== null ||
      current.timeFilter.endDate !== null ||
      current.timeFilter.smartLogic !== null ||
      current.priceFilter.minPrice !== defaultFilters.priceFilter.minPrice ||
      current.priceFilter.maxPrice !== defaultFilters.priceFilter.maxPrice ||
      current.searchQuery.trim() !== '' ||
      current.searchInVideoTitles !== defaultFilters.searchInVideoTitles
    )
  }

  /**
   * Get count of active filters
   */
  const getActiveFilterCount = (): number => {
    const current = filters.value
    let count = 0

    if (current.releaseStatus !== 'all') {
      count++
    }
    if (current.platform !== 'all') {
      count++
    }
    if (current.rating !== '0') {
      count++
    }
    if (current.crossPlatform) {
      count++
    }
    if (current.hiddenGems) {
      count++
    }
    if (current.selectedTags.length > 0) {
      count++
    }
    if (current.selectedChannels.length > 0) {
      count++
    }
    if (current.sortBy !== 'date') {
      count++
    }
    if (current.currency !== 'eur') {
      count++
    }
    if (current.timeFilter.type !== null) {
      count++
    }
    if (
      current.priceFilter.minPrice > PRICING.MIN_PRICE ||
      current.priceFilter.maxPrice < PRICING.DEFAULT_MAX_PRICE
    ) {
      count++
    }
    if (current.searchQuery.trim() !== '') {
      count++
    }
    if (current.searchInVideoTitles) {
      count++
    }

    return count
  }

  /**
   * Convert FilterState to QueryFilters for service compatibility
   */
  const toQueryFilters = (): QueryFilters => ({
    releaseStatus: filters.value.releaseStatus,
    platform: filters.value.platform,
    rating: filters.value.rating,
    crossPlatform: filters.value.crossPlatform,
    hiddenGems: filters.value.hiddenGems,
    selectedTags: filters.value.selectedTags,
    tagLogic: filters.value.tagLogic,
    selectedChannels: filters.value.selectedChannels,
    sortBy: filters.value.sortBy,
    sortSpec: filters.value.sortSpec,
    currency: filters.value.currency,
    timeFilter: filters.value.timeFilter,
    priceFilter: filters.value.priceFilter,
    searchQuery: filters.value.searchQuery,
    searchInVideoTitles: filters.value.searchInVideoTitles,
  })

  return {
    // Reactive state
    filters: filters as Readonly<Ref<FilterState>>,

    // Update methods
    updateFilters,
    updateFilter,
    setFilters,

    // Clear methods
    clearFilters,
    clearSelectionFilters,
    clearSearchFilters,
    clearTimeFilters,
    clearPriceFilters,

    // Selection handlers
    handleTagClick,
    removeTag,
    handleChannelClick,
    removeChannel,
    handleSortChange,

    // State inspection
    getFilters,
    hasActiveFilters,
    getActiveFilterCount,
    toQueryFilters,
  }
}
