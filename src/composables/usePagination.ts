import { ref, computed, watch, type Ref } from 'vue'

export interface PaginationOptions {
  pageSize?: number
  maxVisiblePages?: number
  enableLoadMore?: boolean
  onPageChange?: () => void
}

export function usePagination<T>(
  items: Ref<T[]>,
  options: PaginationOptions = {},
) {
  const {
    pageSize: initialPageSize = 150,
    maxVisiblePages = 7,
    enableLoadMore = true,
    onPageChange,
  } = options

  // State
  const currentPage = ref(1)
  const pageSize = ref(initialPageSize)
  const loadMoreVisible = ref(enableLoadMore)
  const loading = ref(false)
  const jumpToPageValue = ref<number | null>(null)

  // Computed properties
  const totalPages = computed(() =>
    Math.ceil(items.value.length / pageSize.value),
  )

  const totalItems = computed(() => items.value.length)

  const startIndex = computed(() => (currentPage.value - 1) * pageSize.value)

  const endIndex = computed(() =>
    Math.min(startIndex.value + pageSize.value, totalItems.value),
  )

  const currentPageItems = computed(() =>
    items.value.slice(startIndex.value, endIndex.value),
  )

  const hasNextPage = computed(() => currentPage.value < totalPages.value)

  const hasPrevPage = computed(() => currentPage.value > 1)

  const remainingItems = computed(() =>
    Math.max(0, totalItems.value - endIndex.value),
  )

  // Smart page number display
  const visiblePages = computed(() => {
    const pages: number[] = []
    const current = currentPage.value
    const total = totalPages.value
    const maxVisible = maxVisiblePages

    if (total <= maxVisible) {
      // Show all pages
      for (let i = 1; i <= total; i++) {
        pages.push(i)
      }
    } else {
      // Smart truncation
      const sidePages = Math.floor((maxVisible - 3) / 2) // -3 for first, last, current
      let startPage = Math.max(2, current - sidePages)
      let endPage = Math.min(total - 1, current + sidePages)

      // Adjust if we're near the beginning or end
      if (current <= sidePages + 2) {
        endPage = Math.min(total - 1, maxVisible - 1)
      }
      if (current >= total - sidePages - 1) {
        startPage = Math.max(2, total - maxVisible + 2)
      }

      for (let i = startPage; i <= endPage; i++) {
        pages.push(i)
      }
    }

    return pages
  })

  const showFirstPage = computed(
    () => totalPages.value > 1 && !visiblePages.value.includes(1),
  )

  const showLastPage = computed(
    () =>
      totalPages.value > 1 && !visiblePages.value.includes(totalPages.value),
  )

  const showLeftEllipsis = computed(
    () => visiblePages.value.length > 0 && visiblePages.value[0] > 2,
  )

  const showRightEllipsis = computed(
    () =>
      visiblePages.value.length > 0 &&
      visiblePages.value[visiblePages.value.length - 1] < totalPages.value - 1,
  )

  // Methods
  const goToPage = (page: number) => {
    if (page >= 1 && page <= totalPages.value && page !== currentPage.value) {
      currentPage.value = page

      // Scroll to top of results smoothly
      const gameGrid = document.querySelector('.game-grid')
      if (gameGrid) {
        gameGrid.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        })
      }

      // Notify parent of page change for URL updates
      onPageChange?.()
    }
  }

  const loadMore = async () => {
    if (hasNextPage.value && !loading.value) {
      loading.value = true

      // Small delay for better UX
      await new Promise((resolve) => setTimeout(resolve, 200))

      currentPage.value++
      loading.value = false

      // Scroll to top of results smoothly
      const gameGrid = document.querySelector('.game-grid')
      if (gameGrid) {
        gameGrid.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        })
      }

      // Notify parent of page change for URL updates
      onPageChange?.()
    }
  }

  const handleJumpToPage = () => {
    if (jumpToPageValue.value && jumpToPageValue.value !== currentPage.value) {
      goToPage(jumpToPageValue.value)
    }
    jumpToPageValue.value = null
  }

  const setPageSize = (newSize: number) => {
    // Maintain approximate position when changing page size
    const currentFirstItem = startIndex.value
    pageSize.value = newSize
    currentPage.value = Math.floor(currentFirstItem / newSize) + 1
    
    // Notify parent of page change for URL updates
    onPageChange?.()
  }

  const getPageButtonClass = (page: number) => [
    'page-btn',
    'min-w-[44px] h-11 px-3 rounded-lg text-sm font-medium transition-all duration-150',
    'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2',
    'active:scale-95',
    page === currentPage.value
      ? 'bg-accent text-white shadow-sm'
      : 'bg-bg-secondary text-text-primary hover:bg-bg-tertiary border border-border hover:border-accent/30',
  ]

  const getNavButtonClass = () => [
    'nav-btn',
    'flex items-center gap-2 px-4 py-2.5 rounded-lg border border-border bg-bg-secondary text-text-primary',
    'hover:bg-bg-tertiary hover:border-accent/30 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2',
    'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-bg-secondary disabled:hover:border-border',
    'transition-all duration-150 active:scale-95',
    'min-w-[44px] min-h-[44px]',
  ]

  // Reset to page 1 when items change (new filters)
  watch(
    () => items.value.length,
    () => {
      currentPage.value = 1
    },
  )

  return {
    // State
    currentPage,
    pageSize,
    loadMoreVisible,
    loading,
    jumpToPageValue,

    // Computed
    totalPages,
    totalItems,
    startIndex,
    endIndex,
    currentPageItems,
    hasNextPage,
    hasPrevPage,
    remainingItems,
    visiblePages,
    showFirstPage,
    showLastPage,
    showLeftEllipsis,
    showRightEllipsis,

    // Methods
    goToPage,
    loadMore,
    handleJumpToPage,
    setPageSize,
    getPageButtonClass,
    getNavButtonClass,
  }
}
