<script setup lang="ts">
import { ref, computed, watch, type Ref } from 'vue'
import GameCard from './GameCard.vue'
import SortIndicator from './SortIndicator.vue'
import PaginationControls from './PaginationControls.vue'
import { usePagination } from '../composables/usePagination'
import type { ProcessedGameData } from '../services/GameDataProcessingService'
import type { SortSpec, SortChangeEvent } from '../types/sorting'
import type { VideoData } from '../types/database'

// Component interfaces
export interface SearchState {
  query: string
  searchInVideoTitles: boolean
}

export interface PaginationConfig {
  initialPageSize?: number
  enableLoadMore?: boolean
  onPageChange?: () => void
}

interface Props {
  // Search state
  searchState: SearchState

  // Filter state
  currency: 'eur' | 'usd'
  sortBy: string
  sortSpec: SortSpec
  selectedTags: string[]

  // Game data
  filteredGames: ProcessedGameData[]
  highlightedGameId: string | null

  // Pagination configuration
  paginationConfig?: PaginationConfig

  // State flags
  loading: boolean
  error: string | null

  // Database functions
  loadGameVideos?: (gameId: string) => VideoData[]
}

interface Emits {
  // Search events
  'update:searchState': [value: SearchState]

  // Sort events
  sortChanged: [sortData: SortChangeEvent]

  // Game interaction events
  clearHighlight: []
  tagClick: [tag: string]

  // Pagination events (for URL updates)
  paginationChanged: [{ currentPage: number; pageSize: number }]

  // Sharing events
  copyCurrentFiltersLink: []
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Template refs
const gameGrid: Ref<HTMLElement | null> = ref(null)

// Set up pagination inside the component
const {
  currentPage,
  pageSize,
  totalPages,
  startIndex,
  endIndex,
  currentPageItems: currentPageGames,
  hasNextPage,
  hasPrevPage,
  remainingItems,
  loading: paginationLoading,
  loadMoreVisible,
  visiblePages,
  showFirstPage,
  showLastPage,
  showLeftEllipsis,
  showRightEllipsis,
  goToPage,
  loadMore,
  setPageSize,
  getPageButtonClass,
  getNavButtonClass,
} = usePagination(
  computed(() => props.filteredGames),
  {
    pageSize: props.paginationConfig?.initialPageSize || 150,
    enableLoadMore: props.paginationConfig?.enableLoadMore ?? true,
    onPageChange: () => {
      // Emit pagination changes for URL updates
      emit('paginationChanged', {
        currentPage: currentPage.value,
        pageSize: pageSize.value,
      })
      // Call parent's onPageChange if provided
      props.paginationConfig?.onPageChange?.()
    },
  },
)

// Event handlers
const handleSortChange = (sortData: SortChangeEvent): void => {
  emit('sortChanged', sortData)
}

const handleTagClick = (tag: string): void => {
  emit('tagClick', tag)
}

const handleClearHighlight = (): void => {
  emit('clearHighlight')
}

const handleCopyCurrentFiltersLink = (): void => {
  emit('copyCurrentFiltersLink')
}

// Search computed properties for v-model
const searchQueryModel = computed({
  get: () => props.searchState.query,
  set: (value: string) =>
    emit('update:searchState', {
      query: value,
      searchInVideoTitles: props.searchState.searchInVideoTitles,
    }),
})

const searchInVideoTitlesModel = computed({
  get: () => props.searchState.searchInVideoTitles,
  set: (value: boolean) => {
    emit('update:searchState', {
      query: props.searchState.query,
      searchInVideoTitles: value,
    })
    // Trigger mode change feedback
    showModeChangeMessage.value = true
    setTimeout(() => {
      showModeChangeMessage.value = false
    }, 2000)
  },
})

// Animation state
const showModeChangeMessage = ref(false)
const showResultsPulse = ref(false)

// Watch for filtered games changes to trigger animations
watch(
  () => props.filteredGames,
  () => {
    // Trigger pulse animation on results count
    showResultsPulse.value = true
    setTimeout(() => {
      showResultsPulse.value = false
    }, 800)
  },
)

// Pagination event handlers (now handled internally)
const handleGoToPage = (page: number): void => {
  goToPage(page)
}

const handleLoadMore = (): void => {
  loadMore()
}

const handleJumpToPageInternal = (page: number): void => {
  goToPage(page)
}

const handleSetPageSize = (size: number): void => {
  setPageSize(size)
}
</script>

<template>
  <div class="game-discovery-container relative">
    <!-- Sort, Search & Status Info -->
    <div class="mb-5 text-text-secondary">
      <!-- Desktop layout -->
      <div class="hidden md:flex md:items-center md:justify-between md:gap-4">
        <!-- Sort Indicator -->
        <div class="flex items-center gap-4">
          <SortIndicator
            :sort-by="sortBy"
            :sort-spec="sortSpec"
            :game-count="filteredGames.length"
            @sort-changed="handleSortChange"
          />
          <div class="text-sm">
            <span
              :class="{ 'bloom-pulse': showResultsPulse }"
              class="inline-block transition-all"
            >
              {{ filteredGames.length }} games found
            </span>
          </div>
        </div>

        <!-- Search Bar -->
        <div class="mx-4 max-w-lg flex-1">
          <div class="flex items-center gap-3">
            <div class="relative flex-1">
              <input
                type="text"
                v-model="searchQueryModel"
                placeholder="Search games..."
                class="border-border w-full rounded-lg border bg-bg-secondary px-3 py-1.5 pr-8 text-sm text-text-primary placeholder-text-secondary transition-colors focus:border-accent focus:outline-none"
              />
              <!-- Clear button -->
              <button
                v-if="searchQueryModel"
                type="button"
                @click="searchQueryModel = ''"
                class="absolute top-1/2 right-1 -translate-y-1/2 rounded-sm p-1 text-text-secondary transition-all hover:bg-bg-secondary hover:text-text-primary"
                title="Clear search"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="size-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
            <!-- Search scope toggle -->
            <div class="flex rounded-lg bg-bg-secondary p-0.5">
              <button
                @click="searchInVideoTitlesModel = false"
                class="rounded-md px-2 py-1 text-xs font-medium transition-all"
                :class="
                  !searchInVideoTitlesModel
                    ? 'bg-bg-primary text-text-primary shadow-sm'
                    : 'text-text-secondary hover:text-text-primary'
                "
                type="button"
                title="Search in game names only"
              >
                🎮 Games
              </button>
              <button
                @click="searchInVideoTitlesModel = true"
                class="rounded-md px-2 py-1 text-xs font-medium transition-all"
                :class="
                  searchInVideoTitlesModel
                    ? 'bg-bg-primary text-text-primary shadow-sm'
                    : 'text-text-secondary hover:text-text-primary'
                "
                type="button"
                title="Search in both game names and video titles"
              >
                🎮+🎬 All
              </button>
            </div>
          </div>
        </div>

        <!-- Share Button -->
        <div class="flex items-center gap-2">
          <button
            @click="handleCopyCurrentFiltersLink"
            class="flex items-center gap-1.5 rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-accent-hover active:bg-accent-active"
            title="Copy shareable link with current filters"
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
                d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z"
              />
            </svg>
            <span>Share</span>
          </button>
        </div>
      </div>

      <!-- Mobile layout -->
      <div class="md:hidden">
        <!-- Sort Indicator -->
        <div class="mb-3 flex items-center justify-between">
          <SortIndicator
            :sort-by="sortBy"
            :sort-spec="sortSpec"
            :game-count="filteredGames.length"
            @sort-changed="handleSortChange"
          />
        </div>

        <!-- Search Bar -->
        <div class="flex items-center gap-2">
          <div class="relative flex-1">
            <input
              type="text"
              v-model="searchQueryModel"
              placeholder="Search games..."
              class="border-border w-full rounded-lg border bg-bg-secondary px-3 py-1.5 pr-8 text-sm text-text-primary placeholder-text-secondary transition-colors focus:border-accent focus:outline-none"
            />
            <!-- Clear button -->
            <button
              v-if="searchQueryModel"
              type="button"
              @click="searchQueryModel = ''"
              class="absolute top-1/2 right-1 -translate-y-1/2 rounded-sm p-1 text-text-secondary transition-all hover:bg-bg-secondary hover:text-text-primary"
              title="Clear search"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class="size-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
          <!-- Search scope toggle (compact for mobile) -->
          <div class="flex rounded-lg bg-bg-secondary p-0.5">
            <button
              @click="searchInVideoTitlesModel = false"
              class="rounded-md px-1.5 py-1 text-xs font-medium transition-all"
              :class="
                !searchInVideoTitlesModel
                  ? 'bg-bg-primary text-text-primary shadow-sm'
                  : 'text-text-secondary'
              "
              type="button"
              title="Search games only"
            >
              🎮
            </button>
            <button
              @click="searchInVideoTitlesModel = true"
              class="rounded-md px-1.5 py-1 text-xs font-medium transition-all"
              :class="
                searchInVideoTitlesModel
                  ? 'bg-bg-primary text-text-primary shadow-sm'
                  : 'text-text-secondary'
              "
              type="button"
              title="Search games and video titles"
            >
              🎮+🎬
            </button>
          </div>
        </div>

        <!-- Search results count -->
        <div
          v-if="searchState.query"
          class="mt-2 text-center text-xs text-text-secondary"
        >
          {{ filteredGames.length }} results
          <span v-if="searchState.searchInVideoTitles">(games & videos)</span>
          <span v-else>(games only)</span>
        </div>
      </div>
    </div>

    <!-- Mode Change Message (absolute positioned) -->
    <Transition name="fade">
      <div
        v-if="showModeChangeMessage"
        class="absolute -top-14 left-1/2 z-20 -translate-x-1/2 rounded-full bg-accent/20 px-4 py-2 text-sm font-medium text-accent backdrop-blur-sm"
      >
        {{
          searchInVideoTitlesModel
            ? '🎬 Now searching in both game names and video titles'
            : '🎮 Now searching in game names only'
        }}
      </div>
    </Transition>

    <!-- Modern Game Grid with Pagination -->
    <div class="game-discovery-content min-h-0 w-full flex-1">
      <!-- Game Grid -->
      <div
        ref="gameGrid"
        v-if="filteredGames.length > 0"
        class="game-grid mb-8 grid w-full justify-start gap-5"
        style="grid-template-columns: repeat(auto-fit, minmax(320px, 400px))"
      >
        <GameCard
          v-for="game in currentPageGames"
          :key="game.id"
          :game="game"
          :currency="currency"
          :is-highlighted="highlightedGameId === String(game.id)"
          :selected-tags="selectedTags"
          :load-game-videos="loadGameVideos"
          @click="handleClearHighlight"
          @tag-click="handleTagClick"
        />
      </div>

      <!-- Pagination Controls -->
      <PaginationControls
        v-if="filteredGames.length > 0"
        :current-page="currentPage"
        :total-pages="totalPages"
        :total-items="filteredGames.length"
        :start-index="startIndex"
        :end-index="endIndex"
        :remaining-items="remainingItems"
        :page-size="pageSize"
        :has-next-page="hasNextPage"
        :has-prev-page="hasPrevPage"
        :loading="paginationLoading"
        :visible-pages="visiblePages"
        :show-first-page="showFirstPage"
        :show-last-page="showLastPage"
        :show-left-ellipsis="showLeftEllipsis"
        :show-right-ellipsis="showRightEllipsis"
        :load-more-visible="loadMoreVisible"
        :get-page-button-class="getPageButtonClass"
        :get-nav-button-class="getNavButtonClass"
        @go-to-page="handleGoToPage"
        @load-more="handleLoadMore"
        @jump-to-page="handleJumpToPageInternal"
        @set-page-size="handleSetPageSize"
      />
    </div>

    <!-- Loading/Error States -->
    <div v-if="loading" class="py-10 text-center text-text-secondary">
      Loading games...
    </div>

    <div v-if="error" class="py-10 text-center text-red-500">
      Error loading games: {{ error }}
    </div>

    <!-- No Results State -->
    <div
      v-if="!loading && !error && filteredGames.length === 0"
      class="py-20 text-center text-text-secondary"
    >
      <div class="mb-2 text-xl">No games found</div>
      <div class="text-sm">Try adjusting your filters to see more results.</div>
    </div>
  </div>
</template>

<style scoped>
/* Modern game grid styles - return to master's proven approach */
.game-grid {
  /* Ensure proper grid container behavior */
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1.25rem; /* 20px - matches gap-5 */
  width: 100%;
  min-width: 0;
}

/* Grid items inherit proper sizing from GameCard component */

/* Game discovery container */
.game-discovery-container {
  /* Clean container for the entire discovery interface */
  display: flex;
  flex-direction: column;
  width: 100%;
  min-height: 0;
}

/* Game discovery content area */
.game-discovery-content {
  /* Clean container for pagination layout */
  display: flex;
  flex-direction: column;
  width: 100%;
  min-height: 0;
}

/* Responsive behavior for dynamic grid columns */
@media (max-width: 359px) {
  /* Extra small mobile: force smaller minimum */
  .game-grid {
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)) !important;
  }
}

@media (min-width: 360px) {
  /* Standard responsive grid with 320px minimum */
  .game-grid {
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)) !important;
  }
}

/* Fade transition for mode change message */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Bloom pulse animation for results count */
@keyframes bloomPulse {
  0% {
    transform: scale(1);
    filter: brightness(1) drop-shadow(0 0 0 rgba(139, 92, 246, 0));
    color: inherit;
  }
  50% {
    transform: scale(1.1);
    filter: brightness(1.5) drop-shadow(0 0 30px rgba(139, 92, 246, 1))
      drop-shadow(0 0 60px rgba(139, 92, 246, 0.6));
    color: #a78bfa;
  }
  100% {
    transform: scale(1);
    filter: brightness(1) drop-shadow(0 0 0 rgba(139, 92, 246, 0));
    color: inherit;
  }
}

.bloom-pulse {
  animation: bloomPulse 0.8s ease-out;
  transform-origin: center;
}
</style>
