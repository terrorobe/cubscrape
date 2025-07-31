<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

interface Props {
  currentPage: number
  totalPages: number
  totalItems: number
  startIndex: number
  endIndex: number
  remainingItems: number
  pageSize: number
  hasNextPage: boolean
  hasPrevPage: boolean
  loading: boolean
  visiblePages: number[]
  showFirstPage: boolean
  showLastPage: boolean
  showLeftEllipsis: boolean
  showRightEllipsis: boolean
  loadMoreVisible: boolean
  getPageButtonClass: (page: number) => string[]
  getNavButtonClass: () => string[]
}

interface Emits {
  goToPage: [page: number]
  loadMore: []
  jumpToPage: [page: number]
  setPageSize: [size: number]
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const jumpToPageValue = ref<number | null>(null)

// Keyboard navigation
const handleKeydown = (event: KeyboardEvent) => {
  // Only handle pagination keys when not focused on an input
  if ((event.target as HTMLElement)?.tagName === 'INPUT') {
    return
  }

  switch (event.key) {
    case 'ArrowLeft':
      if (props.hasPrevPage) {
        event.preventDefault()
        emit('goToPage', props.currentPage - 1)
      }
      break
    case 'ArrowRight':
      if (props.hasNextPage) {
        event.preventDefault()
        emit('goToPage', props.currentPage + 1)
      }
      break
    case 'Home':
      if (event.ctrlKey && props.currentPage !== 1) {
        event.preventDefault()
        emit('goToPage', 1)
      }
      break
    case 'End':
      if (event.ctrlKey && props.currentPage !== props.totalPages) {
        event.preventDefault()
        emit('goToPage', props.totalPages)
      }
      break
  }
}

const handleJumpToPage = () => {
  if (jumpToPageValue.value && jumpToPageValue.value !== props.currentPage) {
    emit('jumpToPage', jumpToPageValue.value)
  }
  jumpToPageValue.value = null
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div class="pagination-container w-full">
    <!-- Results Summary -->
    <div
      class="results-summary mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <div class="flex items-center gap-4">
        <span class="text-sm text-text-secondary">
          Showing {{ startIndex + 1 }}-{{ endIndex }} of
          {{ totalItems.toLocaleString() }} games
        </span>
      </div>

      <div class="flex items-center gap-4">
        <!-- Page Size Selector -->
        <div class="page-size-selector">
          <label class="text-sm text-text-secondary">
            Show:
            <select
              :value="pageSize"
              @change="emit('setPageSize', parseInt(($event.target as HTMLSelectElement).value))"
              class="border-border ml-2 rounded-sm border bg-bg-secondary px-2 py-1 text-text-primary focus:ring-2 focus:ring-accent focus:ring-offset-2"
            >
              <option value="50">50</option>
              <option value="100">100</option>
              <option value="150">150</option>
              <option value="200">200</option>
            </select>
          </label>
        </div>
      </div>
    </div>

    <!-- Load More Button (Primary Action) -->
    <div v-if="hasNextPage && loadMoreVisible" class="load-more-section mb-8">
      <button
        @click="emit('loadMore')"
        :disabled="loading"
        class="load-more-btn mx-auto block w-full max-w-md rounded-lg bg-accent px-8 py-4 font-medium text-white transition-all duration-200 hover:bg-accent-hover focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:outline-none active:scale-98 disabled:opacity-50"
        style="min-height: 56px"
      >
        <span v-if="!loading" class="flex items-center justify-center gap-2">
          <span>Load More Games</span>
          <span class="text-white/80"
            >({{ remainingItems.toLocaleString() }} remaining)</span
          >
        </span>
        <span v-else class="flex items-center justify-center gap-2">
          <div
            class="size-5 animate-spin rounded-full border-2 border-white border-t-transparent"
          ></div>
          Loading...
        </span>
      </button>
    </div>

    <!-- Traditional Pagination Navigation -->
    <nav class="pagination-nav" aria-label="Game pages" v-if="totalPages > 1">
      <div class="flex flex-col items-center gap-6">
        <!-- Main pagination controls -->
        <div class="flex items-center gap-2">
          <!-- Previous Button -->
          <button
            @click="emit('goToPage', currentPage - 1)"
            :disabled="!hasPrevPage"
            :class="getNavButtonClass()"
            aria-label="Previous page"
          >
            <svg
              class="size-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M15 19l-7-7 7-7"
              />
            </svg>
            <span class="hidden sm:inline">Previous</span>
          </button>

          <!-- Page Numbers (Smart Truncation) -->
          <div class="page-numbers flex items-center gap-1">
            <!-- First page -->
            <button
              v-if="showFirstPage"
              @click="emit('goToPage', 1)"
              :class="getPageButtonClass(1)"
              aria-label="Page 1"
            >
              1
            </button>

            <!-- Left ellipsis -->
            <span
              v-if="showLeftEllipsis"
              class="px-2 text-text-secondary select-none"
              >...</span
            >

            <!-- Visible page range -->
            <button
              v-for="page in visiblePages"
              :key="page"
              @click="emit('goToPage', page)"
              :class="getPageButtonClass(page)"
              :aria-label="`${page === currentPage ? 'Current page, ' : ''}Page ${page}`"
              :aria-current="page === currentPage ? 'page' : undefined"
            >
              {{ page }}
            </button>

            <!-- Right ellipsis -->
            <span
              v-if="showRightEllipsis"
              class="px-2 text-text-secondary select-none"
              >...</span
            >

            <!-- Last page -->
            <button
              v-if="showLastPage"
              @click="emit('goToPage', totalPages)"
              :class="getPageButtonClass(totalPages)"
              :aria-label="`Page ${totalPages}`"
            >
              {{ totalPages }}
            </button>
          </div>

          <!-- Next Button -->
          <button
            @click="emit('goToPage', currentPage + 1)"
            :disabled="!hasNextPage"
            :class="getNavButtonClass()"
            aria-label="Next page"
          >
            <span class="hidden sm:inline">Next</span>
            <svg
              class="size-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 5l7 7-7 7"
              />
            </svg>
          </button>
        </div>

        <!-- Jump to Page (Desktop Only) -->
        <div class="jump-to-page hidden items-center gap-3 md:flex">
          <label class="flex items-center gap-2 text-sm text-text-secondary">
            Jump to page:
            <input
              v-model.number="jumpToPageValue"
              @keydown.enter="handleJumpToPage"
              type="number"
              :min="1"
              :max="totalPages"
              :placeholder="currentPage.toString()"
              class="border-border w-16 rounded-sm border bg-bg-secondary px-2 py-1 text-center text-text-primary focus:ring-2 focus:ring-accent focus:ring-offset-2"
            />
          </label>
          <button
            @click="handleJumpToPage"
            :disabled="!jumpToPageValue || jumpToPageValue === currentPage"
            class="hover:bg-bg-tertiary border-border rounded-sm border bg-bg-secondary px-3 py-1 text-sm text-text-primary transition-all duration-150 hover:border-accent/30 focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
          >
            Go
          </button>
        </div>

        <!-- Keyboard shortcuts hint -->
        <div
          class="keyboard-hints hidden text-center text-xs text-text-secondary/70 lg:block"
        >
          Use arrow keys to navigate • Ctrl+Home/End for first/last page
        </div>
      </div>
    </nav>
  </div>
</template>

<style scoped>
/* Ensure smooth transitions */
.pagination-container * {
  transition-property:
    background-color, border-color, color, transform, opacity;
}

/* Custom active scale for better feedback */
.active\:scale-98:active {
  transform: scale(0.98);
}

/* Loading spinner animation */
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.animate-spin {
  animation: spin 1s linear infinite;
}

/* Mobile responsive adjustments */
@media (max-width: 640px) {
  .page-numbers {
    gap: 0.25rem;
  }

  .page-btn {
    min-width: 40px;
    height: 40px;
    padding-left: 0.5rem;
    padding-right: 0.5rem;
    font-size: 0.75rem;
  }

  .nav-btn {
    min-width: 40px;
    min-height: 40px;
    padding-left: 0.75rem;
    padding-right: 0.75rem;
  }
}
</style>
