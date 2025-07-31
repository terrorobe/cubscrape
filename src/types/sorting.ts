/**
 * Centralized sorting type system
 * Provides type-safe handling of all sort specifications across components
 */

import { debug } from '../utils/debug'

/**
 * Available sort fields for advanced sorting
 */
export type SortField =
  | 'rating'
  | 'coverage'
  | 'recency'
  | 'release'
  | 'price'
  | 'channels'
  | 'reviews'

/**
 * Sort direction
 */
export type SortDirection = 'asc' | 'desc'

/**
 * Sort criteria for individual sort fields
 */
export interface SortCriteria {
  field: SortField
  direction: SortDirection
  weight?: number
}

/**
 * Advanced multi-criteria sort specification
 */
export interface AdvancedSortSpec {
  mode: 'advanced'
  primary: SortCriteria
  secondary?: SortCriteria | null
}

/**
 * Simple object-based sort specification
 */
export interface SimpleSortSpec {
  mode: 'simple'
  field: SortField
  direction: SortDirection
}

/**
 * Comprehensive sort specification type (discriminated union)
 */
export type SortSpec = AdvancedSortSpec | SimpleSortSpec | string | null

/**
 * Sort change event payload
 */
export interface SortChangeEvent {
  sortBy: string
  sortSpec: SortSpec
}

/**
 * Type guard for advanced sort specifications
 */
export function isAdvancedSortSpec(
  sortSpec: unknown,
): sortSpec is AdvancedSortSpec {
  return (
    typeof sortSpec === 'object' &&
    sortSpec !== null &&
    'mode' in sortSpec &&
    (sortSpec as Record<string, unknown>).mode === 'advanced' &&
    'primary' in sortSpec &&
    typeof (sortSpec as Record<string, unknown>).primary === 'object'
  )
}

/**
 * Type guard for simple sort specifications
 */
export function isSimpleSortSpec(
  sortSpec: unknown,
): sortSpec is SimpleSortSpec {
  return (
    typeof sortSpec === 'object' &&
    sortSpec !== null &&
    'mode' in sortSpec &&
    (sortSpec as Record<string, unknown>).mode === 'simple' &&
    'field' in sortSpec &&
    'direction' in sortSpec
  )
}

/**
 * Type guard for string sort specifications
 */
export function isStringSortSpec(sortSpec: unknown): sortSpec is string {
  return typeof sortSpec === 'string' && sortSpec.length > 0
}

/**
 * Normalize any sort specification to a consistent format
 */
export function normalizeSortSpec(sortSpec: unknown): SortSpec {
  // Handle null/undefined
  if (!sortSpec) {
    return null
  }

  // Handle string sorts
  if (isStringSortSpec(sortSpec)) {
    return sortSpec
  }

  // Handle already normalized sorts
  if (isAdvancedSortSpec(sortSpec) || isSimpleSortSpec(sortSpec)) {
    return sortSpec
  }

  // Fallback to null for unrecognized formats
  debug.warn('Unable to normalize sort specification:', sortSpec)
  return null
}

/**
 * Serialize sort specification for storage/URL
 */
export function serializeSortSpec(sortSpec: SortSpec): string {
  if (!sortSpec) {
    return ''
  }

  if (isStringSortSpec(sortSpec)) {
    return sortSpec
  }

  if (isSimpleSortSpec(sortSpec)) {
    return JSON.stringify({
      field: sortSpec.field,
      direction: sortSpec.direction,
    })
  }

  if (isAdvancedSortSpec(sortSpec)) {
    return JSON.stringify({
      mode: sortSpec.mode,
      primary: sortSpec.primary,
      secondary: sortSpec.secondary,
    })
  }

  return ''
}

/**
 * Deserialize sort specification from storage/URL
 */
export function deserializeSortSpec(serialized: string): SortSpec {
  if (!serialized || serialized.trim() === '') {
    return null
  }

  // Handle simple string sorts
  if (!serialized.startsWith('{') && !serialized.startsWith('[')) {
    return serialized
  }

  // Handle JSON sorts
  try {
    const parsed = JSON.parse(serialized)
    return normalizeSortSpec(parsed)
  } catch (error) {
    debug.warn('Failed to deserialize sort specification:', serialized, error)
    return null
  }
}

/**
 * Get display name for sort specification
 */
export function getSortDisplayName(sortSpec: SortSpec): string {
  if (!sortSpec) {
    return ''
  }

  if (isStringSortSpec(sortSpec)) {
    const displayNames: Record<string, string> = {
      date: 'Latest Videos',
      'rating-score': 'Rating Score',
      'rating-category': 'Rating Category',
      'best-value': 'Best Value',
      'hidden-gems': 'Hidden Gems',
      trending: 'Trending',
      relevance: 'Relevance',
    }
    return displayNames[sortSpec] || sortSpec
  }

  if (isSimpleSortSpec(sortSpec)) {
    return `${sortSpec.field} (${sortSpec.direction})`
  }

  if (isAdvancedSortSpec(sortSpec)) {
    return `Advanced: ${sortSpec.primary.field} (${sortSpec.primary.direction})`
  }

  return 'Custom'
}
