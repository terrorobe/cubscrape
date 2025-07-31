/**
 * Time filter types - shared between components and type system
 */

/**
 * Time filter type options
 */
export type TimeFilterType = 'video' | 'release' | null

/**
 * Time filter preset options
 */
export type TimeFilterPreset =
  | 'last-week'
  | 'last-month'
  | 'last-3-months'
  | 'last-6-months'
  | 'last-year'
  | null

/**
 * Time filter configuration for components
 */
export interface TimeFilterConfig {
  type: TimeFilterType
  preset: TimeFilterPreset
  startDate: string | null
  endDate: string | null
  smartLogic: string | null
}
