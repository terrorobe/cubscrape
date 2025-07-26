/**
 * Composable for debounced filter updates to prevent excessive database queries
 * Provides a 400ms debounce delay for filter changes
 */

import { ref } from 'vue'

export function useDebouncedFilters(
  initialFilters,
  onFiltersChanged,
  debounceMs = 400,
) {
  const pendingFilters = ref({ ...initialFilters })
  let debounceTimer = null

  const debouncedEmit = (newFilters) => {
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

  const immediateEmit = (newFilters) => {
    // Clear any pending debounced updates
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }

    // Update immediately (for critical operations like presets or clear all)
    pendingFilters.value = { ...newFilters }
    onFiltersChanged(newFilters)
  }

  const cancelPendingUpdates = () => {
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }
  }

  // Cleanup on unmount
  const cleanup = () => {
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
