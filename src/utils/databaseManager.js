/**
 * Database manager for both development and production environments
 *
 * Features:
 * - Automatic database reloading in development (via Vite HMR)
 * - Timer-based checking in production
 * - Manual refresh capability
 * - Database change detection via file modification time
 */

export class DatabaseManager {
  constructor() {
    this.db = null
    this.SQL = null
    this.lastModified = null
    this.lastETag = null
    this.checkInterval = null
    this.isDevelopment = import.meta.env.DEV
    this.listeners = new Set()
    this.lastCheckTime = null
    this.currentAppVersion = null
    this.databaseAppVersion = null
    this.versionMismatchListeners = new Set()

    // In production, check every 10 minutes
    this.PRODUCTION_CHECK_INTERVAL = 10 * 60 * 1000 // 10 minutes
  }

  /**
   * Initialize the database manager
   */
  async init() {
    // Initialize SQL.js
    const initSqlJs = (await import('sql.js')).default
    this.SQL = await initSqlJs({
      locateFile: (file) => `https://sql.js.org/dist/${file}`,
    })

    // Load initial database (will cache currentAppVersion from database)
    await this.loadDatabase()

    // Set up automatic checking in production
    if (!this.isDevelopment) {
      this.startProductionChecking()
    }

    // In development, listen for Vite HMR events
    if (this.isDevelopment && import.meta.hot) {
      // Listen for database file changes via custom HMR event
      import.meta.hot.on('database-updated', async () => {
        console.log('🔄 Database updated, reloading...')
        await this.reloadDatabase()
      })
    }
  }

  /**
   * Extract app version from database metadata
   */
  extractDatabaseAppVersion(db) {
    try {
      const result = db.exec(
        "SELECT value FROM app_metadata WHERE key = 'app_version'",
      )
      if (result.length > 0 && result[0].values.length > 0) {
        const version = result[0].values[0][0]
        console.log('🗄️ Database app version:', version)
        return version
      }
    } catch (error) {
      console.warn('⚠️ Could not extract database version:', error)
    }

    return 'unknown'
  }

  /**
   * Load database from server
   */
  async loadDatabase() {
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
      const tempDb = new this.SQL.Database(new Uint8Array(dbBuffer))

      // Extract version from the new database
      const newDatabaseVersion = this.extractDatabaseAppVersion(tempDb)

      // Handle initial load vs updates differently
      if (!this.currentAppVersion) {
        // Initial load: use database version as current version
        this.currentAppVersion = newDatabaseVersion
        console.log(
          '📱 INITIAL LOAD: Set app version from database:',
          this.currentAppVersion,
        )
      } else {
        // Subsequent load: check compatibility
        console.log('🔍 VERSION CHECK:', {
          cached: this.currentAppVersion,
          database: newDatabaseVersion,
          compatible: this.currentAppVersion === newDatabaseVersion,
        })

        const isCompatible = this.currentAppVersion === newDatabaseVersion

        if (!isCompatible) {
          // Don't update the database, keep the old one
          tempDb.close()
          console.error('🚫 VERSION MISMATCH DETECTED:', {
            current: this.currentAppVersion,
            database: newDatabaseVersion,
          })

          // Stop checking since we'll never be compatible again
          this.stopProductionChecking()
          console.warn('🛑 Stopped database checking due to version mismatch')

          // Notify about version mismatch
          console.log('📢 Notifying version mismatch listeners...')
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

      // Make database available globally for backward compatibility
      window.gameDatabase = this.db

      console.log(
        '🗄️ Database loaded, total games:',
        this.db.exec('SELECT COUNT(*) FROM games')[0].values[0][0],
      )

      // Notify listeners that database has been updated
      this.notifyListeners()

      return true
    } catch (error) {
      console.error('❌ Error loading database:', error)
      throw error
    }
  }

  /**
   * Force reload the database
   */
  async reloadDatabase() {
    this.lastModified = null // Force reload by clearing headers
    this.lastETag = null
    return await this.loadDatabase()
  }

  /**
   * Start periodic checking in production
   */
  startProductionChecking() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval)
    }

    this.checkInterval = setInterval(async () => {
      try {
        const wasUpdated = await this.loadDatabase()
        if (wasUpdated) {
          console.log('🔄 Database automatically updated in production')
        }
        // Always notify listeners to update UI timestamps, even if no content changed
        this.notifyListeners()
      } catch (error) {
        console.error('❌ Error checking for database updates:', error)
      }
    }, this.PRODUCTION_CHECK_INTERVAL)

    console.log(
      `⏰ Started production database checking (every ${this.PRODUCTION_CHECK_INTERVAL / 60000}m)`,
    )
  }

  /**
   * Stop periodic checking
   */
  stopProductionChecking() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval)
      this.checkInterval = null
      console.log('⏹️ Stopped production database checking')
    }
  }

  /**
   * Add listener for database updates
   */
  addUpdateListener(callback) {
    this.listeners.add(callback)
  }

  /**
   * Remove listener for database updates
   */
  removeUpdateListener(callback) {
    this.listeners.delete(callback)
  }

  /**
   * Add listener for version mismatches
   */
  addVersionMismatchListener(callback) {
    this.versionMismatchListeners.add(callback)
  }

  /**
   * Remove listener for version mismatches
   */
  removeVersionMismatchListener(callback) {
    this.versionMismatchListeners.delete(callback)
  }

  /**
   * Notify all listeners that database has been updated
   */
  notifyListeners() {
    this.listeners.forEach((callback) => {
      try {
        callback(this.db)
      } catch (error) {
        console.error('❌ Error in database update listener:', error)
      }
    })
  }

  /**
   * Notify all listeners about version mismatch
   */
  notifyVersionMismatchListeners() {
    this.versionMismatchListeners.forEach((callback) => {
      try {
        callback({
          currentVersion: this.currentAppVersion,
          databaseVersion: this.databaseAppVersion,
        })
      } catch (error) {
        console.error('❌ Error in version mismatch listener:', error)
      }
    })
  }

  /**
   * Get current database instance
   */
  getDatabase() {
    return this.db
  }

  /**
   * Check if database is loaded
   */
  isLoaded() {
    return this.db !== null
  }

  /**
   * Get database statistics
   */
  getStats() {
    if (!this.db) {
      return null
    }

    try {
      const gameCount = this.db.exec(
        'SELECT COUNT(*) FROM games WHERE is_absorbed = 0',
      )[0].values[0][0]
      const channelResults = this.db.exec(
        "SELECT COUNT(DISTINCT unique_channels) FROM games WHERE unique_channels IS NOT NULL AND unique_channels != '[]'",
      )
      const channelCount =
        channelResults.length > 0 ? channelResults[0].values[0][0] : 0

      return {
        games: gameCount,
        channels: channelCount,
        lastModified: this.lastModified,
        lastCheckTime: this.lastCheckTime,
        isDevelopment: this.isDevelopment,
      }
    } catch (error) {
      console.error('❌ Error getting database stats:', error)
      return null
    }
  }

  /**
   * Force a version mismatch test (development only)
   */
  async testVersionMismatch() {
    if (!this.isDevelopment) {
      return
    }

    console.log('🧪 TESTING VERSION MISMATCH')
    console.log('Current cached version:', this.currentAppVersion)

    // Manually trigger a version mismatch by pretending database has different version
    const fakeVersion = 'test-mismatch-version'
    console.log('Simulating database with version:', fakeVersion)

    if (this.currentAppVersion !== fakeVersion) {
      console.log('📢 Triggering version mismatch notification...')
      this.notifyVersionMismatchListeners({
        currentVersion: this.currentAppVersion,
        databaseVersion: fakeVersion,
      })
    }
  }

  /**
   * Cleanup resources
   */
  destroy() {
    this.stopProductionChecking()

    if (this.db) {
      this.db.close()
      this.db = null
    }

    this.listeners.clear()
    this.versionMismatchListeners.clear()

    if (window.gameDatabase === this.db) {
      delete window.gameDatabase
    }
  }
}

// Create HMR-safe singleton instance
let _databaseManager

if (import.meta.hot && window.__databaseManager) {
  // Reuse existing instance during HMR
  _databaseManager = window.__databaseManager
} else {
  // Create new instance
  _databaseManager = new DatabaseManager()

  // Store globally for HMR persistence
  if (typeof window !== 'undefined') {
    window.__databaseManager = _databaseManager
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
