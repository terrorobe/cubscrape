/**
 * Application-wide constants and magic numbers
 * @module config/constants
 */

/**
 * Timing constants (in milliseconds)
 */
export const TIMING = {
  /** Duration to highlight a game card after navigation */
  GAME_HIGHLIGHT_DURATION: 6000,

  /** Interval for updating relative timestamps */
  TIMESTAMP_UPDATE_INTERVAL: 60000,

  /** Database check interval in production */
  DATABASE_CHECK_INTERVAL: 10 * 60 * 1000, // 10 minutes

  /** Default debounce delay for filter updates */
  FILTER_DEBOUNCE_DELAY: 400,

  /** Quick debounce for responsive operations */
  QUICK_DEBOUNCE_DELAY: 100,

  /** Simulated loading delay for progressive options */
  PROGRESSIVE_LOAD_DELAY: 50,

  /** Debug info update delay */
  DEBUG_UPDATE_DELAY: 100,

  /** Scroll retry delay */
  SCROLL_RETRY_DELAY: 100,

  /** Resize debounce delay */
  RESIZE_DEBOUNCE_DELAY: 100,

  /** Initial debug delay */
  INITIAL_DEBUG_DELAY: 500,

  /** Milliseconds in a minute */
  MINUTE_IN_MS: 60000,

  /** Milliseconds in an hour */
  HOUR_IN_MS: 3600000,
} as const

/**
 * Price-related constants
 */
export const PRICING = {
  /** Default minimum price */
  MIN_PRICE: 0,

  /** Default maximum price for filters */
  DEFAULT_MAX_PRICE: 70,

  /** Maximum possible price (can be overridden by actual data) */
  MAX_POSSIBLE_PRICE: 70,

  /** Price thresholds for smart sorting value calculations */
  VALUE_THRESHOLDS: {
    BUDGET: 20,
    MODERATE: 30,
  },
} as const

/**
 * Rating threshold configuration
 */
interface RatingFilterOption {
  value: number
  label: string
}

/**
 * Rating thresholds and percentages
 */
export const RATINGS = {
  /** Threshold for "positive" rating classification */
  POSITIVE_THRESHOLD: 80,

  /** Threshold for "mixed" rating classification */
  MIXED_THRESHOLD: 50,

  /** Available rating filter options */
  FILTER_OPTIONS: [
    { value: 0, label: 'All Ratings' },
    { value: 70, label: '70%+ Positive' },
    { value: 80, label: '80%+ Positive' },
    { value: 90, label: '90%+ Positive' },
  ] as readonly RatingFilterOption[],

  /** Smart sorting rating thresholds */
  SMART_SORT: {
    EXCELLENT: 85,
    VERY_POSITIVE: 80,
    POSITIVE: 75,
    MOSTLY_POSITIVE: 70,
    MIXED: 60,
  },
} as const

/**
 * Progressive loading configuration
 */
export const PROGRESSIVE_LOADING = {
  /** Initial number of items to load */
  INITIAL_LOAD_COUNT: 20,

  /** Number of items to load on each "load more" action */
  LOAD_MORE_COUNT: 10,
} as const

/**
 * UI component display limits
 */
export const UI_LIMITS = {
  /** Initial number of channels to show in filter dropdown */
  CHANNEL_FILTER_INITIAL_SHOW_COUNT: 5,

  /** Initial number of tags to show in filter dropdown */
  TAG_FILTER_INITIAL_SHOW_COUNT: 8,

  /** Number of popular channels to show for quick selection */
  POPULAR_CHANNELS_COUNT: 4,

  /** Number of mobile channels to show */
  MOBILE_CHANNELS_COUNT: 5,

  /** Number of tags to show in game card */
  GAME_CARD_TAG_LIMIT: 5,

  /** Number of tags to show in preset previews */
  PRESET_TAG_PREVIEW_COUNT: 2,

  /** Number of popular tags for top selection */
  POPULAR_TAGS_COUNT: 10,
} as const

/**
 * Layout and responsive design constants
 */
export const LAYOUT = {
  /** Maximum container width */
  CONTAINER_MAX_WIDTH: '1600px',

  /** Maximum container width as number (for responsive calculations) */
  CONTAINER_MAX_WIDTH_PX: 1600,

  /** Minimum card width for grid layout */
  CARD_MIN_WIDTH: '296px',

  /** Minimum card width as number */
  CARD_MIN_WIDTH_PX: 296,

  /** Sidebar width when expanded */
  SIDEBAR_WIDTH_EXPANDED: 'w-72',

  /** Sidebar width when collapsed */
  SIDEBAR_WIDTH_COLLAPSED: 'w-12',

  /** Sticky top offset for sidebar toggle */
  SIDEBAR_TOGGLE_TOP: 'top-6',

  /** Sticky top offset for sidebar content */
  SIDEBAR_CONTENT_TOP: 'top-20',

  /** Maximum height calculation for sidebar scroll area */
  SIDEBAR_MAX_HEIGHT: 'calc(100vh-6rem)',

  /** Responsive breakpoints (Tailwind CSS defaults) */
  BREAKPOINTS: {
    SM: '640px',
    MD: '768px',
    LG: '1024px',
    XL: '1280px',
    '2XL': '1536px',
  },
} as const

/**
 * Internationalization strings (preparation for i18n)
 */
export const I18N_STRINGS = {
  /** App title and branding */
  APP_TITLE: 'Curated Steam Games',
  APP_SUBTITLE: 'Discovered from YouTube Gaming Channels',

  /** Common UI labels */
  GAMES_FOUND: 'games found',
  TOTAL_GAMES: 'total',
  LOADING_GAMES: 'Loading games...',
  ERROR_LOADING: 'Error loading games:',
  NO_GAMES_FOUND: 'No games found matching your criteria.',

  /** Database status */
  DATABASE_LABEL: 'Database:',
  LAST_CHECK_LABEL: 'Last check:',
  NEW_VERSION_TITLE: 'New Version Available',
  NEW_VERSION_MESSAGE:
    'The app has been updated. Please reload to get the latest features and fixes.',
  RELOAD_NOW: 'Reload Now',
  DISMISS: 'Dismiss',

  /** Filter labels */
  SORTED_BY: 'Sorted by:',
  FILTERS: 'Filters',
  EXPAND_FILTERS: 'Expand filters',
  COLLAPSE_FILTERS: 'Collapse filters',
} as const

/**
 * Animation durations
 */
export const ANIMATIONS = {
  /** Fast transitions (button clicks, hovers) */
  FAST: '0.1s',

  /** Normal transitions (most UI elements) */
  NORMAL: '0.2s',

  /** Slow transitions (layout changes, sidebar) */
  SLOW: '0.3s',

  /** Sidebar transition duration */
  SIDEBAR_TRANSITION: '300ms',
} as const

/**
 * Sort specification with SQL ordering logic
 */
interface SortSpec {
  sql: string
}

/**
 * Sort specifications with their SQL ordering logic
 */
export const SORT_SPECS: Record<string, SortSpec> = {
  relevance: {
    sql: `
      ORDER BY
        search_score DESC,
        CASE
          WHEN positive_review_percentage >= 80 AND (is_free = 1 OR COALESCE(price_eur, price_usd, 0) <= 2000) THEN 1
          WHEN positive_review_percentage >= 70 AND (is_free = 1 OR COALESCE(price_eur, price_usd, 0) <= 3000) THEN 2
          WHEN positive_review_percentage >= 60 THEN 3
          ELSE 4
        END ASC,
        total_reviews DESC
    `,
  },
  'added-desc': {
    sql: 'ORDER BY date_added DESC',
  },
  'added-asc': {
    sql: 'ORDER BY date_added ASC',
  },
  'released-desc': {
    sql: 'ORDER BY release_date DESC',
  },
  'released-asc': {
    sql: 'ORDER BY release_date ASC',
  },
  'rating-desc': {
    sql: `
      ORDER BY
        CASE
          WHEN positive_review_percentage >= 80 THEN 1
          WHEN positive_review_percentage >= 70 THEN 2
          ELSE 3
        END ASC,
        positive_review_percentage DESC,
        total_reviews DESC
    `,
  },
  'price-asc': {
    sql: 'ORDER BY is_free DESC, COALESCE(price_eur, price_usd, 0) ASC',
  },
  'price-desc': {
    sql: 'ORDER BY is_free ASC, COALESCE(price_eur, price_usd, 0) DESC',
  },
  'reviews-desc': {
    sql: 'ORDER BY total_reviews DESC',
  },
  alphabetical: {
    sql: 'ORDER BY name ASC',
  },
}

/**
 * Hidden gems discovery criteria
 */
export const HIDDEN_GEMS = {
  /** Minimum rating percentage for hidden gems */
  MIN_RATING: 80,

  /** Minimum video coverage count */
  MIN_VIDEOS: 1,

  /** Maximum video coverage count */
  MAX_VIDEOS: 3,

  /** Minimum review count required */
  MIN_REVIEWS: 50,
} as const

/**
 * Time-based filtering constants (in days)
 */
export const TIME_RANGES = {
  /** Recent activity threshold */
  RECENT: 7,

  /** Semi-recent activity threshold */
  SEMI_RECENT: 14,

  /** Monthly activity threshold */
  MONTHLY: 30,

  /** Yearly threshold for old games */
  YEARLY: 365,
} as const

/**
 * Video coverage thresholds for smart sorting
 */
export const VIDEO_COVERAGE = {
  /** Low coverage threshold */
  LOW: 3,

  /** Medium coverage threshold */
  MEDIUM: 5,

  /** High coverage threshold */
  HIGH: 8,

  /** Minimum for trending classification */
  TRENDING_MIN: 2,

  /** Minimum for consensus classification */
  CONSENSUS_MIN: 2,

  /** Strong consensus threshold */
  STRONG_CONSENSUS: 3,
} as const

// Type exports for external use
export type TimingConfig = typeof TIMING
export type PricingConfig = typeof PRICING
export type RatingsConfig = typeof RATINGS
export type UILimitsConfig = typeof UI_LIMITS
export type LayoutConfig = typeof LAYOUT
export type I18NStringsConfig = typeof I18N_STRINGS
export type AnimationsConfig = typeof ANIMATIONS
export type HiddenGemsConfig = typeof HIDDEN_GEMS
export type TimeRangesConfig = typeof TIME_RANGES
export type VideoCoverageConfig = typeof VIDEO_COVERAGE
