/**
 * Centralized filter event type system
 * Provides type-safe handling of filter change events across components
 */

import type {
  TimeFilterConfig,
  TimeFilterType,
  TimeFilterPreset,
} from './timeFilter'

/**
 * Complex filter value types that can be applied
 */
export type FilterValue =
  | string
  | string[]
  | number
  | boolean
  | { min: number; max: number }
  | {
      type: string | null
      preset: string | null
      startDate: string | null
      endDate: string | null
      smartLogic: string | null
    }
  | { minPrice: number; maxPrice: number }
  | null

/**
 * Filter remove event payload - used when removing individual filters
 */
export interface FilterRemoveEvent {
  type: string
  value: FilterValue
}

/**
 * Applied filter item interface for display
 */
export interface AppliedFilter {
  key: string
  type: string
  label: string
  value: FilterValue
}

/**
 * Type transformation utilities for component boundary compatibility
 */

/**
 * Generic time filter interface for storage/serialization (used in FilterConfig)
 */
export interface GenericTimeFilter {
  type: string | null
  preset: string | null
  startDate: string | null
  endDate: string | null
  smartLogic: string | null
}

/**
 * Type guard to check if string is valid TimeFilterType
 */
export function isValidTimeFilterType(
  value: string | null,
): value is TimeFilterType {
  return value === null || value === 'video' || value === 'release'
}

/**
 * Type guard to check if string is valid TimeFilterPreset
 */
export function isValidTimeFilterPreset(
  value: string | null,
): value is TimeFilterPreset {
  return (
    value === null ||
    [
      'last-week',
      'last-month',
      'last-3-months',
      'last-6-months',
      'last-year',
    ].includes(value)
  )
}

/**
 * Convert generic time filter to component-specific type
 * Provides type safety at component boundaries
 */
export function convertToTimeFilterConfig(
  genericFilter: GenericTimeFilter,
): TimeFilterConfig {
  return {
    type: isValidTimeFilterType(genericFilter.type) ? genericFilter.type : null,
    preset: isValidTimeFilterPreset(genericFilter.preset)
      ? genericFilter.preset
      : null,
    startDate: genericFilter.startDate,
    endDate: genericFilter.endDate,
    smartLogic: genericFilter.smartLogic,
  }
}

/**
 * Convert component-specific type back to generic type
 * For storage and serialization
 */
export function convertFromTimeFilterConfig(
  specificFilter: TimeFilterConfig,
): GenericTimeFilter {
  return {
    type: specificFilter.type,
    preset: specificFilter.preset,
    startDate: specificFilter.startDate,
    endDate: specificFilter.endDate,
    smartLogic: specificFilter.smartLogic,
  }
}
