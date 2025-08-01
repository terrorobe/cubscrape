/**
 * Rating system configuration and utilities
 * Centralizes all rating-related constants and color calculations
 */

/**
 * Color configuration for ratings
 */
export interface RatingColor {
  hsl: string
  textColor: 'black' | 'white'
}

/**
 * Game object interface for rating calculations
 */
export interface GameForRating {
  positive_review_percentage?: number | null
  video_count?: number
  review_count?: number | null
}

/**
 * Rating color result interface
 */
export interface RatingColorResult {
  backgroundColor: string
  textColor: string
}

// Rating thresholds
export const RATING_THRESHOLDS = {
  POSITIVE: 80, // >= 80% is considered positive
  MIXED: 50, // >= 50% and < 80% is mixed
  // < 50% is negative
} as const

// Hidden gem criteria
export const HIDDEN_GEM_CRITERIA = {
  MIN_RATING: 80, // Minimum positive review percentage
  MIN_VIDEO_COUNT: 1, // Minimum number of videos
  MAX_VIDEO_COUNT: 3, // Maximum number of videos
  MIN_REVIEW_COUNT: 50, // Minimum number of reviews
} as const

// Review summary to color mapping
export const REVIEW_SUMMARY_COLORS: Record<string, RatingColor> = {
  'overwhelmingly positive': { hsl: 'hsl(120, 70%, 40%)', textColor: 'black' },
  'very positive': { hsl: 'hsl(100, 60%, 50%)', textColor: 'black' },
  'mostly positive': { hsl: 'hsl(80, 60%, 50%)', textColor: 'black' },
  positive: { hsl: 'hsl(90, 60%, 50%)', textColor: 'black' },
  mixed: { hsl: 'hsl(45, 60%, 50%)', textColor: 'black' },
  'mostly negative': { hsl: 'hsl(20, 60%, 50%)', textColor: 'white' },
  'overwhelmingly negative': { hsl: 'hsl(0, 80%, 40%)', textColor: 'white' },
  'very negative': { hsl: 'hsl(10, 70%, 50%)', textColor: 'white' },
  negative: { hsl: 'hsl(15, 65%, 45%)', textColor: 'white' },
}

// Default colors for special cases
export const DEFAULT_COLORS = {
  NO_REVIEWS: { hsl: 'hsl(0, 0%, 50%)', textColor: 'white' as const }, // Gray
  POSITIVE_FALLBACK: { hsl: 'hsl(120, 70%, 40%)', textColor: 'black' as const },
  MIXED_FALLBACK: { hsl: 'hsl(45, 60%, 50%)', textColor: 'black' as const },
  NEGATIVE_FALLBACK: { hsl: 'hsl(0, 80%, 40%)', textColor: 'white' as const },
} as const

/**
 * Get rating color based on review summary or percentage
 */
export function getRatingColor(
  percentage?: number | null,
  reviewSummary?: string | null,
): RatingColorResult {
  // Handle no reviews case
  if (!percentage) {
    return {
      backgroundColor: DEFAULT_COLORS.NO_REVIEWS.hsl,
      textColor: DEFAULT_COLORS.NO_REVIEWS.textColor,
    }
  }

  // Use review summary for more specific classification when available
  if (reviewSummary) {
    const summary = reviewSummary.toLowerCase()

    // Check each review summary type
    for (const [key, config] of Object.entries(REVIEW_SUMMARY_COLORS)) {
      if (summary.includes(key)) {
        return {
          backgroundColor: config.hsl,
          textColor: config.textColor,
        }
      }
    }
  }

  // Fallback to percentage-based classification
  if (percentage >= RATING_THRESHOLDS.POSITIVE) {
    return {
      backgroundColor: DEFAULT_COLORS.POSITIVE_FALLBACK.hsl,
      textColor: DEFAULT_COLORS.POSITIVE_FALLBACK.textColor,
    }
  }

  if (percentage >= RATING_THRESHOLDS.MIXED) {
    return {
      backgroundColor: DEFAULT_COLORS.MIXED_FALLBACK.hsl,
      textColor: DEFAULT_COLORS.MIXED_FALLBACK.textColor,
    }
  }

  return {
    backgroundColor: DEFAULT_COLORS.NEGATIVE_FALLBACK.hsl,
    textColor: DEFAULT_COLORS.NEGATIVE_FALLBACK.textColor,
  }
}

/**
 * Get text color class based on rating
 */
export function getRatingTextClass(
  percentage?: number | null,
  reviewSummary?: string | null,
): string {
  const { textColor } = getRatingColor(percentage, reviewSummary)
  return textColor === 'black' ? 'text-black' : 'text-white'
}

/**
 * Check if a game qualifies as a hidden gem
 */
export function isHiddenGem(game: GameForRating): boolean {
  return !!(
    game.positive_review_percentage &&
    game.positive_review_percentage >= HIDDEN_GEM_CRITERIA.MIN_RATING &&
    game.video_count &&
    game.video_count >= HIDDEN_GEM_CRITERIA.MIN_VIDEO_COUNT &&
    game.video_count <= HIDDEN_GEM_CRITERIA.MAX_VIDEO_COUNT &&
    game.review_count &&
    game.review_count >= HIDDEN_GEM_CRITERIA.MIN_REVIEW_COUNT
  )
}

/**
 * Get rating class for styling (background and text color)
 */
export function getRatingClass(
  percentage?: number | null,
  reviewSummary?: string | null,
): string {
  // Handle special cases first
  if (reviewSummary === 'No user reviews' || !percentage) {
    return 'bg-gray-500 text-white'
  }

  // Get text color class from rating
  return getRatingTextClass(percentage, reviewSummary)
}

/**
 * Get rating style object for inline styling
 */
export function getRatingStyle(
  percentage?: number | null,
  reviewSummary?: string | null,
): { backgroundColor: string } {
  const { backgroundColor } = getRatingColor(percentage, reviewSummary)
  return { backgroundColor }
}
