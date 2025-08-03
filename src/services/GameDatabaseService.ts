/**
 * Game Database Service
 * Handles database operations, statistics, and data loading for the game discovery platform
 */

import type { Database } from 'sql.js'
import { databaseManager } from '../utils/databaseManager'
import { debug } from '../utils/debug'
import { PRICING } from '../config/index'
import type {
  ChannelWithCount,
  TagWithCount,
  VideoData,
} from '../types/database'

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
    const statsResults = this.executeQuery(
      database,
      `
      SELECT
        COUNT(*) as total_games,
        COUNT(CASE WHEN is_free = 1 OR price_final = 0 THEN 1 END) as free_games,
        MAX(CASE WHEN price_final > 0 THEN price_final ELSE 0 END) as max_price
      FROM games
      WHERE is_absorbed = 0
    `,
      [],
    )

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
    const channelResults = this.executeQuery(
      database,
      "SELECT unique_channels FROM games WHERE unique_channels IS NOT NULL AND unique_channels != '[]' AND is_absorbed = 0",
      [],
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
    const videoResults = this.executeQuery(
      database,
      'SELECT channel_name, COUNT(*) as video_count FROM game_videos GROUP BY channel_name',
      [],
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
    const tagResults = this.executeQuery(
      database,
      "SELECT tags FROM games WHERE tags IS NOT NULL AND tags != '[]' AND is_absorbed = 0",
      [],
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
   * Load video data for a specific game
   */
  loadGameVideos(database: Database, gameId: string): VideoData[] {
    const query = `
      SELECT video_title, video_id, video_date, channel_name
      FROM game_videos
      WHERE game_id = ?
      ORDER BY video_date DESC
    `
    const results = this.executeQuery(database, query, [gameId])

    if (results.length > 0) {
      return results[0].values.map(
        (row): VideoData => ({
          video_title: row[0] as string,
          video_id: row[1] as string,
          video_date: row[2] as string,
          channel_name: row[3] as string,
        }),
      )
    }

    return []
  }

  /**
   * Execute a database query with parameters
   */
  executeQuery(
    database: Database,
    query: string,
    params: (string | number)[],
  ): DatabaseQueryResult[] {
    // Enhanced debug logging for all queries
    const cleanQuery = query.replace(/\s+/g, ' ').trim()
    debug.log(`🔍 SQL Query: ${cleanQuery}`)
    if (params.length > 0) {
      debug.log(`📋 Parameters: ${JSON.stringify(params)}`)
    }

    // Check for undefined params
    params.forEach((param, index) => {
      if (param === undefined) {
        debug.error(`Parameter ${index} is undefined!`)
      }
    })

    const startTime = performance.now()
    const result = database.exec(query, params)
    const duration = performance.now() - startTime

    debug.log(
      `⏱️ Query executed in ${duration.toFixed(2)}ms, returned ${result.length} result sets`,
    )

    return result
  }
}

// Export singleton instance
export const gameDatabaseService = new GameDatabaseService()
