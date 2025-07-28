/**
 * Composable for progressive loading of filter options (tags, channels)
 * Loads popular options first, then loads more on demand
 */

import { ref, computed, type Ref, type ComputedRef } from 'vue'

/**
 * Option interface with name and count
 */
export interface OptionWithCount {
  name: string
  count: number
  isPopular?: boolean
}

/**
 * Option statistics interface
 */
export interface OptionStats {
  visible: number
  total: number
  loaded: number
  hasMore: boolean
}

/**
 * Progressive options composable return type
 */
export interface ProgressiveOptionsComposable {
  visibleOptions: ComputedRef<OptionWithCount[]>
  searchQuery: Ref<string>
  isLoading: Ref<boolean>
  hasMore: ComputedRef<boolean>
  optionStats: ComputedRef<OptionStats>
  loadMore: () => void
  reset: () => void
  updateSearch: (query: string) => void
}

/**
 * All options parameter type - can be array, ref, or function returning array
 */
export type AllOptionsParameter =
  | OptionWithCount[]
  | Ref<OptionWithCount[]>
  | (() => OptionWithCount[])

export function useProgressiveOptions(
  allOptions: AllOptionsParameter,
  initialLoadCount: number = 20,
  loadMoreCount: number = 10,
): ProgressiveOptionsComposable {
  // Handle reactive refs and ensure we always have an array
  const getOptionsArray = (): OptionWithCount[] => {
    const options =
      typeof allOptions === 'function'
        ? allOptions()
        : ((allOptions as any)?.value ?? allOptions)
    return Array.isArray(options) ? options : []
  }

  const currentLoadCount = ref(
    Math.min(initialLoadCount, getOptionsArray().length),
  )
  const searchQuery = ref('')
  const isLoading = ref(false)

  // Visible options based on current load count and search
  const visibleOptions = computed((): OptionWithCount[] => {
    const optionsArray = getOptionsArray()
    let options = optionsArray.slice(0, currentLoadCount.value)

    // If searching, show all matching options
    if (searchQuery.value.trim()) {
      const query = searchQuery.value.toLowerCase()
      options = optionsArray.filter((option) =>
        option.name.toLowerCase().includes(query),
      )
    }

    return options
  })

  // Whether there are more options to load
  const hasMore = computed((): boolean => {
    const optionsArray = getOptionsArray()
    if (searchQuery.value.trim()) {
      return false // When searching, show all results
    }
    return currentLoadCount.value < optionsArray.length
  })

  // Load more options
  const loadMore = (): void => {
    if (hasMore.value && !isLoading.value) {
      isLoading.value = true

      // Simulate async loading with a small delay for UX
      setTimeout(() => {
        const optionsArray = getOptionsArray()
        currentLoadCount.value = Math.min(
          currentLoadCount.value + loadMoreCount,
          optionsArray.length,
        )
        isLoading.value = false
      }, 50)
    }
  }

  // Reset to initial load count
  const reset = (): void => {
    const optionsArray = getOptionsArray()
    currentLoadCount.value = Math.min(initialLoadCount, optionsArray.length)
    searchQuery.value = ''
  }

  // Update search query
  const updateSearch = (query: string): void => {
    searchQuery.value = query
  }

  // Get option statistics
  const optionStats = computed((): OptionStats => {
    const optionsArray = getOptionsArray()
    return {
      visible: visibleOptions.value.length,
      total: optionsArray.length,
      loaded: currentLoadCount.value,
      hasMore: hasMore.value,
    }
  })

  return {
    visibleOptions,
    searchQuery,
    isLoading,
    hasMore,
    optionStats,
    loadMore,
    reset,
    updateSearch,
  }
}
