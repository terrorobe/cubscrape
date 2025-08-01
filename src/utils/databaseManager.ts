/**
 * Database manager for both development and production environments
 *
 * Features:
 * - Automatic database reloading in development (via Vite HMR)
 * - Timer-based checking in production
 * - Manual refresh capability
 * - Database change detection via file modification time
 */

import type { Database } from 'sql.js'
import { debug } from './debug'

/**
 * SQL.js Database-like interface for type checking
 */
interface DatabaseLike {
  exec: (sql: string, params?: (string | number)[]) => unknown[]
}

/**
 * Type guard to check if value is sql.js Database
 */
function isDatabase(value: unknown): value is Database {
  return (
    value !== null &&
    typeof value === 'object' &&
    'exec' in value &&
    typeof (value as DatabaseLike).exec === 'function'
  )
}

/**
 * SQL.js Module-like interface for type checking
 */
interface SQLModuleLike {
  Database: new (data?: Uint8Array) => Database
}

/**
 * Initialized SQL.js module type
 */
interface InitializedSQLModule {
  Database: new (data?: Uint8Array) => Database
}

/**
 * Type guard to check if SQL.js module is loaded
 */
function isSQLModule(value: unknown): value is InitializedSQLModule {
  return (
    value !== null &&
    typeof value === 'object' &&
    'Database' in value &&
    typeof (value as SQLModuleLike).Database === 'function'
  )
}

/**
 * SQL.js Query Result interface for type checking
 */
interface QueryResultLike {
  values: (string | number | null)[][]
}

/**
 * Extended window interface for HMR persistence only
 */
interface WindowWithGameDatabase extends Window {
  __databaseManager?: DatabaseManager
}

/**
 * Safely extract single value from query result
 */
function extractSingleValue(
  result: unknown,
  fallback: string | number = '',
): string | number {
  if (
    Array.isArray(result) &&
    result.length > 0 &&
    result[0] &&
    typeof result[0] === 'object' &&
    'values' in result[0]
  ) {
    const queryResult = result[0] as QueryResultLike
    if (
      Array.isArray(queryResult.values) &&
      queryResult.values.length > 0 &&
      Array.isArray(queryResult.values[0]) &&
      queryResult.values[0].length > 0
    ) {
      const value = queryResult.values[0][0]
      return typeof value === 'string' || typeof value === 'number'
        ? value
        : fallback
    }
  }
  return fallback
}

/**
 * Database update listener callback type
 */
export type DatabaseUpdateListener = (db: Database | null) => void

/**
 * Version mismatch information
 */
export interface VersionMismatchInfo {
  currentVersion: string
  databaseVersion: string
}

/**
 * Version mismatch listener callback type
 */
export type VersionMismatchListener = (info: VersionMismatchInfo) => void

/**
 * Database statistics interface
 */
export interface DatabaseStats {
  games: number
  channels: number
  lastModified: string | null
  lastCheckTime: Date | null
  isDevelopment: boolean
}

export class DatabaseManager {
  private db: Database | null = null
  private SQL: InitializedSQLModule | null = null
  private lastModified: string | null = null
  private lastETag: string | null = null
  private checkInterval: NodeJS.Timeout | null = null
  private readonly isDevelopment: boolean
  private readonly listeners = new Set<DatabaseUpdateListener>()
  private lastCheckTime: Date | null = null
  private currentAppVersion: string | null = null
  private databaseAppVersion: string | null = null
  private readonly versionMismatchListeners = new Set<VersionMismatchListener>()

  // In production, check every 10 minutes
  public readonly PRODUCTION_CHECK_INTERVAL = 10 * 60 * 1000 // 10 minutes

  constructor() {
    this.isDevelopment = import.meta.env.DEV
  }

  /**
   * Initialize the database manager
   */
  async init(): Promise<void> {
    // Initialize SQL.js
    const sqlJsModule = await import('sql.js')
    const initSqlJs = sqlJsModule.default
    this.SQL = (await initSqlJs({
      locateFile: (file: string) => `https://sql.js.org/dist/${file}`,
    })) as InitializedSQLModule

    // Load initial database (will cache currentAppVersion from database)
    await this.loadDatabase()

    // Set up automatic checking in production
    if (!this.isDevelopment) {
      this.startProductionChecking()
    }

    // In development, listen for Vite HMR events
    if (this.isDevelopment && import.meta.hot) {
      // Listen for database file changes via custom HMR event
      import.meta.hot.on('database-updated', () => {
        debug.log('🔄 Database updated, reloading...')
        void this.reloadDatabase() // Explicitly handle promise without awaiting
      })
    }
  }

  /**
   * Extract app version from database metadata
   */
  private extractDatabaseAppVersion(db: Database): string {
    try {
      const result = db.exec(
        "SELECT value FROM app_metadata WHERE key = 'app_version'",
      )
      const version = extractSingleValue(result, 'unknown')
      debug.log('🗄️ Database app version:', version)
      return String(version)
    } catch (error) {
      debug.warn('⚠️ Could not extract database version:', error)
    }

    return 'unknown'
  }

  /**
   * Load database from server
   */
  async loadDatabase(): Promise<boolean> {
    if (!this.SQL) {
      throw new Error('SQL.js not initialized')
    }

    try {
      this.lastCheckTime = new Date()

      // In production, check headers first to avoid unnecessary downloads
      if (!this.isDevelopment && this.lastModified) {
        const headResponse = await fetch('./data/games.db', {
          method: 'HEAD',
          cache: 'no-cache',
        })

        if (!headResponse.ok) {
          throw new Error(`Failed to check database: ${headResponse.status}`)
        }

        const lastModified = headResponse.headers.get('Last-Modified')
        const etag = headResponse.headers.get('ETag')

        // Check if database hasn't changed (use both headers for reliability)
        if (
          (lastModified && lastModified === this.lastModified) ||
          (etag && etag === this.lastETag)
        ) {
          // Database hasn't changed, no need to download
          return false
        }
      }

      // Download the actual database (development or when changed in production)
      const response = await fetch('./data/games.db', {
        cache: this.isDevelopment ? 'default' : 'no-cache',
      })

      if (!response.ok) {
        throw new Error(`Failed to load database: ${response.status}`)
      }

      // Store headers for next comparison
      const lastModified = response.headers.get('Last-Modified')
      const etag = response.headers.get('ETag')

      const dbBuffer = await response.arrayBuffer()

      // Close existing database if present
      if (this.db) {
        this.db.close()
      }

      // Create temporary database instance to check version
      if (!this.SQL || !isSQLModule(this.SQL)) {
        throw new Error('SQL.js module not initialized')
      }
      const tempDb = new this.SQL.Database(new Uint8Array(dbBuffer))

      // Extract version from the new database
      const newDatabaseVersion = this.extractDatabaseAppVersion(tempDb)

      // Handle initial load vs updates differently
      if (!this.currentAppVersion) {
        // Initial load: use database version as current version
        this.currentAppVersion = newDatabaseVersion
        debug.log(
          '📱 INITIAL LOAD: Set app version from database:',
          this.currentAppVersion,
        )
      } else {
        // Subsequent load: check compatibility
        debug.log('🔍 VERSION CHECK:', {
          cached: this.currentAppVersion,
          database: newDatabaseVersion,
          compatible: this.currentAppVersion === newDatabaseVersion,
        })

        const isCompatible = this.currentAppVersion === newDatabaseVersion

        if (!isCompatible) {
          // Don't update the database, keep the old one
          tempDb.close()
          debug.error('🚫 VERSION MISMATCH DETECTED:', {
            current: this.currentAppVersion,
            database: newDatabaseVersion,
          })

          // Stop checking since we'll never be compatible again
          this.stopProductionChecking()
          debug.warn('🛑 Stopped database checking due to version mismatch')

          // Notify about version mismatch
          debug.log('📢 Notifying version mismatch listeners...')
          this.notifyVersionMismatchListeners({
            currentVersion: this.currentAppVersion,
            databaseVersion: newDatabaseVersion,
          })

          return false
        }
      }

      // Close existing database if present
      if (this.db) {
        this.db.close()
      }

      this.db = tempDb
      this.databaseAppVersion = newDatabaseVersion
      this.lastModified = lastModified
      this.lastETag = etag

      // Database available through databaseManager.getDatabase() - no global access needed

      const totalGames = extractSingleValue(
        this.db.exec('SELECT COUNT(*) FROM games'),
        0,
      )
      debug.log('🗄️ Database loaded, total games:', totalGames)

      // Notify listeners that database has been updated
      this.notifyListeners()

      return true
    } catch (error) {
      debug.error('❌ Error loading database:', error)
      throw error
    }
  }

  /**
   * Force reload the database
   */
  async reloadDatabase(): Promise<boolean> {
    this.lastModified = null // Force reload by clearing headers
    this.lastETag = null
    return await this.loadDatabase()
  }

  /**
   * Start periodic checking in production
   */
  private startProductionChecking(): void {
    if (this.checkInterval) {
      clearInterval(this.checkInterval)
    }

    this.checkInterval = setInterval(() => {
      void (async () => {
        try {
          const wasUpdated = await this.loadDatabase()
          if (wasUpdated) {
            debug.info('🔄 Database automatically updated in production')
          }
          // Always notify listeners to update UI timestamps, even if no content changed
          this.notifyListeners()
        } catch (error) {
          debug.error('❌ Error checking for database updates:', error)
        }
      })()
    }, this.PRODUCTION_CHECK_INTERVAL)

    debug.log(
      `⏰ Started production database checking (every ${this.PRODUCTION_CHECK_INTERVAL / 60000}m)`,
    )
  }

  /**
   * Stop periodic checking
   */
  private stopProductionChecking(): void {
    if (this.checkInterval) {
      clearInterval(this.checkInterval)
      this.checkInterval = null
      debug.log('⏹️ Stopped production database checking')
    }
  }

  /**
   * Add listener for database updates
   */
  addUpdateListener(callback: DatabaseUpdateListener): void {
    this.listeners.add(callback)
  }

  /**
   * Remove listener for database updates
   */
  removeUpdateListener(callback: DatabaseUpdateListener): void {
    this.listeners.delete(callback)
  }

  /**
   * Add listener for version mismatches
   */
  addVersionMismatchListener(callback: VersionMismatchListener): void {
    this.versionMismatchListeners.add(callback)
  }

  /**
   * Remove listener for version mismatches
   */
  removeVersionMismatchListener(callback: VersionMismatchListener): void {
    this.versionMismatchListeners.delete(callback)
  }

  /**
   * Notify all listeners that database has been updated
   */
  private notifyListeners(): void {
    this.listeners.forEach((callback) => {
      try {
        callback(this.db)
      } catch (error) {
        debug.error('❌ Error in database update listener:', error)
      }
    })
  }

  /**
   * Notify all listeners about version mismatch
   */
  private notifyVersionMismatchListeners(info: VersionMismatchInfo): void {
    this.versionMismatchListeners.forEach((callback) => {
      try {
        callback(info)
      } catch (error) {
        debug.error('❌ Error in version mismatch listener:', error)
      }
    })
  }

  /**
   * Get current database instance
   */
  getDatabase(): Database | null {
    if (this.db && isDatabase(this.db)) {
      return this.db
    }
    return null
  }

  /**
   * Check if database is loaded and valid
   */
  isLoaded(): boolean {
    return this.db !== null && isDatabase(this.db)
  }

  /**
   * Get database statistics
   */
  getStats(): DatabaseStats | null {
    if (!this.db) {
      return null
    }

    try {
      const gameCount = extractSingleValue(
        this.db.exec('SELECT COUNT(*) FROM games WHERE is_absorbed = 0'),
        0,
      ) as number
      const channelResults = this.db.exec(
        "SELECT COUNT(DISTINCT unique_channels) FROM games WHERE unique_channels IS NOT NULL AND unique_channels != '[]'",
      )
      const channelCount = extractSingleValue(channelResults, 0) as number

      // Get data freshness from database metadata instead of HTTP requests
      let dataModified = this.lastModified // fallback to database file mtime
      try {
        const metadataResult = this.db.exec(
          "SELECT value FROM app_metadata WHERE key = 'data_last_modified'",
        )
        const extractedData = extractSingleValue(metadataResult, '')
        if (extractedData) {
          dataModified = String(extractedData)
        }
      } catch (error) {
        debug.log('Could not read data_last_modified from metadata:', error)
      }

      return {
        games: gameCount,
        channels: channelCount,
        lastModified: dataModified,
        lastCheckTime: this.lastCheckTime,
        isDevelopment: this.isDevelopment,
      }
    } catch (error) {
      debug.error('❌ Error getting database stats:', error)
      return null
    }
  }

  /**
   * Force a version mismatch test (development only)
   */
  async testVersionMismatch(): Promise<void> {
    if (!this.isDevelopment) {
      return
    }

    debug.log('🧪 TESTING VERSION MISMATCH')
    debug.log('Current cached version:', this.currentAppVersion)

    // Manually trigger a version mismatch by pretending database has different version
    const fakeVersion = 'test-mismatch-version'
    debug.log('Simulating database with version:', fakeVersion)

    if (this.currentAppVersion !== fakeVersion) {
      debug.log('📢 Triggering version mismatch notification...')
      this.notifyVersionMismatchListeners({
        currentVersion: this.currentAppVersion ?? 'unknown',
        databaseVersion: fakeVersion,
      })
    }
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    this.stopProductionChecking()

    if (this.db) {
      this.db.close()
      this.db = null
    }

    this.listeners.clear()
    this.versionMismatchListeners.clear()

    // Database cleanup handled by this.db.close() above
  }
}

// Create HMR-safe singleton instance
let _databaseManager!: DatabaseManager

if (import.meta.hot && (window as WindowWithGameDatabase).__databaseManager) {
  // Reuse existing instance during HMR
  _databaseManager = (window as WindowWithGameDatabase)
    .__databaseManager as DatabaseManager
} else {
  // Create new instance
  _databaseManager = new DatabaseManager()

  // Store globally for HMR persistence
  if (typeof window !== 'undefined') {
    ;(window as WindowWithGameDatabase).__databaseManager = _databaseManager
  }
}

// HMR support
if (import.meta.hot) {
  import.meta.hot.accept()

  // Preserve the instance across HMR updates
  import.meta.hot.dispose(() => {
    // Don't destroy the database manager on HMR
    // It will be reused by the new module
  })
}

export const databaseManager = _databaseManager
