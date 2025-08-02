import { debug } from '../utils/debug'
import type { SortSpec } from '../types/sorting'
import { normalizeSortSpec, isAdvancedSortSpec } from '../types/sorting'
import type { SearchQueryParams } from '../composables/useGameSearch'
import {
  PRICING,
  RATINGS,
  HIDDEN_GEMS,
  TIME_RANGES,
  VIDEO_COVERAGE,
} from '../config/index'

/**
 * Time filter configuration interface
 */
export interface TimeFilter {
  type: string | null
  preset: string | null
  startDate: string | null
  endDate: string | null
  smartLogic: string | null
}

/**
 * Price filter configuration interface
 */
export interface PriceFilter {
  minPrice: number
  maxPrice: number
}

/**
 * Complete filter configuration interface for SQL query building
 */
export interface QueryFilters {
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
 * SQL query result interface
 */
export interface QueryResult {
  query: string
  params: (string | number)[]
}

/**
 * Query Builder Service that handles all SQL query generation for game filtering and sorting
 *
 * This service is responsible for:
 * - Building complex SQL queries with multiple filter conditions
 * - Generating sort clauses including advanced and smart sorting
 * - Optimizing query performance by ordering conditions strategically
 * - Handling search integration from the useGameSearch composable
 *
 * The service is stateless and designed to be used as a singleton.
 */
export class QueryBuilderService {
  /**
   * Build a complete SQL query with all filters applied
   *
   * @param filterValues - Complete filter configuration
   * @param searchQueryBuilder - Function to build search query (from useGameSearch)
   * @param selectClause - Type of query to build ('full', 'count', 'price-only')
   * @returns Object containing SQL query string and parameters
   */
  buildSQLQuery(
    filterValues: QueryFilters,
    searchQueryBuilder: (
      searchTerm: string,
      searchInVideoTitles: boolean,
    ) => SearchQueryParams,
    selectClause: 'full' | 'count' | 'price-only' = 'full',
  ): QueryResult {
    // Only log for full queries to reduce noise during live filtering
    if (selectClause === 'full') {
      debug.log('Building query with filters:', filterValues)
    }

    // Performance optimization: Track which filters are active to optimize query order
    // These variables can be used for future query optimization

    // Build SELECT and FROM clauses based on query type
    const selectClauses = {
      full: `SELECT g.*,
               gv.video_title as latest_video_title,
               gv.video_id as latest_video_id`,
      count: `SELECT COUNT(*) as count`,
      'price-only': `SELECT g.id, g.price_usd, g.price_eur, g.is_free`,
    }

    let query = `
        ${selectClauses[selectClause]}
        FROM games g`

    // Only add JOINs for full queries that need video data
    if (selectClause === 'full') {
      query += `
        LEFT JOIN game_videos gv ON g.id = gv.game_id
        AND gv.video_date = g.latest_video_date`
    }

    query += `
        WHERE 1=1
      `
    const params: (string | number)[] = []

    // Start with most selective conditions first for better performance

    // For release date sorting, only include games with sortable dates
    if (
      filterValues.sortBy === 'release-new' ||
      filterValues.sortBy === 'release-old'
    ) {
      query += ' AND g.release_date_sortable IS NOT NULL'
    }

    // Platform filter early (highly selective)
    if (filterValues.platform && filterValues.platform !== 'all') {
      if (filterValues.platform === 'itch') {
        // Special handling for itch filter: show both itch games and absorbed itch games
        query +=
          " AND ((g.platform = ? AND g.is_absorbed = 0) OR (g.platform = 'steam' AND g.itch_url IS NOT NULL) OR (g.platform = 'itch' AND g.is_absorbed = 1))"
        params.push(filterValues.platform)
      } else {
        // For steam/crazygames: exclude absorbed games by default
        query += ' AND g.platform = ? AND g.is_absorbed = 0'
        params.push(filterValues.platform)
      }
    } else if (!filterValues.crossPlatform) {
      // Default filter: exclude absorbed games when showing all platforms (unless cross-platform filter is active)
      query += ' AND g.is_absorbed = 0'
    }

    // Cross-platform filter (if not already handled by platform filter)
    if (
      filterValues.crossPlatform &&
      (filterValues.platform === 'all' || !filterValues.platform)
    ) {
      // Count how many platform URLs are non-null
      query += ` AND (
          (CASE WHEN g.steam_url IS NOT NULL THEN 1 ELSE 0 END +
           CASE WHEN g.itch_url IS NOT NULL THEN 1 ELSE 0 END +
           CASE WHEN g.crazygames_url IS NOT NULL THEN 1 ELSE 0 END) >= 2
        ) AND g.is_absorbed = 0`
    }

    // Rating filter (highly selective, place early)
    if (filterValues.rating && filterValues.rating !== '0') {
      const ratingValue = parseInt(filterValues.rating)
      if (!isNaN(ratingValue)) {
        query += ' AND g.positive_review_percentage >= ?'
        params.push(ratingValue)
      }
    }

    // Hidden Gems filter (very selective)
    if (filterValues.hiddenGems) {
      query += ` AND g.positive_review_percentage >= ${HIDDEN_GEMS.MIN_RATING} AND g.video_count >= ${HIDDEN_GEMS.MIN_VIDEOS} AND g.video_count <= ${HIDDEN_GEMS.MAX_VIDEOS} AND g.review_count >= ${HIDDEN_GEMS.MIN_REVIEWS}`
    }

    // Release status filter
    if (filterValues.releaseStatus && filterValues.releaseStatus !== 'all') {
      if (filterValues.releaseStatus === 'released') {
        query +=
          " AND (g.platform IN ('itch', 'crazygames') OR (g.platform = 'steam' AND g.coming_soon = 0 AND g.is_early_access = 0 AND g.is_demo = 0))"
      } else if (filterValues.releaseStatus === 'early-access') {
        query +=
          " AND g.platform = 'steam' AND g.is_early_access = 1 AND g.coming_soon = 0"
      } else if (filterValues.releaseStatus === 'coming-soon') {
        query += " AND g.platform = 'steam' AND g.coming_soon = 1"
      }
    }

    // Tag filter with AND/OR logic
    // Note: These are expensive LIKE queries on JSON columns - consider placing them later for better performance
    if (filterValues.selectedTags && filterValues.selectedTags.length > 0) {
      const tagConditions = filterValues.selectedTags.map(() => 'g.tags LIKE ?')
      if (filterValues.tagLogic === 'or') {
        query += ` AND (${tagConditions.join(' OR ')})`
      } else {
        // AND logic - each tag must be present
        query += ` AND (${tagConditions.join(' AND ')})`
      }
      filterValues.selectedTags.forEach((tag) => {
        params.push(`%"${tag}"%`)
      })
    }

    // Channel filter with OR logic (games featured by ANY selected channel)
    // Note: These are expensive LIKE queries on JSON columns - consider placing them later for better performance
    if (
      filterValues.selectedChannels &&
      filterValues.selectedChannels.length > 0
    ) {
      const channelConditions = filterValues.selectedChannels.map(
        () => 'g.unique_channels LIKE ?',
      )
      query += ` AND (${channelConditions.join(' OR ')})`
      filterValues.selectedChannels.forEach((channel) => {
        params.push(`%"${channel}"%`)
      })
    }

    // Price-based filtering
    if (filterValues.priceFilter) {
      const { priceFilter } = filterValues
      const currencyField =
        filterValues.currency === 'usd' ? 'price_usd' : 'price_eur'

      // Handle price range filtering
      if (
        priceFilter.minPrice > 0 ||
        priceFilter.maxPrice < PRICING.DEFAULT_MAX_PRICE
      ) {
        const priceConditions = []

        // Free games condition (when minPrice is 0, include free games)
        if (priceFilter.minPrice === 0) {
          priceConditions.push(`(g.is_free = 1 OR g.${currencyField} = 0)`)
        }

        // Paid games price range condition
        if (priceFilter.maxPrice > 0) {
          const paidCondition = `(g.is_free = 0 AND g.${currencyField} IS NOT NULL AND g.${currencyField} >= ? AND g.${currencyField} <= ?)`
          priceConditions.push(paidCondition)
          params.push(priceFilter.minPrice)
          params.push(priceFilter.maxPrice)
        }

        if (priceConditions.length > 0) {
          query += ` AND (${priceConditions.join(' OR ')})`
        }
      }
    }

    // Time-based filtering
    if (filterValues.timeFilter?.type) {
      const queryAndParams = this.buildTimeFilter(
        filterValues.timeFilter,
        query,
        params,
      )
      const { query: updatedQuery, params: newParams } = queryAndParams
      query = updatedQuery
      params.push(...newParams)
    }

    // Search filtering using LIKE queries
    if (filterValues.searchQuery?.trim()) {
      const searchQuery = searchQueryBuilder(
        filterValues.searchQuery,
        filterValues.searchInVideoTitles,
      )
      query += searchQuery.query
      params.push(...searchQuery.params)
    }

    // Advanced Sorting Logic (only for full queries)
    if (selectClause === 'full') {
      const orderByClause = this.buildSortClause(filterValues)
      query += ` ORDER BY ${orderByClause}`
    }

    return { query, params }
  }

  /**
   * Build a count-only query for live filtering (optimized for performance)
   *
   * @param filterValues - Complete filter configuration
   * @param searchQueryBuilder - Function to build search query (from useGameSearch)
   * @returns Object containing SQL query string and parameters
   */
  buildCountQuery(
    filterValues: QueryFilters,
    searchQueryBuilder: (
      searchTerm: string,
      searchInVideoTitles: boolean,
    ) => SearchQueryParams,
  ): QueryResult {
    return this.buildSQLQuery(filterValues, searchQueryBuilder, 'count')
  }

  /**
   * Build time-based filter conditions
   *
   * @param timeFilter - Time filter configuration
   * @param baseQuery - Base SQL query
   * @param baseParams - Base SQL parameters
   * @returns Updated query and parameters
   */
  private buildTimeFilter(
    timeFilter: TimeFilter,
    baseQuery: string,
    baseParams: (string | number)[],
  ): { query: string; params: (string | number)[] } {
    let query = baseQuery
    const params = [...baseParams]

    if (
      timeFilter.type === 'video' &&
      (timeFilter.startDate || timeFilter.endDate)
    ) {
      // Filter by video publication date
      if (timeFilter.startDate && timeFilter.endDate) {
        query += ' AND g.latest_video_date >= ? AND g.latest_video_date <= ?'
        params.push(`${timeFilter.startDate}T00:00:00`)
        params.push(`${timeFilter.endDate}T23:59:59`)
      } else if (timeFilter.startDate) {
        query += ' AND g.latest_video_date >= ?'
        params.push(`${timeFilter.startDate}T00:00:00`)
      } else if (timeFilter.endDate) {
        query += ' AND g.latest_video_date <= ?'
        params.push(`${timeFilter.endDate}T23:59:59`)
      }
    } else if (
      timeFilter.type === 'release' &&
      (timeFilter.startDate || timeFilter.endDate)
    ) {
      // Filter by game release date using sortable date format
      query += ' AND g.release_date_sortable IS NOT NULL'

      if (timeFilter.startDate && timeFilter.endDate) {
        const startSortable = parseInt(timeFilter.startDate.replace(/-/g, ''))
        const endSortable = parseInt(timeFilter.endDate.replace(/-/g, ''))
        query +=
          ' AND g.release_date_sortable >= ? AND g.release_date_sortable <= ?'
        params.push(startSortable)
        params.push(endSortable)
      } else if (timeFilter.startDate) {
        const startSortable = parseInt(timeFilter.startDate.replace(/-/g, ''))
        query += ' AND g.release_date_sortable >= ?'
        params.push(startSortable)
      } else if (timeFilter.endDate) {
        const endSortable = parseInt(timeFilter.endDate.replace(/-/g, ''))
        query += ' AND g.release_date_sortable <= ?'
        params.push(endSortable)
      }
    } else if (timeFilter.type === 'smart' && timeFilter.smartLogic) {
      const smartResult = this.buildSmartTimeFilter(
        timeFilter.smartLogic,
        query,
        params,
      )
      const { query: updatedQuery, params: newParams } = smartResult
      query = updatedQuery
      params.push(...newParams)
    }

    return { query, params }
  }

  /**
   * Build smart time filtering logic
   *
   * @param smartLogic - Smart filter logic type
   * @param baseQuery - Base SQL query
   * @param baseParams - Base SQL parameters
   * @returns Updated query and parameters
   */
  private buildSmartTimeFilter(
    smartLogic: string,
    baseQuery: string,
    baseParams: (string | number)[],
  ): { query: string; params: (string | number)[] } {
    let query = baseQuery
    const params = [...baseParams]

    // Smart filtering logic
    const now = new Date()
    const thirtyDaysAgo = new Date(
      now.getTime() - TIME_RANGES.MONTHLY * 24 * 60 * 60 * 1000,
    )
    const sevenDaysAgo = new Date(
      now.getTime() - TIME_RANGES.RECENT * 24 * 60 * 60 * 1000,
    )
    const oneYearAgo = new Date(
      now.getTime() - TIME_RANGES.YEARLY * 24 * 60 * 60 * 1000,
    )
    const twoThousandTwenty = new Date('2020-01-01')

    switch (smartLogic) {
      case 'release-and-video-recent':
        // Recently released games with video coverage
        query += ' AND g.release_date_sortable IS NOT NULL'
        query += ' AND g.release_date_sortable >= ?'
        query += ' AND g.latest_video_date >= ?'
        params.push(
          parseInt(thirtyDaysAgo.toISOString().slice(0, 10).replace(/-/g, '')),
        )
        params.push(thirtyDaysAgo.toISOString())
        break

      case 'first-video-recent':
        // Games with first video coverage recently - need to join with game_videos
        query = query.replace(
          'LEFT JOIN game_videos gv ON g.id = gv.game_id AND gv.video_date = g.latest_video_date',
          `LEFT JOIN game_videos gv ON g.id = gv.game_id AND gv.video_date = g.latest_video_date
               LEFT JOIN (
                 SELECT game_id, MIN(video_date) as first_video_date 
                 FROM game_videos 
                 GROUP BY game_id
               ) fv ON g.id = fv.game_id`,
        )
        query += ' AND fv.first_video_date >= ?'
        params.push(thirtyDaysAgo.toISOString())
        break

      case 'multiple-videos-recent':
        // Games with multiple videos in last 7 days (trending)
        query = query.replace(
          'LEFT JOIN game_videos gv ON g.id = gv.game_id AND gv.video_date = g.latest_video_date',
          `LEFT JOIN game_videos gv ON g.id = gv.game_id AND gv.video_date = g.latest_video_date
               LEFT JOIN (
                 SELECT game_id, COUNT(*) as recent_video_count 
                 FROM game_videos 
                 WHERE video_date >= ? 
                 GROUP BY game_id 
                 HAVING COUNT(*) >= 2
               ) rv ON g.id = rv.game_id`,
        )
        query += ' AND rv.recent_video_count >= 2'
        params.push(sevenDaysAgo.toISOString())
        break

      case 'old-game-new-attention':
        // Older games (2020+) with recent video attention
        query += ' AND g.release_date_sortable IS NOT NULL'
        query +=
          ' AND g.release_date_sortable >= ? AND g.release_date_sortable <= ?'
        query += ' AND g.latest_video_date >= ?'
        params.push(
          parseInt(
            twoThousandTwenty.toISOString().slice(0, 10).replace(/-/g, ''),
          ),
        )
        params.push(
          parseInt(oneYearAgo.toISOString().slice(0, 10).replace(/-/g, '')),
        )
        params.push(thirtyDaysAgo.toISOString())
        break
    }

    return { query, params }
  }

  /**
   * Build complete sort clause for SQL ORDER BY
   *
   * @param filterValues - Filter configuration containing sort settings
   * @returns SQL ORDER BY clause string
   */
  buildSortClause(filterValues: QueryFilters): string {
    // Handle advanced sorting with multi-criteria
    if (filterValues.sortBy === 'advanced' && filterValues.sortSpec) {
      return this.buildAdvancedSortClause(filterValues.sortSpec)
    }

    // Handle smart discovery sorting presets
    if (this.isSmartSortPreset(filterValues.sortBy)) {
      return this.buildSmartSortClause(filterValues.sortBy)
    }

    // Traditional single-criteria sorting
    const sortMappings: Record<string, string> = {
      'rating-score': 'positive_review_percentage DESC',
      'rating-category':
        'review_summary_priority ASC, positive_review_percentage DESC, review_count DESC',
      date: 'latest_video_date DESC',
      name: 'name ASC',
      'release-new': 'release_date_sortable DESC',
      'release-old': 'release_date_sortable ASC',
    }

    return sortMappings[filterValues.sortBy] ?? 'latest_video_date DESC'
  }

  /**
   * Build advanced multi-criteria sort clause
   *
   * @param sortSpec - Advanced sort specification
   * @returns SQL ORDER BY clause string
   */
  private buildAdvancedSortClause(sortSpec: SortSpec): string {
    const normalized = normalizeSortSpec(sortSpec)

    // If it's a string, treat as simple sort
    if (typeof normalized === 'string') {
      return (
        this.getSortFieldClause(normalized, 'desc') ?? 'latest_video_date DESC'
      )
    }

    if (!normalized) {
      return 'latest_video_date DESC'
    }

    // Handle advanced sort object
    if (!isAdvancedSortSpec(normalized)) {
      // If it's not an advanced spec, fall back to default sorting
      return (
        this.getSortFieldClause('latest_video_date', 'desc') ??
        'latest_video_date DESC'
      )
    }

    const clauses = []

    // Primary sorting criteria
    const primaryClause = this.getSortFieldClause(
      normalized.primary?.field ?? 'latest_video_date',
      normalized.primary?.direction ?? 'desc',
    )
    if (primaryClause) {
      clauses.push(primaryClause)
    }

    // Secondary sorting criteria
    if (normalized.secondary) {
      const secondaryClause = this.getSortFieldClause(
        normalized.secondary.field,
        normalized.secondary.direction,
      )
      if (secondaryClause) {
        clauses.push(secondaryClause)
      }
    }

    // Add fallback sorts for consistency
    clauses.push('latest_video_date DESC') // Recency fallback
    clauses.push('name ASC') // Alphabetical fallback

    return clauses.join(', ')
  }

  /**
   * Get SQL clause for a specific sort field
   *
   * @param field - Sort field name
   * @param direction - Sort direction (asc/desc)
   * @returns SQL sort clause or null if field is invalid
   */
  private getSortFieldClause(field: string, direction: string): string | null {
    const dir = direction.toUpperCase()

    switch (field) {
      case 'rating':
        return `positive_review_percentage ${dir}`
      case 'coverage':
        return `video_count ${dir}`
      case 'recency':
        return `latest_video_date ${dir}`
      case 'release':
        return `release_date_sortable ${dir}`
      case 'price':
        // Price sorting: free games first if ASC, paid games first if DESC
        if (direction === 'asc') {
          return 'CASE WHEN is_free = 1 OR price_final = 0 THEN 0 ELSE price_final END ASC'
        } else {
          return 'CASE WHEN is_free = 1 OR price_final = 0 THEN 99999 ELSE price_final END DESC'
        }
      case 'channels':
        // Channel count sorting (derived from unique_channels JSON length)
        return `LENGTH(unique_channels) - LENGTH(REPLACE(unique_channels, ',', '')) + 1 ${dir}`
      case 'reviews':
        return `review_count ${dir}`
      default:
        return null
    }
  }

  /**
   * Check if a sort type is a smart sort preset
   *
   * @param sortBy - Sort type string
   * @returns True if it's a smart sort preset
   */
  private isSmartSortPreset(sortBy: string): boolean {
    return [
      'best-value',
      'hidden-gems',
      'most-covered',
      'trending',
      'creator-consensus',
      'recent-discoveries',
      'video-recency',
      'time-range-releases',
      'price-value',
      'steam-optimized',
      'itch-discoveries',
      'premium-quality',
      'tag-match',
      'channel-picks',
    ].includes(sortBy)
  }

  /**
   * Build smart discovery sort clause
   *
   * Smart sorts are complex multi-criteria sorts designed to surface interesting games
   * based on various quality and discovery metrics.
   *
   * @param sortBy - Smart sort type
   * @returns SQL ORDER BY clause string
   */
  private buildSmartSortClause(sortBy: string): string {
    switch (sortBy) {
      case 'best-value':
        // High rating + reasonable price (prioritize quality over cheapness)
        return `
            CASE 
              WHEN positive_review_percentage >= ${RATINGS.SMART_SORT.VERY_POSITIVE} AND (is_free = 1 OR price_final <= ${PRICING.VALUE_THRESHOLDS.BUDGET}) THEN 1
              WHEN positive_review_percentage >= ${RATINGS.SMART_SORT.MOSTLY_POSITIVE} AND (is_free = 1 OR price_final <= ${PRICING.VALUE_THRESHOLDS.MODERATE}) THEN 2
              WHEN positive_review_percentage >= ${RATINGS.SMART_SORT.MIXED} THEN 3
              ELSE 4
            END ASC,
            positive_review_percentage DESC,
            CASE WHEN is_free = 1 OR price_final = 0 THEN 0 ELSE price_final END ASC
          `

      case 'hidden-gems':
        // High rating + low video coverage (undiscovered quality games)
        return `
            CASE 
              WHEN positive_review_percentage >= ${RATINGS.SMART_SORT.EXCELLENT} AND video_count <= ${VIDEO_COVERAGE.LOW} THEN 1
              WHEN positive_review_percentage >= ${RATINGS.SMART_SORT.VERY_POSITIVE} AND video_count <= ${VIDEO_COVERAGE.MEDIUM} THEN 2
              WHEN positive_review_percentage >= ${RATINGS.SMART_SORT.POSITIVE} AND video_count <= ${VIDEO_COVERAGE.HIGH} THEN 3
              ELSE 4
            END ASC,
            positive_review_percentage DESC,
            video_count ASC
          `

      case 'most-covered':
        // High video coverage + good ratings (community favorites)
        return `video_count DESC, positive_review_percentage DESC, latest_video_date DESC`

      case 'trending':
        // Recent videos + increasing coverage (games gaining momentum)
        return `
            CASE 
              WHEN latest_video_date >= datetime('now', '-${TIME_RANGES.RECENT} days') AND video_count >= ${VIDEO_COVERAGE.TRENDING_MIN} THEN 1
              WHEN latest_video_date >= datetime('now', '-${TIME_RANGES.SEMI_RECENT} days') AND video_count >= ${VIDEO_COVERAGE.STRONG_CONSENSUS} THEN 2
              WHEN latest_video_date >= datetime('now', '-${TIME_RANGES.MONTHLY} days') AND video_count >= ${VIDEO_COVERAGE.TRENDING_MIN} THEN 3
              ELSE 4
            END ASC,
            latest_video_date DESC,
            video_count DESC
          `

      case 'creator-consensus':
        // Multiple channels + high ratings (broadly appreciated games)
        return `
            CASE 
              WHEN (LENGTH(unique_channels) - LENGTH(REPLACE(unique_channels, ',', '')) + 1) >= ${VIDEO_COVERAGE.STRONG_CONSENSUS} AND positive_review_percentage >= ${RATINGS.SMART_SORT.VERY_POSITIVE} THEN 1
              WHEN (LENGTH(unique_channels) - LENGTH(REPLACE(unique_channels, ',', '')) + 1) >= ${VIDEO_COVERAGE.CONSENSUS_MIN} AND positive_review_percentage >= ${RATINGS.SMART_SORT.POSITIVE} THEN 2
              WHEN (LENGTH(unique_channels) - LENGTH(REPLACE(unique_channels, ',', '')) + 1) >= ${VIDEO_COVERAGE.CONSENSUS_MIN} THEN 3
              ELSE 4
            END ASC,
            positive_review_percentage DESC,
            LENGTH(unique_channels) - LENGTH(REPLACE(unique_channels, ',', '')) + 1 DESC
          `

      case 'recent-discoveries':
        // Recently covered games worth checking out
        return `
            CASE 
              WHEN latest_video_date >= datetime('now', '-${TIME_RANGES.SEMI_RECENT} days') THEN 1
              WHEN latest_video_date >= datetime('now', '-${TIME_RANGES.MONTHLY} days') THEN 2
              ELSE 3
            END ASC,
            latest_video_date DESC,
            CASE 
              WHEN positive_review_percentage >= ${RATINGS.SMART_SORT.VERY_POSITIVE} THEN 1
              WHEN positive_review_percentage >= ${RATINGS.SMART_SORT.MOSTLY_POSITIVE} THEN 2
              ELSE 3
            END ASC
          `

      // Contextual sorting cases
      case 'video-recency':
        // Video time range focused sorting
        return `latest_video_date DESC, positive_review_percentage DESC`

      case 'time-range-releases':
        // Release time range with quality priority
        return `positive_review_percentage DESC, release_date_sortable DESC, video_count DESC`

      case 'price-value':
        // Price range value optimization
        return `
            positive_review_percentage DESC,
            CASE WHEN is_free = 1 OR price_final = 0 THEN 0 ELSE price_final END ASC,
            video_count DESC
          `

      case 'steam-optimized':
        // Steam-specific quality sorting
        return `
            review_summary_priority ASC,
            positive_review_percentage DESC,
            review_count DESC,
            latest_video_date DESC
          `

      case 'itch-discoveries':
        // Itch.io creative discoveries
        return `video_count DESC, latest_video_date DESC, positive_review_percentage DESC`

      case 'premium-quality':
        // High-rating focused with review depth
        return `
            review_count DESC,
            positive_review_percentage DESC,
            latest_video_date DESC
          `

      case 'tag-match':
        // Tag relevance sorting
        return `positive_review_percentage DESC, video_count DESC, latest_video_date DESC`

      case 'channel-picks':
        // Channel-specific selections
        return `positive_review_percentage DESC, video_count DESC, latest_video_date DESC`

      default:
        return 'latest_video_date DESC'
    }
  }
}

// Export singleton instance
export const queryBuilderService = new QueryBuilderService()
