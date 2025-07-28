/**
 * Theme configuration for colors, spacing, and visual design tokens
 * @module config/theme
 */

/**
 * Rating color configuration with background and text color
 */
interface RatingColor {
  background: string
  text: 'text-black' | 'text-white'
}

/**
 * Rating color system based on review percentages and summaries
 * Each color includes HSL values and text color recommendations
 */
export const RATING_COLORS: Record<string, RatingColor> = {
  // Review summary-based colors (take precedence)
  OVERWHELMINGLY_POSITIVE: {
    background: 'hsl(120, 70%, 40%)', // Deep green
    text: 'text-black',
  },
  VERY_POSITIVE: {
    background: 'hsl(100, 60%, 50%)', // Bright green
    text: 'text-black',
  },
  MOSTLY_POSITIVE: {
    background: 'hsl(80, 60%, 50%)', // Yellow-green
    text: 'text-black',
  },
  POSITIVE: {
    background: 'hsl(60, 60%, 50%)', // Yellow
    text: 'text-black',
  },
  MIXED: {
    background: 'hsl(45, 60%, 50%)', // Orange-yellow
    text: 'text-black',
  },
  MOSTLY_NEGATIVE: {
    background: 'hsl(20, 60%, 50%)', // Orange-red
    text: 'text-white',
  },
  OVERWHELMINGLY_NEGATIVE: {
    background: 'hsl(0, 80%, 40%)', // Deep red
    text: 'text-white',
  },
  VERY_NEGATIVE: {
    background: 'hsl(10, 70%, 50%)', // Red
    text: 'text-white',
  },
  NEGATIVE: {
    background: 'hsl(15, 65%, 45%)', // Light red
    text: 'text-white',
  },

  // Percentage-based fallbacks
  HIGH: {
    background: 'hsl(120, 70%, 40%)', // 80%+ - Deep green
    text: 'text-black',
  },
  MEDIUM: {
    background: 'hsl(45, 60%, 50%)', // 50-79% - Orange-yellow
    text: 'text-black',
  },
  LOW: {
    background: 'hsl(0, 80%, 40%)', // <50% - Deep red
    text: 'text-white',
  },
  UNKNOWN: {
    background: 'hsl(0, 0%, 50%)', // No data - Gray
    text: 'text-white',
  },
} as const

/**
 * Platform color configuration
 */
interface PlatformColor {
  primary: string
  secondary: string
  accent: string
}

/**
 * Platform-specific colors and styles
 */
export const PLATFORM_COLORS: Record<
  'steam' | 'itch' | 'crazygames',
  PlatformColor
> = {
  steam: {
    primary: '#1b2838',
    secondary: '#66c0f4',
    accent: '#00aeff',
  },
  itch: {
    primary: '#fa5c5c',
    secondary: '#ff2449',
    accent: '#fa5c5c',
  },
  crazygames: {
    primary: '#7b2ff7',
    secondary: '#9747ff',
    accent: '#7b2ff7',
  },
} as const

/**
 * CSS transition timing functions
 */
export const TRANSITIONS = {
  easing: {
    default: 'ease',
    easeIn: 'ease-in',
    easeOut: 'ease-out',
    easeInOut: 'ease-in-out',
  },
} as const

/**
 * Opacity values for various UI states
 */
export const OPACITY = {
  /** Disabled elements */
  disabled: 0.5,

  /** Subtle elements (timestamps, metadata) */
  subtle: 0.7,

  /** Hover state overlays */
  hoverOverlay: 0.1,

  /** Active state overlays */
  activeOverlay: 0.2,
} as const

/**
 * Z-index layering system
 */
export const Z_INDEX = {
  /** Base content layer */
  base: 0,

  /** Sticky elements (headers, sidebars) */
  sticky: 10,

  /** Dropdown menus and popovers */
  dropdown: 20,

  /** Modal overlays */
  modal: 30,

  /** Toast notifications */
  toast: 40,

  /** Critical UI elements that must always be on top */
  critical: 50,
} as const

/**
 * Border radius values
 */
export const BORDERS = {
  radius: {
    none: '0',
    sm: '0.125rem', // 2px
    DEFAULT: '0.25rem', // 4px
    md: '0.375rem', // 6px
    lg: '0.5rem', // 8px
    xl: '0.75rem', // 12px
    full: '9999px',
  },
} as const

/**
 * Shadow definitions
 */
export const SHADOWS = {
  sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  DEFAULT: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
  md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
  lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
} as const

/**
 * Helper function to get rating color based on percentage and review summary
 */
export function getRatingColor(
  percentage?: number | null,
  reviewSummary?: string | null,
): RatingColor {
  if (!percentage) {
    return RATING_COLORS.UNKNOWN
  }

  // Check review summary first for more specific classification
  if (reviewSummary) {
    const summary = reviewSummary.toLowerCase()

    if (summary.includes('overwhelmingly positive')) {
      return RATING_COLORS.OVERWHELMINGLY_POSITIVE
    }
    if (summary.includes('very positive')) {
      return RATING_COLORS.VERY_POSITIVE
    }
    if (summary.includes('mostly positive')) {
      return RATING_COLORS.MOSTLY_POSITIVE
    }
    if (summary.includes('positive')) {
      return RATING_COLORS.POSITIVE
    }
    if (summary.includes('mixed')) {
      return RATING_COLORS.MIXED
    }
    if (summary.includes('mostly negative')) {
      return RATING_COLORS.MOSTLY_NEGATIVE
    }
    if (summary.includes('overwhelmingly negative')) {
      return RATING_COLORS.OVERWHELMINGLY_NEGATIVE
    }
    if (summary.includes('very negative')) {
      return RATING_COLORS.VERY_NEGATIVE
    }
    if (summary.includes('negative')) {
      return RATING_COLORS.NEGATIVE
    }
  }

  // Fallback to percentage-based classification
  if (percentage >= 80) {
    return RATING_COLORS.HIGH
  }
  if (percentage >= 50) {
    return RATING_COLORS.MEDIUM
  }
  return RATING_COLORS.LOW
}

// Type exports for external use
export type RatingColorConfig = typeof RATING_COLORS
export type PlatformColorConfig = typeof PLATFORM_COLORS
export type TransitionConfig = typeof TRANSITIONS
export type OpacityConfig = typeof OPACITY
export type ZIndexConfig = typeof Z_INDEX
export type BordersConfig = typeof BORDERS
export type ShadowsConfig = typeof SHADOWS
