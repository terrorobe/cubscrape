import { type Ref } from 'vue'
import { queryBuilderService } from '../services/QueryBuilderService'
import type { FilterConfig } from '../utils/presetManager'
import type { SearchQueryParams } from './useGameSearch'
import type { Database } from 'sql.js'
import type { QueryFilters } from '../services/QueryBuilderService'
import { debug } from '../utils/debug'

// Import PriceFilterConfig type inline since it's from a Vue file
interface PriceFilterConfig {
  minPrice: number
  maxPrice: number
}

/**
 * Composable for live price count calculation during slider interaction
 * Executes optimized count queries directly against the database
 */
export function useLivePriceCount(
  currentFilters: Ref<FilterConfig>,
  database: () => Database | null,
  buildSearchQuery: (
    searchTerm: string,
    searchInVideoTitles: boolean,
  ) => SearchQueryParams,
) {
  /**
   * Get live count of games matching current filters with custom price range
   * @param priceFilter - The price filter to apply
   * @returns Number of games matching all filters
   */
  const getLiveCount = (priceFilter: PriceFilterConfig): number => {
    const db = database()
    if (!db) {
      return 0
    }

    // Create temporary filter state with new price filter
    const tempFilters = {
      ...currentFilters.value,
      priceFilter,
    }

    // Convert FilterConfig to QueryFilters format for QueryBuilderService
    const queryFilters: QueryFilters = {
      releaseStatus: tempFilters.releaseStatus,
      platform: tempFilters.platform,
      rating: tempFilters.rating,
      crossPlatform: tempFilters.crossPlatform ?? false,
      hiddenGems: tempFilters.hiddenGems ?? false,
      onSale: tempFilters.onSale ?? false,
      selectedTags: tempFilters.selectedTags,
      tagLogic: tempFilters.tagLogic,
      selectedChannels: tempFilters.selectedChannels,
      sortBy: tempFilters.sortBy,
      sortSpec: tempFilters.sortSpec,
      currency: tempFilters.currency,
      timeFilter: tempFilters.timeFilter,
      priceFilter: tempFilters.priceFilter,
      searchQuery: '', // No search query needed for count queries
      searchInVideoTitles: false, // No search needed for count queries
    }

    try {
      // Build optimized count query (no JOINs, no ORDER BY)
      const { query, params } = queryBuilderService.buildCountQuery(
        queryFilters,
        buildSearchQuery,
      )

      // Execute query and extract count
      const result = db.exec(query, params)
      return result.length > 0 && result[0].values.length > 0
        ? (result[0].values[0][0] as number)
        : 0
    } catch (error) {
      debug.error('Error executing live count query:', error)
      return 0
    }
  }

  return { getLiveCount }
}
