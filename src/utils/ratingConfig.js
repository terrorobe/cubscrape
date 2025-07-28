/**
 * Rating system configuration and utilities
 * Centralizes all rating-related constants and color calculations
 */

// Rating thresholds
export const RATING_THRESHOLDS = {
  POSITIVE: 80, // >= 80% is considered positive
  MIXED: 50, // >= 50% and < 80% is mixed
  // < 50% is negative
}

// Hidden gem criteria
export const HIDDEN_GEM_CRITERIA = {
  MIN_RATING: 80, // Minimum positive review percentage
  MIN_VIDEO_COUNT: 1, // Minimum number of videos
  MAX_VIDEO_COUNT: 3, // Maximum number of videos
  MIN_REVIEW_COUNT: 50, // Minimum number of reviews
}

// Review summary to color mapping
export const REVIEW_SUMMARY_COLORS = {
  'overwhelmingly positive': { hsl: 'hsl(120, 70%, 40%)', textColor: 'black' },
  'very positive': { hsl: 'hsl(100, 60%, 50%)', textColor: 'black' },
  'mostly positive': { hsl: 'hsl(80, 60%, 50%)', textColor: 'black' },
  positive: { hsl: 'hsl(60, 60%, 50%)', textColor: 'black' },
  mixed: { hsl: 'hsl(45, 60%, 50%)', textColor: 'black' },
  'mostly negative': { hsl: 'hsl(20, 60%, 50%)', textColor: 'white' },
  'overwhelmingly negative': { hsl: 'hsl(0, 80%, 40%)', textColor: 'white' },
  'very negative': { hsl: 'hsl(10, 70%, 50%)', textColor: 'white' },
  negative: { hsl: 'hsl(15, 65%, 45%)', textColor: 'white' },
}

// Default colors for special cases
export const DEFAULT_COLORS = {
  NO_REVIEWS: { hsl: 'hsl(0, 0%, 50%)', textColor: 'white' }, // Gray
  POSITIVE_FALLBACK: { hsl: 'hsl(120, 70%, 40%)', textColor: 'black' },
  MIXED_FALLBACK: { hsl: 'hsl(45, 60%, 50%)', textColor: 'black' },
  NEGATIVE_FALLBACK: { hsl: 'hsl(0, 80%, 40%)', textColor: 'white' },
}

/**
 * Get rating color based on review summary or percentage
 * @param {number|null} percentage - Positive review percentage
 * @param {string|null} reviewSummary - Review summary text
 * @returns {{backgroundColor: string, textColor: string}} Color configuration
 */
export function getRatingColor(percentage, reviewSummary) {
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
 * @param {number|null} percentage - Positive review percentage
 * @param {string|null} reviewSummary - Review summary text
 * @returns {string} CSS class for text color
 */
export function getRatingTextClass(percentage, reviewSummary) {
  const { textColor } = getRatingColor(percentage, reviewSummary)
  return textColor === 'black' ? 'text-black' : 'text-white'
}

/**
 * Check if a game qualifies as a hidden gem
 * @param {Object} game - Game object with rating and video data
 * @returns {boolean} True if game is a hidden gem
 */
export function isHiddenGem(game) {
  return (
    game.positive_review_percentage >= HIDDEN_GEM_CRITERIA.MIN_RATING &&
    game.video_count >= HIDDEN_GEM_CRITERIA.MIN_VIDEO_COUNT &&
    game.video_count <= HIDDEN_GEM_CRITERIA.MAX_VIDEO_COUNT &&
    game.review_count >= HIDDEN_GEM_CRITERIA.MIN_REVIEW_COUNT
  )
}

/**
 * Get rating class for styling (background and text color)
 * @param {number|null} percentage - Positive review percentage
 * @param {string|null} reviewSummary - Review summary text
 * @returns {string} CSS class string
 */
export function getRatingClass(percentage, reviewSummary) {
  // Handle special cases first
  if (reviewSummary === 'No user reviews' || !percentage) {
    return 'bg-gray-500 text-white'
  }

  // Get text color class from rating
  return getRatingTextClass(percentage, reviewSummary)
}

/**
 * Get rating style object for inline styling
 * @param {number|null} percentage - Positive review percentage
 * @param {string|null} reviewSummary - Review summary text
 * @returns {Object} Style object with backgroundColor
 */
export function getRatingStyle(percentage, reviewSummary) {
  const { backgroundColor } = getRatingColor(percentage, reviewSummary)
  return { backgroundColor }
}
