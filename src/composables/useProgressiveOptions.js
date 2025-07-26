/**
 * Composable for progressive loading of filter options (tags, channels)
 * Loads popular options first, then loads more on demand
 */

import { ref, computed } from 'vue'

export function useProgressiveOptions(
  allOptions,
  initialLoadCount = 20,
  loadMoreCount = 10,
) {
  // Handle reactive refs and ensure we always have an array
  const getOptionsArray = () => {
    const options =
      typeof allOptions === 'function'
        ? allOptions()
        : (allOptions?.value ?? allOptions)
    return Array.isArray(options) ? options : []
  }

  const currentLoadCount = ref(
    Math.min(initialLoadCount, getOptionsArray().length),
  )
  const searchQuery = ref('')
  const isLoading = ref(false)

  // Visible options based on current load count and search
  const visibleOptions = computed(() => {
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
  const hasMore = computed(() => {
    const optionsArray = getOptionsArray()
    if (searchQuery.value.trim()) {
      return false // When searching, show all results
    }
    return currentLoadCount.value < optionsArray.length
  })

  // Load more options
  const loadMore = () => {
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
  const reset = () => {
    const optionsArray = getOptionsArray()
    currentLoadCount.value = Math.min(initialLoadCount, optionsArray.length)
    searchQuery.value = ''
  }

  // Update search query
  const updateSearch = (query) => {
    searchQuery.value = query
  }

  // Get option statistics
  const optionStats = computed(() => {
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
