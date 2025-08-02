/**
 * Game Database Service
 * Handles database operations, statistics, and data loading for the game discovery platform
 */

import type { Database } from 'sql.js'
import { databaseManager } from '../utils/databaseManager'
import { debug } from '../utils/debug'
import { PRICING } from '../config/index'
import type { ChannelWithCount, TagWithCount } from '../types/database'

/**
 * Game statistics from database
 */
export interface GameStats {
  totalGames: number
  freeGames: number
  maxPrice: number
}

/**
 * Database query result for processing
 */
export interface DatabaseQueryResult {
  columns: string[]
  values: unknown[][]
}

/**
 * Service for managing game database operations
 */
export class GameDatabaseService {
  private db: Database | null = null

  /**
   * Initialize database connection
   */
  async loadDatabase(): Promise<void> {
    await databaseManager.init()
    this.db = databaseManager.getDatabase()
  }

  /**
   * Get current database instance
   */
  getDatabase(): Database | null {
    return this.db
  }

  /**
   * Load game statistics for price filtering and UI display
   */
  loadGameStats(database: Database): GameStats {
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
      return {
        totalGames: (stats[0] as number) || 0,
        freeGames: (stats[1] as number) || 0,
        maxPrice: Math.ceil((stats[2] as number) || PRICING.DEFAULT_MAX_PRICE),
      }
    }

    return {
      totalGames: 0,
      freeGames: 0,
      maxPrice: PRICING.DEFAULT_MAX_PRICE,
    }
  }

  /**
   * Load channels and tags with counts from database
   */
  loadChannelsAndTags(database: Database): {
    channels: string[]
    channelsWithCounts: ChannelWithCount[]
    allTags: TagWithCount[]
  } {
    // Get all unique channels with counts
    const channelResults = database.exec(
      "SELECT unique_channels FROM games WHERE unique_channels IS NOT NULL AND unique_channels != '[]' AND is_absorbed = 0",
    )
    const channelCounts = new Map()
    if (channelResults.length > 0) {
      channelResults[0].values.forEach((row) => {
        try {
          const channelArray = JSON.parse((row[0] as string) ?? '[]')
          channelArray.forEach((channel: string) => {
            channelCounts.set(channel, (channelCounts.get(channel) ?? 0) + 1)
          })
        } catch {
          debug.warn('Failed to parse channels:', row[0])
        }
      })
    }

    // Get video counts per channel
    const videoCounts = new Map<string, number>()
    const videoResults = database.exec(
      'SELECT channel_name, COUNT(*) as video_count FROM game_videos GROUP BY channel_name',
    )
    if (videoResults.length > 0) {
      videoResults[0].values.forEach((row) => {
        const channelName = row[0] as string
        const videoCount = row[1] as number
        videoCounts.set(channelName, videoCount)
      })
    }

    // Convert to sorted arrays
    const channels = Array.from(channelCounts.keys()).sort()
    const channelsWithCounts = Array.from(channelCounts.entries())
      .map(([name, count]) => ({
        name,
        count,
        videoCount: videoCounts.get(name) ?? 0,
      }))
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
          const tags = JSON.parse((row[0] as string) ?? '[]')
          tags.forEach((tag: string) => {
            tagCounts.set(tag, (tagCounts.get(tag) ?? 0) + 1)
          })
        } catch {
          debug.warn('Failed to parse tags:', row[0])
        }
      })
    }

    // Convert to sorted array of tag objects with counts
    const allTags = Array.from(tagCounts.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => {
        // Sort by count (descending) then by name (ascending)
        if (a.count !== b.count) {
          return b.count - a.count
        }
        return a.name.localeCompare(b.name)
      })

    return {
      channels,
      channelsWithCounts,
      allTags,
    }
  }

  /**
   * Execute a database query with parameters
   */
  executeQuery(
    database: Database,
    query: string,
    params: (string | number)[],
  ): DatabaseQueryResult[] {
    debug.log('Executing query:', query)
    debug.log('With params:', params)

    // Check for undefined params
    params.forEach((param, index) => {
      if (param === undefined) {
        debug.error(`Parameter ${index} is undefined!`)
      }
    })

    return database.exec(query, params)
  }
}

// Export singleton instance
export const gameDatabaseService = new GameDatabaseService()
