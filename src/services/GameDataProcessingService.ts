/**
 * Game Data Processing Service
 * Handles transformation of raw database query results into processed game data
 * for display in the application
 */

import { debug } from '../utils/debug'
import type { DatabaseQueryResult } from './GameDatabaseService'
import type { ParsedGameData } from '../types/database'

/**
 * Extended game interface for App component usage with additional computed properties
 */
export interface ProcessedGameData extends ParsedGameData {
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

  // Add index signature for backward compatibility
  [key: string]: unknown
}

/**
 * Raw game data structure from database before processing
 */
interface RawGameData {
  [key: string]: string | number | null
}

/**
 * Parent game data lookup for absorbed games
 */
type ParentGameLookup = Map<string, RawGameData>

/**
 * Service for processing and transforming raw database query results
 */
export class GameDataProcessingService {
  /**
   * Process database query results into usable game data
   * @param results - Raw database query results
   * @returns Array of processed game data ready for display
   */
  processQueryResults(results: DatabaseQueryResult[]): ProcessedGameData[] {
    if (results.length === 0) {
      debug.log('✓ No games found matching filters')
      return []
    }

    const processedGames: ProcessedGameData[] = []

    // First pass: collect all games and build a lookup for parent data resolution
    const allGameData: RawGameData[] = []
    const parentGameLookup = this.buildParentGameLookup(results[0])

    // Extract all game data from query results
    results[0].values.forEach((row) => {
      const { columns } = results[0]
      const gameData = this.mapRowToGameData(
        row as (string | number | null)[],
        columns,
      )
      allGameData.push(gameData)
    })

    // Second pass: process games and resolve parent data for absorbed games
    allGameData.forEach((gameData) => {
      // Parse JSON columns
      this.parseJsonColumns(gameData)

      // For absorbed games, supplement with parent game data where needed
      if (gameData.is_absorbed && gameData.absorbed_into) {
        this.resolveAbsorbedGameData(gameData, parentGameLookup)
      }

      // Transform raw data to processed game object
      const game = this.transformToProcessedGame(gameData)
      processedGames.push(game)
    })

    debug.log(`✓ Processed ${processedGames.length} games`)
    return processedGames
  }

  /**
   * Extract unique channels from processed games
   * @param games - Array of processed game data
   * @returns Array of unique channel names sorted alphabetically
   */
  extractUniqueChannels(games: ProcessedGameData[]): string[] {
    const channelSet = new Set<string>()

    games.forEach((game) => {
      if (Array.isArray(game.unique_channels)) {
        game.unique_channels.forEach((channel: string) => {
          channelSet.add(channel)
        })
      }
    })

    return Array.from(channelSet).sort()
  }

  /**
   * Extract unique tags from processed games
   * @param games - Array of processed game data
   * @returns Array of unique tag names sorted alphabetically
   */
  extractUniqueTags(games: ProcessedGameData[]): string[] {
    const tagSet = new Set<string>()

    games.forEach((game) => {
      if (Array.isArray(game.tags)) {
        game.tags.forEach((tag: string) => {
          tagSet.add(tag)
        })
      }
    })

    return Array.from(tagSet).sort()
  }

  /**
   * Calculate aggregate statistics from processed games
   * @param games - Array of processed game data
   * @returns Object containing aggregate statistics
   */
  calculateAggregateStats(games: ProcessedGameData[]): {
    totalGames: number
    freeGames: number
    maxPrice: number
    avgRating: number
    totalChannels: number
    totalTags: number
  } {
    const stats = {
      totalGames: games.length,
      freeGames: games.filter((game) => game.is_free).length,
      maxPrice: 0,
      avgRating: 0,
      totalChannels: this.extractUniqueChannels(games).length,
      totalTags: this.extractUniqueTags(games).length,
    }

    if (games.length > 0) {
      // Calculate max price
      stats.maxPrice = Math.max(...games.map((game) => game.price_final ?? 0))

      // Calculate average rating (only for games with reviews)
      const gamesWithRatings = games.filter(
        (game) =>
          game.positive_review_percentage !== undefined &&
          game.positive_review_percentage > 0,
      )

      if (gamesWithRatings.length > 0) {
        const totalRating = gamesWithRatings.reduce(
          (sum, game) => sum + (game.positive_review_percentage ?? 0),
          0,
        )
        stats.avgRating = Math.round(totalRating / gamesWithRatings.length)
      }
    }

    return stats
  }

  /**
   * Build parent game lookup for absorbed games resolution
   * @param queryResult - Raw database query result
   * @returns Map of game keys to game data for parent lookup
   */
  private buildParentGameLookup(
    queryResult: DatabaseQueryResult,
  ): ParentGameLookup {
    const parentGameLookup = new Map<string, RawGameData>()

    queryResult.values.forEach((row) => {
      const gameData = this.mapRowToGameData(
        row as (string | number | null)[],
        queryResult.columns,
      )

      // Build parent lookup for absorbed games
      if (!gameData.is_absorbed) {
        parentGameLookup.set(
          gameData.game_key ? String(gameData.game_key) : '',
          gameData,
        )
      }
    })

    return parentGameLookup
  }

  /**
   * Map database row to game data object
   * @param row - Database row values
   * @param columns - Database column names
   * @returns Raw game data object
   */
  private mapRowToGameData(
    row: (string | number | null)[],
    columns: string[],
  ): RawGameData {
    const gameData: RawGameData = {}

    columns.forEach((col, index) => {
      gameData[col] = row[index]
    })

    return gameData
  }

  /**
   * Parse JSON columns in game data
   * @param gameData - Raw game data object to modify
   */
  private parseJsonColumns(gameData: RawGameData): void {
    // Parse JSON columns
    try {
      gameData.genres = JSON.parse(String(gameData.genres ?? '[]'))
      gameData.tags = JSON.parse(String(gameData.tags ?? '[]'))
      gameData.developers = JSON.parse(String(gameData.developers ?? '[]'))
      gameData.publishers = JSON.parse(String(gameData.publishers ?? '[]'))
      gameData.unique_channels = JSON.parse(
        String(gameData.unique_channels ?? '[]'),
      )
    } catch {
      debug.warn('Failed to parse JSON columns for game:', gameData.name)
    }

    // Parse JSON fields that may contain display links
    try {
      gameData.display_links = gameData.display_links
        ? JSON.parse(String(gameData.display_links))
        : null
    } catch {
      gameData.display_links = null
    }
  }

  /**
   * Resolve parent data for absorbed games
   * @param gameData - Raw game data for absorbed game
   * @param parentGameLookup - Lookup map for parent game data
   */
  private resolveAbsorbedGameData(
    gameData: RawGameData,
    parentGameLookup: ParentGameLookup,
  ): void {
    const parentData = parentGameLookup.get(
      gameData.absorbed_into ? String(gameData.absorbed_into) : '',
    )

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
        gameData.review_summary_priority = parentData.review_summary_priority
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

  /**
   * Transform raw game data to processed game object
   * @param gameData - Raw game data from database
   * @returns Processed game data with proper types
   */
  private transformToProcessedGame(gameData: RawGameData): ProcessedGameData {
    return {
      id: Number(gameData.id),
      game_key: String(gameData.game_key ?? ''),
      name: String(gameData.name),
      steam_app_id: gameData.steam_app_id
        ? String(gameData.steam_app_id)
        : undefined,
      header_image: gameData.header_image
        ? String(gameData.header_image)
        : undefined,
      price_eur: Number(gameData.price_eur),
      price_usd: Number(gameData.price_usd),
      price_final: Number(gameData.price_final),
      is_free: Boolean(gameData.is_free),
      release_date: gameData.release_date
        ? String(gameData.release_date)
        : undefined,
      release_date_sortable: Number(gameData.release_date_sortable),
      review_summary: gameData.review_summary
        ? String(gameData.review_summary)
        : undefined,
      review_summary_priority: Number(gameData.review_summary_priority),
      positive_review_percentage: Number(gameData.positive_review_percentage),
      review_count: Number(gameData.review_count),
      steam_url: gameData.steam_url ? String(gameData.steam_url) : undefined,
      itch_url: gameData.itch_url ? String(gameData.itch_url) : undefined,
      crazygames_url: gameData.crazygames_url
        ? String(gameData.crazygames_url)
        : undefined,
      demo_steam_app_id: gameData.demo_steam_app_id
        ? String(gameData.demo_steam_app_id)
        : undefined,
      demo_steam_url: gameData.demo_steam_url
        ? String(gameData.demo_steam_url)
        : undefined,
      display_links:
        typeof gameData.display_links === 'object' &&
        gameData.display_links !== null
          ? (gameData.display_links as { main?: string; demo?: string })
          : undefined,
      display_price: gameData.display_price
        ? String(gameData.display_price)
        : undefined,
      tags: Array.isArray(gameData.tags) ? gameData.tags : [],
      genres: Array.isArray(gameData.genres) ? gameData.genres : [],
      developers: Array.isArray(gameData.developers) ? gameData.developers : [],
      publishers: Array.isArray(gameData.publishers) ? gameData.publishers : [],
      platform: String(gameData.platform) as 'steam' | 'itch' | 'crazygames',
      last_updated: gameData.last_updated
        ? String(gameData.last_updated)
        : undefined,
      latest_video_title: gameData.latest_video_title
        ? String(gameData.latest_video_title)
        : undefined,
      latest_video_id: gameData.latest_video_id
        ? String(gameData.latest_video_id)
        : undefined,
      latest_video_date: gameData.latest_video_date
        ? String(gameData.latest_video_date)
        : undefined,
      newest_video_date: gameData.latest_video_date
        ? String(gameData.latest_video_date)
        : undefined,
      unique_channels: Array.isArray(gameData.unique_channels)
        ? gameData.unique_channels
        : [],
      video_count: Number(gameData.video_count) || 0,
      coming_soon: Boolean(gameData.coming_soon),
      is_early_access: Boolean(gameData.is_early_access),
      is_demo: Boolean(gameData.is_demo),
      planned_release_date: gameData.planned_release_date
        ? String(gameData.planned_release_date)
        : undefined,
      insufficient_reviews: Boolean(gameData.insufficient_reviews),
      is_inferred_summary: Boolean(gameData.is_inferred_summary),
      review_tooltip: gameData.review_tooltip
        ? String(gameData.review_tooltip)
        : undefined,
      recent_review_percentage: Number(gameData.recent_review_percentage),
      recent_review_count: Number(gameData.recent_review_count),
      recent_review_summary: gameData.recent_review_summary
        ? String(gameData.recent_review_summary)
        : undefined,
      is_absorbed: Boolean(gameData.is_absorbed),
      absorbed_into: gameData.absorbed_into
        ? String(gameData.absorbed_into)
        : undefined,
      discount_percent: Number(gameData.discount_percent) || 0,
      original_price_eur: Number(gameData.original_price_eur) || undefined,
      original_price_usd: Number(gameData.original_price_usd) || undefined,
      is_on_sale: Boolean(gameData.is_on_sale),
    }
  }
}

// Export singleton instance
export const gameDataProcessingService = new GameDataProcessingService()
