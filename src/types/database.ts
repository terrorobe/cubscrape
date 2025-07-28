/**
 * Database schema types for SQLite query results
 * Based on data/schema.sql
 */

/**
 * Platform type identifier
 */
export type PlatformId = 'steam' | 'itch' | 'crazygames'

/**
 * Game record from the games table
 */
export interface GameRecord {
  id: number
  game_key: string
  steam_app_id?: string
  name: string
  platform: PlatformId
  coming_soon: boolean
  is_early_access: boolean
  is_demo: boolean
  is_free: boolean
  price_eur?: number
  price_usd?: number
  price_final?: number
  positive_review_percentage?: number
  review_count?: number
  review_summary?: string
  review_summary_priority?: number
  recent_review_percentage?: number
  recent_review_count?: number
  recent_review_summary?: string
  insufficient_reviews: boolean
  release_date?: string
  planned_release_date?: string
  release_date_sortable?: number
  header_image?: string
  steam_url?: string
  itch_url?: string
  crazygames_url?: string
  last_updated?: string
  video_count: number
  latest_video_date?: string
  unique_channels?: string // JSON array
  genres?: string // JSON array
  tags?: string // JSON array
  developers?: string // JSON array
  publishers?: string // JSON array
  demo_steam_app_id?: string
  demo_steam_url?: string
  review_tooltip?: string
  is_inferred_summary: boolean
  is_absorbed: boolean
  absorbed_into?: string
}

/**
 * Video record from the game_videos table
 */
export interface VideoRecord {
  id: number
  game_id: number
  video_id: string
  video_title: string
  video_date: string
  channel_name: string
  published_at: string
}

/**
 * App metadata record
 */
export interface AppMetadataRecord {
  key: string
  value: string
}

/**
 * SQL.js query execution result
 */
export interface QueryExecResult {
  columns: string[]
  values: (string | number | null)[][]
}

/**
 * Parsed game data with additional computed properties
 */
export interface ParsedGameData
  extends Omit<
    GameRecord,
    'unique_channels' | 'genres' | 'tags' | 'developers' | 'publishers'
  > {
  unique_channels: string[]
  genres: string[]
  tags: string[]
  developers: string[]
  publishers: string[]
  // Video-related properties
  latest_video_title?: string
  latest_video_id?: string
  // Computed properties from display links
  display_links?: {
    main?: string
    demo?: string
  }
  display_price?: string
}

/**
 * Re-export advanced platform types for backward compatibility
 */
export type {
  PlatformGameData,
  SteamGameData,
  ItchGameData,
  CrazyGamesData,
} from './platform-discriminated.js'

/**
 * Database query parameters
 */
export interface QueryParams {
  [key: string]: string | number | boolean | null
}

/**
 * Database stats interface
 */
export interface DatabaseStats {
  totalGames: number
  freeGames: number
  maxPrice: number
}

/**
 * Channel data with counts
 */
export interface ChannelWithCount {
  name: string
  count: number
}

/**
 * Tag data with counts and popularity
 */
export interface TagWithCount {
  name: string
  count: number
  isPopular?: boolean
}

/**
 * Type guard to check if a value is a GameRecord
 */
export function isGameRecord(value: unknown): value is GameRecord {
  if (typeof value !== 'object' || value === null) {
    return false
  }

  const obj = value as Record<string, unknown>
  return (
    typeof obj.id === 'number' &&
    typeof obj.game_key === 'string' &&
    typeof obj.name === 'string' &&
    typeof obj.platform === 'string' &&
    ['steam', 'itch', 'crazygames'].includes(obj.platform)
  )
}

/**
 * Type guard to check if a value is a VideoRecord
 */
export function isVideoRecord(value: unknown): value is VideoRecord {
  if (typeof value !== 'object' || value === null) {
    return false
  }

  const obj = value as Record<string, unknown>
  return (
    typeof obj.id === 'number' &&
    typeof obj.game_id === 'number' &&
    typeof obj.video_id === 'string' &&
    typeof obj.video_title === 'string' &&
    typeof obj.channel_name === 'string'
  )
}

/**
 * Convert SQLite query result to typed records
 */
export function parseGameRecords(result: QueryExecResult): GameRecord[] {
  if (!result.values || result.values.length === 0) {
    return []
  }

  return result.values.map((row) => {
    const record: Record<string, unknown> = {}
    result.columns.forEach((column, index) => {
      record[column] = row[index]
    })
    return record as unknown as GameRecord
  })
}

/**
 * Convert SQLite query result to typed video records
 */
export function parseVideoRecords(result: QueryExecResult): VideoRecord[] {
  if (!result.values || result.values.length === 0) {
    return []
  }

  return result.values.map((row) => {
    const record: Record<string, unknown> = {}
    result.columns.forEach((column, index) => {
      record[column] = row[index]
    })
    return record as unknown as VideoRecord
  })
}

/**
 * Parse JSON fields in game record
 */
export function parseGameData(game: GameRecord): ParsedGameData {
  return {
    ...game,
    unique_channels: game.unique_channels
      ? JSON.parse(game.unique_channels)
      : [],
    genres: game.genres ? JSON.parse(game.genres) : [],
    tags: game.tags ? JSON.parse(game.tags) : [],
    developers: game.developers ? JSON.parse(game.developers) : [],
    publishers: game.publishers ? JSON.parse(game.publishers) : [],
  }
}

// Export types for external use
export type DatabaseRecord = GameRecord | VideoRecord | AppMetadataRecord
