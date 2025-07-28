/**
 * Centralized filter event type system
 * Provides type-safe handling of filter change events across components
 */

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
  | { minPrice: number; maxPrice: number; includeFree: boolean }
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