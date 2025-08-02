/**
 * Database Lifecycle Management Composable
 *
 * Centralizes all database-related state management, lifecycle operations,
 * and event handling. This composable extracts database management logic
 * from App.vue to improve separation of concerns and maintainability.
 *
 * Responsibilities:
 * - Database loading and initialization
 * - Database status management
 * - Game stats loading and management
 * - Channels and tags loading and management
 * - Database event listeners (updates, version mismatches)
 * - Version mismatch handling
 * - Cleanup and resource management
 */

import { ref, onUnmounted, type Ref } from 'vue'
import type { Database } from 'sql.js'
import { databaseManager } from '../utils/databaseManager'
import type { VersionMismatchInfo } from '../utils/databaseManager'
import {
  gameDatabaseService,
  type GameStats,
  type DatabaseQueryResult,
} from '../services/GameDatabaseService'
import type {
  ChannelWithCount,
  TagWithCount,
  VideoData,
} from '../types/database'
import { debug } from '../utils/debug'
import { PRICING } from '../config/index'

/**
 * Database connection status interface
 */
export interface DatabaseStatusData {
  connected: boolean
  games: number
  lastGenerated: Date | null
  lastChecked: Date | null
}

/**
 * Database lifecycle composable options
 */
export interface UseDatabaseLifecycleOptions {
  /** Initial loading state */
  initialLoading?: boolean
}

/**
 * Database Lifecycle Management Composable
 *
 * Provides centralized management of all database-related state and operations.
 * Handles initialization, updates, version management, and cleanup automatically.
 */
export function useDatabaseLifecycle(
  options: UseDatabaseLifecycleOptions = {},
) {
  const { initialLoading = true } = options

  // Core database state
  let db: Database | null = null
  const loading: Ref<boolean> = ref(initialLoading)
  const error: Ref<string | null> = ref(null)

  // Database status state
  const databaseStatus: Ref<DatabaseStatusData> = ref({
    connected: false,
    games: 0,
    lastGenerated: null,
    lastChecked: null,
  })

  // Game data state
  const gameStats: Ref<GameStats> = ref({
    totalGames: 0,
    freeGames: 0,
    maxPrice: PRICING.DEFAULT_MAX_PRICE,
  })

  // Channels and tags state
  const channels: Ref<string[]> = ref([])
  const channelsWithCounts: Ref<ChannelWithCount[]> = ref([])
  const allTags: Ref<TagWithCount[]> = ref([])

  // Version mismatch state
  const showVersionMismatch: Ref<boolean> = ref(false)
  const versionMismatchInfo: Ref<VersionMismatchInfo | null> = ref(null)

  /**
   * Load database from the database service
   */
  const loadDatabase = async (): Promise<void> => {
    try {
      await gameDatabaseService.loadDatabase()
      db = gameDatabaseService.getDatabase()
      debug.log('📊 Database loaded successfully in composable')
    } catch (err) {
      debug.error('❌ Failed to load database in composable:', err)
      throw err
    }
  }

  /**
   * Load game statistics from database
   */
  const loadGameStats = (database: Database): void => {
    try {
      gameStats.value = gameDatabaseService.loadGameStats(database)
      debug.log('📈 Game stats loaded:', gameStats.value)
    } catch (err) {
      debug.error('❌ Failed to load game stats:', err)
      error.value = `Failed to load game statistics: ${err instanceof Error ? err.message : String(err)}`
    }
  }

  /**
   * Load channels and tags from database
   */
  const loadChannelsAndTags = (database: Database): void => {
    try {
      const result = gameDatabaseService.loadChannelsAndTags(database)
      channels.value = result.channels
      channelsWithCounts.value = result.channelsWithCounts
      allTags.value = result.allTags
      debug.log('📺 Loaded channels:', channels.value.length)
      debug.log('🏷️ Loaded tags:', allTags.value.length)
    } catch (err) {
      debug.error('❌ Failed to load channels and tags:', err)
      error.value = `Failed to load channels and tags: ${err instanceof Error ? err.message : String(err)}`
    }
  }

  /**
   * Load only channels from database (for lazy loading)
   */
  const loadChannelsOnly = (): void => {
    if (!db) {
      debug.warn('⚠️ Cannot load channels: database not available')
      return
    }

    try {
      const result = gameDatabaseService.loadChannelsAndTags(db)
      channels.value = result.channels
      channelsWithCounts.value = result.channelsWithCounts
      debug.log('📺 Lazy loaded channels:', channels.value.length)
    } catch (err) {
      debug.error('❌ Failed to load channels:', err)
      error.value = `Failed to load channels: ${err instanceof Error ? err.message : String(err)}`
    }
  }

  /**
   * Load only tags from database (for lazy loading)
   */
  const loadTagsOnly = (): void => {
    if (!db) {
      debug.warn('⚠️ Cannot load tags: database not available')
      return
    }

    try {
      const result = gameDatabaseService.loadChannelsAndTags(db)
      allTags.value = result.allTags
      debug.log('🏷️ Lazy loaded tags:', allTags.value.length)
    } catch (err) {
      debug.error('❌ Failed to load tags:', err)
      error.value = `Failed to load tags: ${err instanceof Error ? err.message : String(err)}`
    }
  }

  /**
   * Load video data for a specific game
   */
  const loadGameVideos = (gameId: string): VideoData[] => {
    if (!db) {
      debug.warn('⚠️ Cannot load game videos: database not available')
      return []
    }

    try {
      return gameDatabaseService.loadGameVideos(db, gameId)
    } catch (err) {
      debug.error('❌ Failed to load game videos:', err)
      error.value = `Failed to load game videos: ${err instanceof Error ? err.message : String(err)}`
      return []
    }
  }

  /**
   * Update database status information
   */
  const updateDatabaseStatus = (): void => {
    try {
      const stats = databaseManager.getStats()
      if (stats) {
        databaseStatus.value.connected = true
        databaseStatus.value.games = stats.games
        databaseStatus.value.lastGenerated = stats.lastModified
          ? new Date(stats.lastModified)
          : null
        databaseStatus.value.lastChecked = stats.lastCheckTime
        debug.log('✅ Database status updated:', {
          games: stats.games,
          lastGenerated: stats.lastModified,
          lastChecked: stats.lastCheckTime,
        })
      } else {
        databaseStatus.value.connected = false
        databaseStatus.value.games = 0
        databaseStatus.value.lastGenerated = null
        databaseStatus.value.lastChecked = null
        debug.warn('⚠️ Database status unavailable')
      }
    } catch (err) {
      debug.error('❌ Failed to update database status:', err)
      databaseStatus.value.connected = false
      databaseStatus.value.games = 0
      databaseStatus.value.lastGenerated = null
      databaseStatus.value.lastChecked = null
    }
  }

  /**
   * Handle database update events from the database manager
   */
  const onDatabaseUpdate = (database: Database | null): void => {
    try {
      debug.log('🔄 Handling database update in composable')
      if (!database) {
        debug.warn('⚠️ Database update received null database')
        return
      }
      db = database
      loadGameStats(db)
      // Only reload data on database update if it was already loaded
      const result = gameDatabaseService.loadChannelsAndTags(db)
      // Only update tags if they were already loaded
      if (allTags.value.length > 0) {
        allTags.value = result.allTags
        debug.log('🏷️ Reloaded tags:', allTags.value.length)
      }
      // Only update channels if they were already loaded
      if (channelsWithCounts.value.length > 0) {
        channels.value = result.channels
        channelsWithCounts.value = result.channelsWithCounts
        debug.log('📺 Reloaded channels:', channels.value.length)
      }
      updateDatabaseStatus()
      debug.log('✅ Database update handled successfully')
    } catch (err) {
      debug.error('❌ Error handling database update:', err)
      error.value = `Failed to handle database update: ${err instanceof Error ? err.message : String(err)}`
    }
  }

  /**
   * Handle version mismatch events from the database manager
   */
  const onVersionMismatch = (versionInfo: VersionMismatchInfo): void => {
    try {
      debug.warn('🔄 App version mismatch detected in composable:', versionInfo)
      versionMismatchInfo.value = versionInfo
      showVersionMismatch.value = true
      debug.log('✅ Version mismatch state updated')
    } catch (err) {
      debug.error('❌ Error handling version mismatch:', err)
    }
  }

  /**
   * Initialize the database lifecycle system
   */
  const initialize = async (): Promise<void> => {
    try {
      loading.value = true
      error.value = null

      // Check if database is already loaded (from HMR preservation)
      if (!databaseManager.isLoaded()) {
        await loadDatabase()
      } else {
        // Reuse existing database
        db = databaseManager.getDatabase()
        debug.log('♻️ Reusing existing database from HMR preservation')
      }

      // Set up listeners for database updates (safe to call multiple times)
      databaseManager.addUpdateListener(onDatabaseUpdate)
      databaseManager.addVersionMismatchListener(onVersionMismatch)

      // Initialize data if database is available
      if (db) {
        loadGameStats(db)
        // Skip loading channels and tags initially - they will be loaded lazily
        updateDatabaseStatus()
      } else {
        throw new Error('Database initialization failed: db is null')
      }

      debug.log('✅ Database lifecycle initialized successfully')
    } catch (err) {
      debug.error('❌ Database lifecycle initialization failed:', err)
      error.value = err instanceof Error ? err.message : String(err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Execute a database query (proxy to service)
   */
  const executeQuery = (
    database: Database,
    query: string,
    params: (string | number)[],
  ): DatabaseQueryResult[] => {
    try {
      return gameDatabaseService.executeQuery(database, query, params)
    } catch (err) {
      debug.error('❌ Query execution failed:', err)
      error.value = `Query execution failed: ${err instanceof Error ? err.message : String(err)}`
      throw err
    }
  }

  /**
   * Get current database instance
   */
  const getDatabase = (): Database | null => db

  /**
   * Force reload the application (for version mismatch resolution)
   */
  const reloadApp = (): void => {
    debug.log('🔄 Reloading application')
    window.location.reload()
  }

  /**
   * Dismiss version mismatch notification
   */
  const dismissVersionMismatch = (): void => {
    debug.log('🔕 Dismissing version mismatch notification')
    showVersionMismatch.value = false
  }

  /**
   * Test version mismatch functionality (development only)
   */
  const testVersionMismatch = (): void => {
    debug.log('🧪 Testing version mismatch functionality')
    void databaseManager.testVersionMismatch()
  }

  /**
   * Check if database is loaded and available
   */
  const isLoaded = (): boolean => db !== null && databaseManager.isLoaded()

  /**
   * Get database statistics
   */
  const getStats = () => databaseManager.getStats()

  /**
   * Cleanup database resources and listeners
   */
  const cleanup = (): void => {
    try {
      debug.log('🧹 Cleaning up database lifecycle resources')

      if (databaseManager.isLoaded()) {
        databaseManager.removeUpdateListener(onDatabaseUpdate)
        databaseManager.removeVersionMismatchListener(onVersionMismatch)

        // Only destroy if not in HMR mode
        if (!import.meta.hot) {
          databaseManager.destroy()
        }
      }

      // Reset state
      db = null
      error.value = null
      showVersionMismatch.value = false
      versionMismatchInfo.value = null

      debug.log('✅ Database lifecycle cleanup completed')
    } catch (err) {
      debug.error('❌ Error during database lifecycle cleanup:', err)
    }
  }

  // Automatic cleanup on component unmount
  onUnmounted(() => {
    cleanup()
  })

  return {
    // State (readonly refs for external consumers)
    db: { get: getDatabase } as const,
    databaseStatus: databaseStatus as Readonly<Ref<DatabaseStatusData>>,
    gameStats: gameStats as Readonly<Ref<GameStats>>,
    channels: channels as Readonly<Ref<string[]>>,
    channelsWithCounts: channelsWithCounts as Readonly<Ref<ChannelWithCount[]>>,
    allTags: allTags as Readonly<Ref<TagWithCount[]>>,
    showVersionMismatch: showVersionMismatch as Readonly<Ref<boolean>>,
    versionMismatchInfo: versionMismatchInfo as Readonly<
      Ref<VersionMismatchInfo | null>
    >,
    loading: loading as Readonly<Ref<boolean>>,
    error: error as Readonly<Ref<string | null>>,

    // Methods
    initialize,
    executeQuery,
    testVersionMismatch,
    reloadApp,
    dismissVersionMismatch,
    isLoaded,
    getStats,
    cleanup,

    // Internal methods (exposed for testing/advanced use)
    loadDatabase,
    loadGameStats,
    loadChannelsAndTags,
    loadChannelsOnly,
    loadTagsOnly,
    loadGameVideos,
    updateDatabaseStatus,
  }
}
