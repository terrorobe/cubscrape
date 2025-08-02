<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, type Ref } from 'vue'
import GameFilters from './components/GameFilters.vue'
import GameDiscoveryContainer, {
  type SearchState,
  type PaginationConfig,
} from './components/GameDiscoveryContainer.vue'
import DatabaseStatus from './components/DatabaseStatus.vue'
import ToastNotifications from './components/ToastNotifications.vue'
import { useGameSearch } from './composables/useGameSearch'
import { databaseManager } from './utils/databaseManager'
import { usePerformanceMonitoring } from './utils/performanceMonitor'
import { debug } from './utils/debug'
import type { DatabaseQueryResult } from './services/GameDatabaseService'
import {
  gameDataProcessingService,
  type ProcessedGameData,
} from './services/GameDataProcessingService'
import { queryBuilderService } from './services/QueryBuilderService'
import { useURLState } from './composables/useURLState'
import { useDeepLinking, type AppFilters } from './composables/useDeepLinking'
import { useToast } from './composables/useToast'
import { useFilterState } from './composables/useFilterState'
import { useDatabaseLifecycle } from './composables/useDatabaseLifecycle'
import type { Database } from 'sql.js'
import { TIMING, LAYOUT } from './config/index'

// Component interfaces

// Component state
const currentTime: Ref<Date> = ref(new Date())
const sidebarCollapsed: Ref<boolean> = ref(false)
const { monitorDatabaseQuery } = usePerformanceMonitoring()

// Database Lifecycle Management
const {
  db,
  databaseStatus,
  gameStats,
  channels,
  channelsWithCounts,
  allTags,
  showVersionMismatch,
  versionMismatchInfo,
  loading,
  error,
  initialize: initializeDatabase,
  executeQuery: databaseExecuteQuery,
  loadChannelsOnly,
  testVersionMismatch,
  reloadApp,
  dismissVersionMismatch,
} = useDatabaseLifecycle()

// Initialize search state with debounced query execution callback
const {
  searchQuery,
  searchInVideoTitles,
  debouncedSearchQuery,
  buildSearchQuery,
  setSearchState,
} = useGameSearch({ debounceDelay: 300 }, (_searchState) => {
  // This callback is triggered after debouncing completes
  // Execute query with the debounced search terms
  const currentDb = db.get()
  if (currentDb) {
    executeQuery(currentDb)
  }
})
// URL State Management
const urlState = useURLState()

// Pagination will be set up after filteredGames is declared
const isDevelopment: boolean = import.meta.env.DEV

const filteredGames: Ref<ProcessedGameData[]> = ref([])

// Pagination state management (now handled inside GameDiscoveryContainer)
const currentPage = ref(1)
const pageSize = ref(150)

// Pagination change handler for URL updates
const handlePaginationChange = (paginationData: {
  currentPage: number
  pageSize: number
}) => {
  currentPage.value = paginationData.currentPage
  pageSize.value = paginationData.pageSize
}

// Filter State Management - initialized after pagination
const {
  filters,
  updateFilters,
  handleTagClick,
  handleSortChange: filterHandleSortChange,
  toQueryFilters,
} = useFilterState({
  executeQuery: (database: Database) => executeQuery(database),
  updateURLParams: (filterValues, currentPageRef, pageSizeRef) =>
    urlState.updateURLParams(filterValues, currentPageRef, pageSizeRef),
  currentPage,
  pageSize,
  database: () => db.get(),
})

// Toast notifications
const { toasts, showToast, removeToast } = useToast()

// Create grouped props for GameDiscoveryContainer
const searchState = computed<SearchState>(() => ({
  query: searchQuery.value,
  searchInVideoTitles: searchInVideoTitles.value,
}))

const paginationConfig = computed<PaginationConfig>(() => ({
  initialPageSize: 150,
  enableLoadMore: true,
  onPageChange: () => {
    // Handle URL updates when pagination changes
    urlState.updateURLParams(filters.value, currentPage, pageSize)
  },
}))

const buildSQLQuery = (): { query: string; params: (string | number)[] } => {
  // Use the filter state composable to get query filters
  const queryFilters = toQueryFilters()

  // Use the query builder service
  return queryBuilderService.buildSQLQuery(queryFilters, buildSearchQuery)
}

const executeQuery = (database: Database): void => {
  monitorDatabaseQuery('Multi-filter Game Query', () => {
    const { query, params } = buildSQLQuery()
    const results = databaseExecuteQuery(database, query, params)
    processQueryResults(results)
  })
}

interface ExtendedWindow extends Window {
  timestampTimer?: NodeJS.Timeout
  handleResize?: () => void
}

const processQueryResults = (results: DatabaseQueryResult[]): void => {
  // Use the game data processing service to transform raw results
  const processedGames = gameDataProcessingService.processQueryResults(results)
  filteredGames.value = processedGames

  if (isDevelopment && processedGames.length > 0) {
    nextTick(() => {
      setTimeout(updateGridDebugInfo, TIMING.DEBUG_UPDATE_DELAY)
    })
  }
}

// Deep Linking System (initialized after db and executeQuery are defined)
const {
  highlightedGameId,
  processDeeplink,
  clearHighlight,
  copyCurrentFiltersLink,
} = useDeepLinking({
  filteredGames,
  filters: filters as Ref<AppFilters>, // Type compatibility bridge
  executeQuery,
  getDb: () => db.get(),
  currentPage,
  pageSize,
})

// Custom database update handler that triggers UI updates
const onDatabaseUpdate = (database: Database | null): void => {
  if (!database) {
    debug.warn('⚠️ Database update received null database in App.vue')
    return
  }
  executeQuery(database)
  debug.log('🔄 UI updated with new database')
}

const updateGridDebugInfo = (): void => {
  if (!isDevelopment) {
    return
  }
  const gridElement = document.querySelector('.game-grid')
  if (gridElement) {
    debug.log('🔧 Grid updated')
  }
}

const loadGames = async (): Promise<void> => {
  try {
    // Initialize database lifecycle
    await initializeDatabase()

    // Set up custom database update listener for UI-specific actions
    databaseManager.addUpdateListener(onDatabaseUpdate)

    // Load filters from URL before executing query
    const urlFilters = urlState.loadFiltersFromURL(
      searchQuery,
      debouncedSearchQuery,
      searchInVideoTitles,
      currentPage,
      pageSize,
    )

    // Update search state if URL contains search parameters
    if (
      urlFilters.searchQuery !== undefined ||
      urlFilters.searchInVideoTitles !== undefined
    ) {
      setSearchState({
        searchQuery: urlFilters.searchQuery || '',
        searchInVideoTitles: urlFilters.searchInVideoTitles || false,
        debouncedSearchQuery: urlFilters.searchQuery || '',
      })
    }
    if (Object.keys(urlFilters).length > 0) {
      updateFilters(urlFilters as Record<string, unknown>)
    } // Type compatibility bridge

    // Execute initial query if database is available
    const currentDb = db.get()
    if (currentDb) {
      executeQuery(currentDb)
    }

    await nextTick()
    await processDeeplink()
  } catch (err) {
    debug.error('Error loading database:', err)
    // Error is already handled by the composable, no need to set it here
  }
}

const handleSortChange = filterHandleSortChange

onMounted((): void => {
  loadGames()

  const handleKeydown = (e: KeyboardEvent): void => {
    if (e.key === 'Escape') {
      clearHighlight()
    }
  }

  document.addEventListener('keydown', handleKeydown)

  const timestampTimer = setInterval(() => {
    currentTime.value = new Date()
  }, TIMING.TIMESTAMP_UPDATE_INTERVAL)

  ;(window as ExtendedWindow).timestampTimer = timestampTimer

  const handleResize = (): void => {
    setTimeout(() => {
      if (isDevelopment) {
        updateGridDebugInfo()
      }
    }, TIMING.RESIZE_DEBOUNCE_DELAY)
  }

  window.addEventListener('resize', handleResize)
  if (isDevelopment) {
    setTimeout(updateGridDebugInfo, TIMING.INITIAL_DEBUG_DELAY)
  }
  ;(window as ExtendedWindow).handleResize = handleResize
})

onUnmounted((): void => {
  // Remove custom database update listener
  if (databaseManager.isLoaded()) {
    databaseManager.removeUpdateListener(onDatabaseUpdate)
  }

  // Database lifecycle cleanup is handled by the composable automatically

  // Cleanup timers and handlers
  const extWindow = window as ExtendedWindow
  if (extWindow.timestampTimer) {
    clearInterval(extWindow.timestampTimer)
    extWindow.timestampTimer = undefined
  }
  if (extWindow.handleResize) {
    window.removeEventListener('resize', extWindow.handleResize)
    extWindow.handleResize = undefined
  }
})

// Search state update handler
const handleSearchStateUpdate = (newSearchState: SearchState): void => {
  setSearchState({
    searchQuery: newSearchState.query,
    searchInVideoTitles: newSearchState.searchInVideoTitles,
  })
  // Update filters for URL state but skip immediate query execution
  // The search composable will handle debounced query execution
  updateFilters(
    {
      searchQuery: newSearchState.query,
      searchInVideoTitles: newSearchState.searchInVideoTitles,
    },
    true,
  ) // skipQuery = true
}

// Sharing functionality with toast feedback
const handleCopyCurrentFiltersLink = async (): Promise<void> => {
  const success = await copyCurrentFiltersLink()
  if (success) {
    showToast('Current filters copied to clipboard!', 'success')
  } else {
    showToast('Failed to copy link. Please try again.', 'error')
  }
}

// HMR support - accept module updates
if (import.meta.hot) {
  import.meta.hot.accept()
}
</script>

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
              :load-channels="loadChannelsOnly"
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
              :load-channels="loadChannelsOnly"
              @filters-changed="updateFilters"
            />
          </div>

          <!-- Database Status -->
          <div class="mb-5">
            <div class="flex justify-center md:justify-end">
              <DatabaseStatus
                :connected="databaseStatus.connected"
                :games="databaseStatus.games"
                :last-generated="databaseStatus.lastGenerated"
                :last-checked="databaseStatus.lastChecked"
                :show-version-mismatch="showVersionMismatch"
                :version-mismatch-info="versionMismatchInfo"
                :is-development="isDevelopment"
                :current-time="currentTime"
                :production-check-interval="
                  databaseManager.PRODUCTION_CHECK_INTERVAL
                "
                @test-version-mismatch="testVersionMismatch"
                @reload-app="reloadApp"
                @dismiss-version-mismatch="dismissVersionMismatch"
              />
            </div>
          </div>

          <!-- Game Discovery Container -->
          <GameDiscoveryContainer
            :search-state="searchState"
            :currency="filters.currency"
            :sort-by="filters.sortBy"
            :sort-spec="filters.sortSpec"
            :selected-tags="filters.selectedTags"
            :filtered-games="filteredGames"
            :highlighted-game-id="
              highlightedGameId ? String(highlightedGameId) : null
            "
            :pagination-config="paginationConfig"
            :loading="loading"
            :error="error"
            @update:search-state="handleSearchStateUpdate"
            @sort-changed="handleSortChange"
            @clear-highlight="clearHighlight"
            @tag-click="handleTagClick"
            @pagination-changed="handlePaginationChange"
            @copy-current-filters-link="handleCopyCurrentFiltersLink"
          />
        </div>
      </div>
    </div>

    <!-- Toast Notifications -->
    <ToastNotifications :toasts="toasts" @remove="removeToast" />
  </div>
</template>
