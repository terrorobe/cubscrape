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
  const currentLoadCount = ref(Math.min(initialLoadCount, allOptions.length))
  const searchQuery = ref('')
  const isLoading = ref(false)

  // Visible options based on current load count and search
  const visibleOptions = computed(() => {
    let options = allOptions.slice(0, currentLoadCount.value)

    // If searching, show all matching options
    if (searchQuery.value.trim()) {
      const query = searchQuery.value.toLowerCase()
      options = allOptions.filter((option) =>
        option.name.toLowerCase().includes(query),
      )
    }

    return options
  })

  // Whether there are more options to load
  const hasMore = computed(() => {
    if (searchQuery.value.trim()) {
      return false // When searching, show all results
    }
    return currentLoadCount.value < allOptions.length
  })

  // Load more options
  const loadMore = () => {
    if (hasMore.value && !isLoading.value) {
      isLoading.value = true

      // Simulate async loading with a small delay for UX
      setTimeout(() => {
        currentLoadCount.value = Math.min(
          currentLoadCount.value + loadMoreCount,
          allOptions.length,
        )
        isLoading.value = false
      }, 50)
    }
  }

  // Reset to initial load count
  const reset = () => {
    currentLoadCount.value = Math.min(initialLoadCount, allOptions.length)
    searchQuery.value = ''
  }

  // Update search query
  const updateSearch = (query) => {
    searchQuery.value = query
  }

  // Get option statistics
  const optionStats = computed(() => ({
    visible: visibleOptions.value.length,
    total: allOptions.length,
    loaded: currentLoadCount.value,
    hasMore: hasMore.value,
  }))

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
