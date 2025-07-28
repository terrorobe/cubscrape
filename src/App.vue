<template>
  <div class="min-h-screen bg-bg-primary text-text-primary">
    <div
      class="container mx-auto p-5"
      :style="{ 'max-width': LAYOUT.CONTAINER_MAX_WIDTH }"
    >
      <header class="mb-10 text-center">
        <h1 class="mb-2 text-4xl font-bold text-accent">Curated Steam Games</h1>
        <p class="text-lg text-text-secondary">
          Discovered from YouTube Gaming Channels
        </p>
      </header>

      <!-- Desktop Layout: Sidebar + Main Content -->
      <div class="flex gap-6">
        <!-- Desktop Sidebar (hidden on mobile) -->
        <div
          class="hidden shrink-0 transition-all duration-300 ease-in-out md:block"
          :class="sidebarCollapsed ? 'w-12' : 'w-72'"
        >
          <!-- Sidebar Toggle Button -->
          <div class="sticky top-6 mb-4">
            <button
              @click="sidebarCollapsed = !sidebarCollapsed"
              class="flex size-10 items-center justify-center rounded-lg bg-accent text-white transition-colors hover:bg-accent-hover active:bg-accent-active"
              :title="sidebarCollapsed ? 'Expand filters' : 'Collapse filters'"
            >
              <svg
                class="size-5 transition-transform duration-300"
                :class="sidebarCollapsed ? 'rotate-180' : ''"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M15 19l-7-7 7-7"
                ></path>
              </svg>
            </button>
          </div>

          <!-- Sidebar Content -->
          <div
            v-show="!sidebarCollapsed"
            class="sidebar-scroll sticky top-20 max-h-[calc(100vh-6rem)] space-y-6 overflow-y-auto pr-2 transition-opacity duration-300"
            ref="sidebarScroll"
          >
            <GameFilters
              :channels="channels"
              :channels-with-counts="channelsWithCounts"
              :tags="allTags"
              :initial-filters="filters"
              :game-count="filteredGames.length"
              :game-stats="gameStats"
              @filters-changed="updateFilters"
            />
          </div>
        </div>

        <!-- Main Content Area -->
        <div class="flex-1">
          <!-- Mobile Filters (shown only on mobile) -->
          <div class="mb-6 md:hidden">
            <GameFilters
              :channels="channels"
              :channels-with-counts="channelsWithCounts"
              :tags="allTags"
              :initial-filters="filters"
              :game-count="filteredGames.length"
              :game-stats="gameStats"
              @filters-changed="updateFilters"
            />
          </div>

          <!-- Sort & Status Info -->
          <div class="relative mb-5 text-text-secondary">
            <!-- Centered content - Sort indicator and game count -->
            <div class="flex flex-col items-center gap-2 md:items-start">
              <!-- Sort Indicator -->
              <SortIndicator
                :sort-by="filters.sortBy"
                :sort-spec="filters.sortSpec"
                :game-count="filteredGames.length"
                @sort-changed="handleSortChange"
              />

              <!-- Game count -->
              <div class="hidden text-center md:block md:text-left">
                <span>{{ filteredGames.length }} games found</span>
              </div>
            </div>

            <!-- Database Status - Absolute positioned to right -->
            <div class="absolute top-0 right-0 flex items-center gap-4 text-sm">
              <div class="flex items-center gap-2">
                <span
                  class="size-2 rounded-full"
                  :class="
                    databaseStatus.connected ? 'bg-green-500' : 'bg-red-500'
                  "
                ></span>
                <span>{{ databaseStatus.games }} total</span>
              </div>
              <div class="text-xs text-text-secondary/70">
                <span
                  v-if="databaseStatus.lastGenerated"
                  :title="
                    isDevelopment
                      ? 'Click to test version mismatch'
                      : `Database generation time: ${formatExactTimestamp(databaseStatus.lastGenerated)}. Database should roughly update every 6 hours.`
                  "
                  :class="
                    isDevelopment
                      ? 'cursor-pointer hover:text-text-primary'
                      : ''
                  "
                  @click="isDevelopment ? testVersionMismatch() : null"
                >
                  Database:
                  {{ formatTimestamp(databaseStatus.lastGenerated, true) }}
                </span>
                <span
                  v-if="databaseStatus.lastChecked && !isDevelopment"
                  :title="`Last database update check: ${formatExactTimestamp(databaseStatus.lastChecked)}. Checks happen every ${Math.round(databaseManager.PRODUCTION_CHECK_INTERVAL / 60000)} minutes.`"
                >
                  • Last check:
                  {{ formatTimestamp(databaseStatus.lastChecked) }}
                </span>
              </div>
            </div>
          </div>

          <!-- Version Mismatch Notification -->
          <div
            v-if="showVersionMismatch"
            class="mb-6 rounded-lg border border-amber-500/50 bg-amber-50 p-4 dark:bg-amber-900/20"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <span class="text-2xl">🔄</span>
                <div>
                  <h3 class="font-semibold text-amber-800 dark:text-amber-200">
                    New Version Available
                  </h3>
                  <p class="text-sm text-amber-700 dark:text-amber-300">
                    The app has been updated. Please reload to get the latest
                    features and fixes.
                  </p>
                </div>
              </div>
              <div class="flex gap-2">
                <button
                  @click="dismissVersionMismatch"
                  class="rounded-sm px-3 py-1 text-sm text-amber-700 hover:bg-amber-100 dark:text-amber-300 dark:hover:bg-amber-800/50"
                >
                  Dismiss
                </button>
                <button
                  @click="reloadApp"
                  class="rounded-sm bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700"
                >
                  Reload Now
                </button>
              </div>
            </div>
          </div>

          <!-- Game Grid -->
          <div class="game-grid grid w-full gap-5" ref="gameGrid">
            <GameCard
              v-for="game in filteredGames"
              :key="game.id"
              :game="game"
              :currency="filters.currency"
              :is-highlighted="highlightedGameId === game.id"
              @click="clearHighlight"
              @tag-click="handleTagClick"
            />
          </div>

          <!-- Loading/Error States -->
          <div v-if="loading" class="py-10 text-center text-text-secondary">
            Loading games...
          </div>

          <div v-if="error" class="py-10 text-center text-red-500">
            Error loading games: {{ error }}
          </div>

          <!-- No Results State -->
          <div
            v-if="!loading && !error && filteredGames.length === 0"
            class="py-10 text-center text-text-secondary"
          >
            No games found matching your criteria.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, type Ref } from 'vue'
import GameCard from './components/GameCard.vue'
import GameFilters from './components/GameFilters.vue'
import SortIndicator from './components/SortIndicator.vue'
import { databaseManager } from './utils/databaseManager'
import type { VersionMismatchInfo } from './utils/databaseManager'
import { usePerformanceMonitoring } from './utils/performanceMonitor'
import type { Database } from 'sql.js'
import type {
  ParsedGameData,
  ChannelWithCount,
  TagWithCount,
} from './types/database'
import {
  TIMING,
  PRICING,
  RATINGS,
  HIDDEN_GEMS,
  TIME_RANGES,
  VIDEO_COVERAGE,
  LAYOUT,
} from './config/index'

// Component interfaces
interface GameStats {
  totalGames: number
  freeGames: number
  maxPrice: number
}

// Extended game interface for App component usage
interface AppGameData extends ParsedGameData {
  // Additional properties used in the component
  price_eur?: number
  price_usd?: number
  is_free: boolean
  release_date?: string
  review_summary?: string
  review_summary_priority?: number
  positive_review_percentage?: number
  review_count?: number
  steam_url?: string
  itch_url?: string
  crazygames_url?: string
  demo_steam_app_id?: string
  demo_steam_url?: string
  last_updated?: string
  latest_video_date?: string
  newest_video_date?: string
  video_count: number
  coming_soon: boolean
  is_early_access: boolean
  is_demo: boolean
  planned_release_date?: string
  insufficient_reviews: boolean
  is_inferred_summary: boolean
  review_tooltip?: string
  recent_review_percentage?: number
  recent_review_count?: number
  is_absorbed: boolean
  absorbed_into?: string
}

interface DatabaseStatus {
  connected: boolean
  games: number
  lastGenerated: Date | null
  lastChecked: Date | null
}

interface SortChangeData {
  sortBy: string
  sortSpec: any
}

interface TimeFilter {
  type: string | null
  preset: string | null
  startDate: string | null
  endDate: string | null
  smartLogic: string | null
}

interface PriceFilter {
  minPrice: number
  maxPrice: number
  includeFree: boolean
}

interface AppFilters {
  releaseStatus: string
  platform: string
  rating: string
  crossPlatform: boolean
  hiddenGems: boolean
  tag: string
  selectedTags: string[]
  tagLogic: 'and' | 'or'
  channel: string
  selectedChannels: string[]
  sortBy: string
  sortSpec: any
  currency: 'eur' | 'usd'
  timeFilter: TimeFilter
  priceFilter: PriceFilter
}

// Component state
const loading: Ref<boolean> = ref(true)
const error: Ref<string | null> = ref(null)
const currentTime: Ref<Date> = ref(new Date())
const sidebarCollapsed: Ref<boolean> = ref(false)
const { monitorDatabaseQuery, monitorFilterUpdate } = usePerformanceMonitoring()
const filters: Ref<AppFilters> = ref({
  releaseStatus: 'all',
  platform: 'all',
  rating: '0',
  crossPlatform: false,
  hiddenGems: false,
  tag: '', // Legacy single tag for backward compatibility
  selectedTags: [], // New multi-select tags
  tagLogic: 'and', // 'and' or 'or'
  channel: '', // Legacy single channel for backward compatibility
  selectedChannels: [], // New multi-select channels
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
    includeFree: true,
  },
})

const channels: Ref<string[]> = ref([])
const channelsWithCounts: Ref<ChannelWithCount[]> = ref([])
const allTags: Ref<TagWithCount[]> = ref([])
const gameGrid: Ref<HTMLElement | null> = ref(null)
const highlightedGameId: Ref<number | null> = ref(null)
const gameStats: Ref<GameStats> = ref({
  totalGames: 0,
  freeGames: 0,
  maxPrice: PRICING.DEFAULT_MAX_PRICE,
})
const isDevelopment: boolean = import.meta.env.DEV
const databaseStatus: Ref<DatabaseStatus> = ref({
  connected: false,
  games: 0,
  lastGenerated: null,
  lastChecked: null,
})
const showVersionMismatch: Ref<boolean> = ref(false)
const versionMismatchInfo: Ref<VersionMismatchInfo | null> = ref(null)

const loadGameStats = (database: Database): void => {
  // Get game statistics for price filtering
  const statsResults = database.exec(`
        SELECT 
          COUNT(*) as total_games,
          COUNT(CASE WHEN is_free = 1 OR price_final = 0 THEN 1 END) as free_games,
          MAX(CASE WHEN price_final > 0 THEN price_final ELSE 0 END) as max_price
        FROM games 
        WHERE is_absorbed = 0
      `)

  if (statsResults.length > 0 && statsResults[0].values.length > 0) {
    const stats = statsResults[0].values[0]
    gameStats.value = {
      totalGames: stats[0] || 0,
      freeGames: stats[1] || 0,
      maxPrice: Math.ceil(stats[2] || PRICING.DEFAULT_MAX_PRICE),
    }
  }
}

const loadChannelsAndTags = (database: Database): void => {
  // Get all unique channels with counts
  const channelResults = database.exec(
    "SELECT unique_channels FROM games WHERE unique_channels IS NOT NULL AND unique_channels != '[]' AND is_absorbed = 0",
  )
  const channelCounts = new Map()
  if (channelResults.length > 0) {
    channelResults[0].values.forEach((row) => {
      try {
        const channelArray = JSON.parse(row[0] || '[]')
        channelArray.forEach((channel) => {
          channelCounts.set(channel, (channelCounts.get(channel) || 0) + 1)
        })
      } catch {
        console.warn('Failed to parse channels:', row[0])
      }
    })
  }

  // Convert to sorted arrays
  channels.value = Array.from(channelCounts.keys()).sort()
  channelsWithCounts.value = Array.from(channelCounts.entries())
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => {
      // Sort by count (descending) then by name (ascending)
      if (a.count !== b.count) {
        return b.count - a.count
      }
      return a.name.localeCompare(b.name)
    })

  // Get all unique tags with counts
  const tagResults = database.exec(
    "SELECT tags FROM games WHERE tags IS NOT NULL AND tags != '[]' AND is_absorbed = 0",
  )
  const tagCounts = new Map()
  if (tagResults.length > 0) {
    tagResults[0].values.forEach((row) => {
      try {
        const tags = JSON.parse(row[0] || '[]')
        tags.forEach((tag) => {
          tagCounts.set(tag, (tagCounts.get(tag) || 0) + 1)
        })
      } catch {
        console.warn('Failed to parse tags:', row[0])
      }
    })
  }

  // Convert to sorted array of tag objects with counts
  allTags.value = Array.from(tagCounts.entries())
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => {
      // Sort by count (descending) then by name (ascending)
      if (a.count !== b.count) {
        return b.count - a.count
      }
      return a.name.localeCompare(b.name)
    })
}

const filteredGames: Ref<AppGameData[]> = ref([])

const buildSQLQuery = (
  filterValues: AppFilters,
): { query: string; params: (string | number)[] } => {
  console.log('Building query with filters:', filterValues)

  // Performance optimization: Track which filters are active to optimize query order
  // These variables can be used for future query optimization

  let query = `
        SELECT g.*,
               gv.video_title as latest_video_title,
               gv.video_id as latest_video_id
        FROM games g
        LEFT JOIN game_videos gv ON g.id = gv.game_id
        AND gv.video_date = g.latest_video_date
        WHERE 1=1
      `
  const params = []

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

  // Tag filter - support both legacy single tag and new multi-tag
  // Note: These are expensive LIKE queries on JSON columns - consider placing them later for better performance
  if (filterValues.selectedTags && filterValues.selectedTags.length > 0) {
    // Multi-tag filtering with AND/OR logic
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
  } else if (filterValues.tag && filterValues.tag.trim()) {
    // Legacy single tag support for backward compatibility
    query += ' AND g.tags LIKE ?'
    params.push(`%"${filterValues.tag}"%`)
  }

  // Channel filter - support both legacy single channel and new multi-channel
  // Note: These are expensive LIKE queries on JSON columns - consider placing them later for better performance
  if (
    filterValues.selectedChannels &&
    filterValues.selectedChannels.length > 0
  ) {
    // Multi-channel filtering with OR logic (games featured by ANY selected channel)
    const channelConditions = filterValues.selectedChannels.map(
      () => 'g.unique_channels LIKE ?',
    )
    query += ` AND (${channelConditions.join(' OR ')})`
    filterValues.selectedChannels.forEach((channel) => {
      params.push(`%"${channel}"%`)
    })
  } else if (filterValues.channel && filterValues.channel.trim()) {
    // Legacy single channel support for backward compatibility
    query += ' AND g.unique_channels LIKE ?'
    params.push(`%"${filterValues.channel}"%`)
  }

  // Price-based filtering
  if (filterValues.priceFilter) {
    const priceFilter = filterValues.priceFilter
    const currencyField =
      filterValues.currency === 'usd' ? 'price_usd' : 'price_eur'

    // Handle free games inclusion
    if (!priceFilter.includeFree) {
      query += ' AND (g.is_free = 0 OR g.is_free IS NULL)'
    }

    // Handle price range filtering for paid games
    if (
      priceFilter.minPrice > 0 ||
      priceFilter.maxPrice < PRICING.DEFAULT_MAX_PRICE
    ) {
      // Create a combined condition for price filtering
      const priceConditions = []

      // Free games condition (if including free games and min price is 0)
      if (priceFilter.includeFree && priceFilter.minPrice === 0) {
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
  if (filterValues.timeFilter && filterValues.timeFilter.type) {
    const timeFilter = filterValues.timeFilter

    if (
      timeFilter.type === 'video' &&
      (timeFilter.startDate || timeFilter.endDate)
    ) {
      // Filter by video publication date
      if (timeFilter.startDate && timeFilter.endDate) {
        query += ' AND g.latest_video_date >= ? AND g.latest_video_date <= ?'
        params.push(timeFilter.startDate + 'T00:00:00')
        params.push(timeFilter.endDate + 'T23:59:59')
      } else if (timeFilter.startDate) {
        query += ' AND g.latest_video_date >= ?'
        params.push(timeFilter.startDate + 'T00:00:00')
      } else if (timeFilter.endDate) {
        query += ' AND g.latest_video_date <= ?'
        params.push(timeFilter.endDate + 'T23:59:59')
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

      switch (timeFilter.smartLogic) {
        case 'release-and-video-recent':
          // Recently released games with video coverage
          query += ' AND g.release_date_sortable IS NOT NULL'
          query += ' AND g.release_date_sortable >= ?'
          query += ' AND g.latest_video_date >= ?'
          params.push(
            parseInt(
              thirtyDaysAgo.toISOString().slice(0, 10).replace(/-/g, ''),
            ),
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
    }
  }

  // Advanced Sorting Logic
  const orderByClause = buildSortClause(filterValues)
  query += ` ORDER BY ${orderByClause}`

  return { query, params }
}

const buildSortClause = (filterValues: AppFilters): string => {
  // Handle advanced sorting with multi-criteria
  if (filterValues.sortBy === 'advanced' && filterValues.sortSpec) {
    return buildAdvancedSortClause(filterValues.sortSpec)
  }

  // Handle smart discovery sorting presets
  if (isSmartSortPreset(filterValues.sortBy)) {
    return buildSmartSortClause(filterValues.sortBy)
  }

  // Traditional single-criteria sorting
  const sortMappings = {
    'rating-score': 'positive_review_percentage DESC',
    'rating-category':
      'review_summary_priority ASC, positive_review_percentage DESC, review_count DESC',
    date: 'latest_video_date DESC',
    name: 'name ASC',
    'release-new': 'release_date_sortable DESC',
    'release-old': 'release_date_sortable ASC',
  }

  return sortMappings[filterValues.sortBy] || 'latest_video_date DESC'
}

const buildAdvancedSortClause = (sortSpec: any): string => {
  const clauses = []

  // Primary sorting criteria
  const primaryClause = getSortFieldClause(
    sortSpec.primary.field,
    sortSpec.primary.direction,
  )
  if (primaryClause) {
    clauses.push(primaryClause)
  }

  // Secondary sorting criteria
  if (sortSpec.secondary) {
    const secondaryClause = getSortFieldClause(
      sortSpec.secondary.field,
      sortSpec.secondary.direction,
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

const getSortFieldClause = (
  field: string,
  direction: string,
): string | null => {
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

const isSmartSortPreset = (sortBy: string): boolean => {
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

const buildSmartSortClause = (sortBy: string): string => {
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

const executeQuery = (db: Database): void => {
  monitorDatabaseQuery('Multi-filter Game Query', () => {
    const { query, params } = buildSQLQuery(filters.value)
    console.log('Executing query:', query)
    console.log('With params:', params)

    // Check for undefined params
    params.forEach((param, index) => {
      if (param === undefined) {
        console.error(`Parameter ${index} is undefined!`)
      }
    })

    const results = db.exec(query, params)
    processQueryResults(results)
  })
}

const processQueryResults = (results: any[]): void => {
  if (results.length > 0) {
    const processedGames: AppGameData[] = []

    // First pass: collect all games and build a lookup for parent data resolution
    const allGameData: any[] = []
    const parentGameLookup = new Map<string, any>()

    results[0].values.forEach((row: any[]) => {
      const columns = results[0].columns
      const gameData: any = {}

      columns.forEach((col, index) => {
        gameData[col] = row[index]
      })

      allGameData.push(gameData)

      // Build parent lookup for absorbed games
      if (!gameData.is_absorbed) {
        parentGameLookup.set(gameData.game_key, gameData)
      }
    })

    // Second pass: process games and resolve parent data for absorbed games
    allGameData.forEach((gameData) => {
      // Parse JSON columns
      try {
        gameData.genres = JSON.parse(gameData.genres || '[]')
        gameData.tags = JSON.parse(gameData.tags || '[]')
        gameData.developers = JSON.parse(gameData.developers || '[]')
        gameData.publishers = JSON.parse(gameData.publishers || '[]')
        gameData.unique_channels = JSON.parse(gameData.unique_channels || '[]')
      } catch {
        console.warn('Failed to parse JSON columns for game:', gameData.name)
      }

      // Parse JSON fields that may contain display links
      try {
        gameData.display_links = gameData.display_links
          ? JSON.parse(gameData.display_links)
          : null
      } catch {
        gameData.display_links = null
      }

      // For absorbed games, supplement with parent game data where needed
      if (gameData.is_absorbed && gameData.absorbed_into) {
        const parentData = parentGameLookup.get(gameData.absorbed_into)
        if (parentData) {
          // Use parent's review data if absorbed game has insufficient data
          if (
            !gameData.review_summary ||
            gameData.review_summary === 'No user reviews'
          ) {
            gameData.review_summary = parentData.review_summary
            gameData.positive_review_percentage =
              parentData.positive_review_percentage
            gameData.review_count = parentData.review_count
            gameData.review_summary_priority =
              parentData.review_summary_priority
          }

          // Use parent's header image if absorbed game doesn't have one
          if (!gameData.header_image && parentData.header_image) {
            gameData.header_image = parentData.header_image
          }

          // Use parent's release date if absorbed game doesn't have one
          if (!gameData.release_date && parentData.release_date) {
            gameData.release_date = parentData.release_date
          }
        }
      }

      // Create game object matching the original data structure
      const game: AppGameData = {
        id: gameData.id,
        game_key: gameData.game_key || '',
        name: gameData.name,
        steam_app_id: gameData.steam_app_id,
        header_image: gameData.header_image,
        price_eur: gameData.price_eur,
        price_usd: gameData.price_usd,
        price_final: gameData.price_final,
        is_free: gameData.is_free,
        release_date: gameData.release_date,
        release_date_sortable: gameData.release_date_sortable,
        review_summary: gameData.review_summary,
        review_summary_priority: gameData.review_summary_priority,
        positive_review_percentage: gameData.positive_review_percentage,
        review_count: gameData.review_count,
        steam_url: gameData.steam_url,
        itch_url: gameData.itch_url,
        crazygames_url: gameData.crazygames_url,
        demo_steam_app_id: gameData.demo_steam_app_id,
        demo_steam_url: gameData.demo_steam_url,
        display_links: gameData.display_links,
        display_price: gameData.display_price,
        tags: gameData.tags || [],
        genres: gameData.genres || [],
        developers: gameData.developers || [],
        publishers: gameData.publishers || [],
        platform: gameData.platform,
        last_updated: gameData.last_updated,
        latest_video_title: gameData.latest_video_title,
        latest_video_id: gameData.latest_video_id,
        latest_video_date: gameData.latest_video_date,
        newest_video_date: gameData.latest_video_date,
        unique_channels: gameData.unique_channels || [],
        video_count: gameData.video_count || 0,
        coming_soon: gameData.coming_soon,
        is_early_access: gameData.is_early_access,
        is_demo: gameData.is_demo,
        planned_release_date: gameData.planned_release_date,
        insufficient_reviews: gameData.insufficient_reviews,
        is_inferred_summary: gameData.is_inferred_summary,
        review_tooltip: gameData.review_tooltip,
        recent_review_percentage: gameData.recent_review_percentage,
        recent_review_count: gameData.recent_review_count,
        recent_review_summary: gameData.recent_review_summary,
        is_absorbed: gameData.is_absorbed,
        absorbed_into: gameData.absorbed_into,
      }

      processedGames.push(game)
    })

    filteredGames.value = processedGames
    console.log(`✓ Processed ${processedGames.length} games`)

    // Update debug info after games are rendered
    if (isDevelopment) {
      nextTick(() => {
        setTimeout(updateGridDebugInfo, TIMING.DEBUG_UPDATE_DELAY)
      })
    }
  } else {
    filteredGames.value = []
    console.log('✓ No games found matching filters')
  }
}

let db: Database | null = null

const loadDatabase = async (): Promise<void> => {
  await databaseManager.init()
  db = databaseManager.getDatabase()
}

const updateDatabaseStatus = (): void => {
  const stats = databaseManager.getStats()
  if (stats) {
    databaseStatus.value.connected = true
    databaseStatus.value.games = stats.games
    databaseStatus.value.lastGenerated = stats.lastModified
      ? new Date(stats.lastModified)
      : null
    databaseStatus.value.lastChecked = stats.lastCheckTime
  } else {
    databaseStatus.value.connected = false
    databaseStatus.value.games = 0
    databaseStatus.value.lastGenerated = null
    databaseStatus.value.lastChecked = null
  }
}

const formatTimestamp = (
  timestamp: Date | string | null,
  useOld = false,
): string => {
  if (!timestamp) {
    return 'Unknown'
  }
  const date = new Date(timestamp)
  const now = currentTime.value // Use reactive current time
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / TIMING.MINUTE_IN_MS)
  const diffHours = Math.floor(diffMs / TIMING.HOUR_IN_MS)

  const suffix = useOld ? ' old' : ' ago'

  if (diffMins < 1) {
    return 'just now'
  }
  if (diffMins < 60) {
    return `${diffMins}m${suffix}`
  }
  if (diffHours < 24) {
    return `${diffHours}h${suffix}`
  }
  return date.toLocaleDateString()
}

const formatExactTimestamp = (timestamp: Date | string | null): string => {
  if (!timestamp) {
    return 'Unknown'
  }
  const date = new Date(timestamp)
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const onDatabaseUpdate = (database: Database): void => {
  db = database
  loadGameStats(db)
  loadChannelsAndTags(db)
  executeQuery(db)
  updateDatabaseStatus()
  console.log('🔄 UI updated with new database')
}

const onVersionMismatch = (versionInfo: VersionMismatchInfo): void => {
  versionMismatchInfo.value = versionInfo
  showVersionMismatch.value = true
  console.warn('🔄 App version mismatch - reload recommended')
}

const reloadApp = (): void => {
  window.location.reload()
}

const dismissVersionMismatch = (): void => {
  showVersionMismatch.value = false
}

const testVersionMismatch = (): void => {
  console.log('🧪 User clicked test version mismatch button')
  databaseManager.testVersionMismatch()
}

const updateGridDebugInfo = (): void => {
  if (!gameGrid.value || !isDevelopment) {
    return
  }

  const gridElement = gameGrid.value
  const containerElement = gridElement.closest('.container')
  const mainContentElement = gridElement.closest('.flex-1')

  const viewport = {
    width: window.innerWidth,
    height: window.innerHeight,
  }

  const containerRect = containerElement?.getBoundingClientRect()
  const mainContentRect = mainContentElement?.getBoundingClientRect()
  const gridRect = gridElement.getBoundingClientRect()

  const computedStyles = window.getComputedStyle(gridElement)

  console.log('🔧 Grid Debug:', {
    viewport,
    container: containerRect?.width,
    mainContent: mainContentRect?.width,
    grid: gridRect?.width,
    gridColumns: computedStyles.gridTemplateColumns,
    gridGap: computedStyles.gap,
    availableSpace:
      mainContentRect?.width -
      parseFloat(computedStyles.paddingLeft) -
      parseFloat(computedStyles.paddingRight),
  })
}

const loadGames = async (): Promise<void> => {
  try {
    // Check if database is already loaded (from HMR preservation)
    if (!databaseManager.isLoaded()) {
      await loadDatabase()
    } else {
      // Reuse existing database
      db = databaseManager.getDatabase()
    }

    // Set up listener for database updates (safe to call multiple times)
    databaseManager.addUpdateListener(onDatabaseUpdate)
    databaseManager.addVersionMismatchListener(onVersionMismatch)

    loadGameStats(db)
    loadChannelsAndTags(db)
    updateDatabaseStatus()

    // Load filters from URL before executing query
    loadFiltersFromURL()

    executeQuery(db)

    // Process deeplink after loading games
    await nextTick()
    await processDeeplink()
  } catch (err) {
    console.error('Error loading database:', err)
    error.value = err.message
  } finally {
    loading.value = false
  }
}

const processDeeplink = async (): Promise<void> => {
  const hash = window.location.hash
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
    targetGame = filteredGames.value.find(
      (game) => game.itch_url && game.itch_url.includes(`${gameId}.itch.io`),
    )
  } else if (platform === 'crazygames') {
    targetGame = filteredGames.value.find(
      (game) =>
        game.crazygames_url &&
        game.crazygames_url.includes(`crazygames.com/game/${gameId}`),
    )
  }

  if (!targetGame) {
    console.warn('Game not found:', platform, gameId)
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
      platform: platform,
      releaseStatus: 'all',
      rating: '0',
      tag: '',
      channel: '',
      sortBy: filters.value.sortBy,
      currency: filters.value.currency,
      crossPlatform: false,
      hiddenGems: false,
      selectedTags: [],
      tagLogic: 'and',
      selectedChannels: [],
      sortSpec: null,
      timeFilter: null,
      priceFilter: { minPrice: 0, maxPrice: 1000, includeFree: true },
    }

    filters.value = newFilters

    // Re-execute query with new filters
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

const clearHighlight = (): void => {
  highlightedGameId.value = null
}

const handleTagClick = (tag: string): void => {
  // Add the clicked tag to the selected tags
  const currentTags = filters.value.selectedTags || []
  if (!currentTags.includes(tag)) {
    const newFilters = {
      ...filters.value,
      selectedTags: [...currentTags, tag],
      tag: currentTags.length === 0 ? tag : '', // Keep legacy field updated for backward compatibility
    }
    updateFilters(newFilters)
  }
}

const updateFilters = (newFilters: Partial<AppFilters>): void => {
  monitorFilterUpdate('Complete Filter Update', () => {
    filters.value = { ...filters.value, ...newFilters }
    updateURLParams(filters.value)
    if (db) {
      executeQuery(db)
    }
  })
}

const handleSortChange = (sortData: SortChangeData): void => {
  filters.value.sortBy = sortData.sortBy
  filters.value.sortSpec = sortData.sortSpec
  updateURLParams(filters.value)
  if (db) {
    executeQuery(db)
  }
}

const updateURLParams = (filterValues: AppFilters): void => {
  const url = new URL(window.location.href)

  // Remove null/undefined values and update URL
  const params = {
    release:
      filterValues.releaseStatus !== 'all' ? filterValues.releaseStatus : null,
    platform: filterValues.platform !== 'all' ? filterValues.platform : null,
    rating: filterValues.rating !== '0' ? filterValues.rating : null,
    crossPlatform: filterValues.crossPlatform ? 'true' : null,
    hiddenGems: filterValues.hiddenGems ? 'true' : null,
    // Support both legacy single tag and new multi-tag format
    tags:
      filterValues.selectedTags && filterValues.selectedTags.length > 0
        ? filterValues.selectedTags.join(',')
        : filterValues.tag || null,
    tagLogic:
      filterValues.selectedTags &&
      filterValues.selectedTags.length > 1 &&
      filterValues.tagLogic !== 'and'
        ? filterValues.tagLogic
        : null,
    // Support both legacy single channel and new multi-channel format
    channels:
      filterValues.selectedChannels && filterValues.selectedChannels.length > 0
        ? filterValues.selectedChannels.join(',')
        : filterValues.channel || null,
    sort: filterValues.sortBy !== 'date' ? filterValues.sortBy : null,
    sortSpec: filterValues.sortSpec
      ? JSON.stringify(filterValues.sortSpec)
      : null,
    currency: filterValues.currency !== 'eur' ? filterValues.currency : null,
    // Time filter parameters
    timeType: filterValues.timeFilter?.type || null,
    timePreset: filterValues.timeFilter?.preset || null,
    timeStart: filterValues.timeFilter?.startDate || null,
    timeEnd: filterValues.timeFilter?.endDate || null,
    timeLogic: filterValues.timeFilter?.smartLogic || null,
    // Price filter parameters
    priceMin:
      filterValues.priceFilter?.minPrice > 0
        ? filterValues.priceFilter.minPrice
        : null,
    priceMax:
      filterValues.priceFilter?.maxPrice < PRICING.DEFAULT_MAX_PRICE
        ? filterValues.priceFilter.maxPrice
        : null,
    includeFree:
      filterValues.priceFilter?.includeFree === false ? 'false' : null,
  }

  Object.keys(params).forEach((key) => {
    if (params[key] === null || params[key] === undefined) {
      url.searchParams.delete(key)
    } else {
      url.searchParams.set(key, params[key])
    }
  })

  // Update URL without page reload
  window.history.replaceState({}, '', url)
}

const loadFiltersFromURL = (): void => {
  const urlParams = new URLSearchParams(window.location.search)

  // Load each filter from URL if present
  const urlFilters: Partial<AppFilters> = {}

  if (urlParams.has('release')) {
    urlFilters.releaseStatus = urlParams.get('release')
  }

  if (urlParams.has('platform')) {
    urlFilters.platform = urlParams.get('platform')
  }

  if (urlParams.has('rating')) {
    urlFilters.rating = urlParams.get('rating')
  }

  if (urlParams.has('crossPlatform')) {
    urlFilters.crossPlatform = urlParams.get('crossPlatform') === 'true'
  }

  if (urlParams.has('hiddenGems')) {
    urlFilters.hiddenGems = urlParams.get('hiddenGems') === 'true'
  }

  // Handle both new 'tags' parameter and legacy 'tag' parameter
  if (urlParams.has('tags')) {
    const tagsParam = urlParams.get('tags')
    if (tagsParam && tagsParam.includes(',')) {
      // Multi-tag format: "tag1,tag2,tag3"
      urlFilters.selectedTags = tagsParam.split(',').filter((tag) => tag.trim())
      urlFilters.tag = '' // Clear legacy field
    } else if (tagsParam) {
      // Single tag in new format
      urlFilters.selectedTags = [tagsParam]
      urlFilters.tag = tagsParam // Keep for backward compatibility
    }
  } else if (urlParams.has('tag')) {
    // Legacy single tag support
    const tagParam = urlParams.get('tag')
    urlFilters.tag = tagParam
    urlFilters.selectedTags = tagParam ? [tagParam] : []
  }

  if (urlParams.has('tagLogic')) {
    const tagLogic = urlParams.get('tagLogic')
    if (tagLogic === 'and' || tagLogic === 'or') {
      urlFilters.tagLogic = tagLogic
    }
  }

  // Handle both new 'channels' parameter and legacy 'channel' parameter
  if (urlParams.has('channels')) {
    const channelsParam = urlParams.get('channels')
    if (channelsParam && channelsParam.includes(',')) {
      // Multi-channel format: "channel1,channel2,channel3"
      urlFilters.selectedChannels = channelsParam
        .split(',')
        .filter((channel) => channel.trim())
      urlFilters.channel = '' // Clear legacy field
    } else if (channelsParam) {
      // Single channel in new format
      urlFilters.selectedChannels = [channelsParam]
      urlFilters.channel = channelsParam // Keep for backward compatibility
    }
  } else if (urlParams.has('channel')) {
    // Legacy single channel support
    const channelParam = urlParams.get('channel')
    urlFilters.channel = channelParam
    urlFilters.selectedChannels = channelParam ? [channelParam] : []
  }

  if (urlParams.has('sort')) {
    urlFilters.sortBy = urlParams.get('sort')
  }

  if (urlParams.has('sortSpec')) {
    try {
      urlFilters.sortSpec = JSON.parse(urlParams.get('sortSpec'))
    } catch {
      console.warn('Invalid sortSpec in URL parameters')
    }
  }

  if (urlParams.has('currency')) {
    const currency = urlParams.get('currency')
    if (currency === 'eur' || currency === 'usd') {
      urlFilters.currency = currency
    }
  }

  // Handle time filter parameters
  if (
    urlParams.has('timeType') ||
    urlParams.has('timePreset') ||
    urlParams.has('timeStart') ||
    urlParams.has('timeEnd') ||
    urlParams.has('timeLogic')
  ) {
    urlFilters.timeFilter = {
      type: urlParams.get('timeType') || null,
      preset: urlParams.get('timePreset') || null,
      startDate: urlParams.get('timeStart') || null,
      endDate: urlParams.get('timeEnd') || null,
      smartLogic: urlParams.get('timeLogic') || null,
    }
  }

  // Handle price filter parameters
  if (
    urlParams.has('priceMin') ||
    urlParams.has('priceMax') ||
    urlParams.has('includeFree')
  ) {
    urlFilters.priceFilter = {
      minPrice: urlParams.has('priceMin')
        ? parseFloat(urlParams.get('priceMin'))
        : 0,
      maxPrice: urlParams.has('priceMax')
        ? parseFloat(urlParams.get('priceMax'))
        : PRICING.DEFAULT_MAX_PRICE,
      includeFree: urlParams.get('includeFree') !== 'false',
    }
  }

  // Update filters with URL values
  if (Object.keys(urlFilters).length > 0) {
    filters.value = { ...filters.value, ...urlFilters }
  }
}

onMounted((): void => {
  loadGames()

  // Set up keyboard handler for clearing highlights
  const handleKeydown = (e: KeyboardEvent): void => {
    if (e.key === 'Escape') {
      clearHighlight()
    }
  }

  document.addEventListener('keydown', handleKeydown)

  // Update timestamps at configured interval
  const timestampTimer = setInterval(() => {
    currentTime.value = new Date()
  }, TIMING.TIMESTAMP_UPDATE_INTERVAL)

  // Store timer reference for cleanup
  ;(window as any).timestampTimer = timestampTimer

  // Set up debug info updates for development
  if (isDevelopment) {
    // Update debug info on resize
    const handleResize = (): void => {
      setTimeout(updateGridDebugInfo, TIMING.RESIZE_DEBOUNCE_DELAY) // Debounce slightly
    }

    window.addEventListener('resize', handleResize)

    // Initial debug info after components are mounted
    setTimeout(updateGridDebugInfo, TIMING.INITIAL_DEBUG_DELAY)

    // Store for cleanup
    ;(window as any).handleResize = handleResize
  }
})

onUnmounted((): void => {
  // Cleanup database manager
  if (databaseManager.isLoaded()) {
    databaseManager.removeUpdateListener(onDatabaseUpdate)
    databaseManager.removeVersionMismatchListener(onVersionMismatch)

    // Only destroy if not in HMR mode
    if (!import.meta.hot) {
      databaseManager.destroy()
    }
  }

  // Cleanup timestamp timer
  if ((window as any).timestampTimer) {
    clearInterval((window as any).timestampTimer)
    ;(window as any).timestampTimer = null
  }

  // Cleanup resize handler
  if ((window as any).handleResize) {
    window.removeEventListener('resize', (window as any).handleResize)
    ;(window as any).handleResize = null
  }

  // Remove keyboard handler
  const handleKeydown = (e: KeyboardEvent): void => {
    if (e.key === 'Escape') {
      clearHighlight()
    }
  }
  document.removeEventListener('keydown', handleKeydown)
})

// Export reactive state and methods for template
defineExpose({
  loading,
  error,
  filters,
  channels,
  channelsWithCounts,
  allTags,
  filteredGames,
  gameStats,
  gameGrid,
  highlightedGameId,
  databaseStatus,
  isDevelopment,
  databaseManager,
  formatTimestamp,
  formatExactTimestamp,
  updateFilters,
  clearHighlight,
  handleTagClick,
  showVersionMismatch,
  versionMismatchInfo,
  reloadApp,
  dismissVersionMismatch,
  testVersionMismatch,
  updateGridDebugInfo,
  sidebarCollapsed,
  handleSortChange,
  LAYOUT,
})

// HMR support - accept module updates
if (import.meta.hot) {
  import.meta.hot.accept()
}
</script>

<style scoped>
.game-grid {
  /* Ensure proper grid container behavior */
  display: grid;
  grid-template-columns: repeat(
    auto-fit,
    minmax(v-bind('LAYOUT.CARD_MIN_WIDTH'), 1fr)
  );
  gap: 1.25rem; /* 20px - matches gap-5 */
  width: 100%;
  min-width: 0;

  /* Force grid to use all available space */
  justify-content: stretch;
  align-items: stretch;
  grid-auto-rows: auto;
}

/* Ensure grid items expand to fill their allocated space */
.game-grid > * {
  width: 100%;
  min-width: 0;
  max-width: none;
  justify-self: stretch;
}

/* Debug: Console-only debugging in development */

/* Responsive grid adjustments for optimal card expansion */
@media (min-width: 1280px) and (max-width: v-bind('LAYOUT.CONTAINER_MAX_WIDTH_PX - 1 + "px"')) {
  .game-grid {
    /* Force equal columns where auto-fit struggles to expand cards properly */
    grid-template-columns: repeat(3, 1fr);
  }
}

/* At very large viewports, allow auto-fit to determine optimal columns */
@media (min-width: v-bind('LAYOUT.CONTAINER_MAX_WIDTH')) {
  .game-grid {
    grid-template-columns: repeat(
      auto-fit,
      minmax(v-bind('LAYOUT.CARD_MIN_WIDTH'), 1fr)
    );
  }
}
</style>
