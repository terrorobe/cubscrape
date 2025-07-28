/**
 * Composable for debounced filter updates to prevent excessive database queries
 * Provides a 400ms debounce delay for filter changes
 */

import { ref, type Ref } from 'vue'

/**
 * Filter change callback type
 */
export type FilterChangeCallback<T> = (filters: T) => void

/**
 * Debounced filters composable return type
 */
export interface DebouncedFiltersComposable<T> {
  pendingFilters: Ref<T>
  debouncedEmit: (newFilters: T) => void
  immediateEmit: (newFilters: T) => void
  cancelPendingUpdates: () => void
  cleanup: () => void
  hasPendingUpdates: () => boolean
}

export function useDebouncedFilters<T extends Record<string, any>>(
  initialFilters: T,
  onFiltersChanged: FilterChangeCallback<T>,
  debounceMs: number = 400,
): DebouncedFiltersComposable<T> {
  const pendingFilters = ref({ ...initialFilters }) as Ref<T>
  let debounceTimer: NodeJS.Timeout | null = null

  const debouncedEmit = (newFilters: T): void => {
    // Clear any existing timer
    if (debounceTimer) {
      clearTimeout(debounceTimer)
    }

    // Update pending filters immediately for UI responsiveness
    pendingFilters.value = { ...newFilters }

    // Debounce the actual filter change event
    debounceTimer = setTimeout(() => {
      onFiltersChanged(newFilters)
      debounceTimer = null
    }, debounceMs)
  }

  const immediateEmit = (newFilters: T): void => {
    // Clear any pending debounced updates
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }

    // Update immediately (for critical operations like presets or clear all)
    pendingFilters.value = { ...newFilters }
    onFiltersChanged(newFilters)
  }

  const cancelPendingUpdates = (): void => {
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }
  }

  // Cleanup on unmount
  const cleanup = (): void => {
    cancelPendingUpdates()
  }

  return {
    pendingFilters,
    debouncedEmit,
    immediateEmit,
    cancelPendingUpdates,
    cleanup,
    hasPendingUpdates: () => debounceTimer !== null,
  }
}