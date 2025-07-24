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
    this.checkInterval = null
    this.isDevelopment = import.meta.env.DEV
    this.listeners = new Set()
    this.lastCheckTime = null

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

    // Load initial database
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
   * Load database from server
   */
  async loadDatabase() {
    try {
      this.lastCheckTime = new Date()

      const response = await fetch('./data/games.db', {
        // Add cache-busting in production to detect changes
        cache: this.isDevelopment ? 'default' : 'no-cache',
      })

      if (!response.ok) {
        throw new Error(`Failed to load database: ${response.status}`)
      }

      // Check if database has been modified
      const lastModified = response.headers.get('Last-Modified')
      if (this.lastModified && lastModified === this.lastModified) {
        // Database hasn't changed, no need to reload
        return false
      }

      const dbBuffer = await response.arrayBuffer()

      // Close existing database if present
      if (this.db) {
        this.db.close()
      }

      this.db = new this.SQL.Database(new Uint8Array(dbBuffer))
      this.lastModified = lastModified

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
    this.lastModified = null // Force reload by clearing last modified
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
      const gameCount = this.db.exec('SELECT COUNT(*) FROM games')[0]
        .values[0][0]
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
   * Cleanup resources
   */
  destroy() {
    this.stopProductionChecking()

    if (this.db) {
      this.db.close()
      this.db = null
    }

    this.listeners.clear()

    if (window.gameDatabase === this.db) {
      delete window.gameDatabase
    }
  }
}

// Create singleton instance
export const databaseManager = new DatabaseManager()
