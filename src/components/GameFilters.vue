<script setup lang="ts">
import {
  reactive,
  computed,
  ref,
  onUnmounted,
  nextTick,
  watch,
  type Ref,
} from 'vue'
import { useDebouncedFilters } from '../composables/useDebouncedFilters'
import { TIMING } from '../config/index'
import type { FilterConfig } from '../utils/presetManager'
import type {
  ChannelWithCount,
  TagWithCount,
  DatabaseStats,
} from '../types/database'
import type { FilterRemoveEvent } from '../types/filters'
import type { SortChangeEvent } from '../types/sorting'
import CollapsibleSection from './CollapsibleSection.vue'
import TagFilterMulti from './TagFilterMulti.vue'
import ChannelFilterMulti from './ChannelFilterMulti.vue'
import TimeFilterSimple from './TimeFilterSimple.vue'
import PriceFilter from './PriceFilter.vue'
import SortingOptions from './SortingOptions.vue'
import MobileFilterModal from './MobileFilterModal.vue'
import AppliedFiltersBar from './AppliedFiltersBar.vue'
import FilterPresets from './FilterPresets.vue'

// Component props interface
interface Props {
  channels?: string[]
  channelsWithCounts?: ChannelWithCount[]
  tags?: TagWithCount[]
  initialFilters?: Partial<FilterConfig>
  gameCount?: number
  gameStats?: DatabaseStats
}

// Component events interface
interface Emits {
  filtersChanged: [filters: FilterConfig]
}

// Define props with defaults
const props = withDefaults(defineProps<Props>(), {
  channels: () => [],
  channelsWithCounts: () => [],
  tags: () => [],
  initialFilters: () => ({}),
  gameCount: 0,
  gameStats: () => ({
    totalGames: 0,
    freeGames: 0,
    maxPrice: 70,
  }),
})

// Define emits
const emit = defineEmits<Emits>()

// Interfaces for filter data
interface TagChangedData {
  selectedTags: string[]
  tagLogic: 'and' | 'or'
}

interface ChannelChangedData {
  selectedChannels: string[]
}

interface TimeFilterData {
  type: string | null
  preset: string | null
  startDate: string | null
  endDate: string | null
  smartLogic: string | null
}

interface PriceFilterData {
  minPrice: number
  maxPrice: number
  includeFree: boolean
}

// Using shared types from ../types/sorting and ../types/filters
// SortChangeEvent and FilterRemoveEvent are imported above

// Reactive state
const showMobileModal: Ref<boolean> = ref(false)

// Initialize local filters with proper defaults
const initialLocalFilters: FilterConfig = {
  releaseStatus: props.initialFilters.releaseStatus || 'all',
  platform: props.initialFilters.platform || 'all',
  rating: props.initialFilters.rating || '0',
  crossPlatform: props.initialFilters.crossPlatform || false,
  hiddenGems: props.initialFilters.hiddenGems || false,
  // Legacy single tag support for backward compatibility
  tag: props.initialFilters.tag || '',
  // New multi-tag support
  selectedTags:
    props.initialFilters.selectedTags ||
    (props.initialFilters.tag ? [props.initialFilters.tag] : []),
  tagLogic: (props.initialFilters.tagLogic as 'and' | 'or') || 'and',
  // Legacy single channel support for backward compatibility
  channel: props.initialFilters.channel || '',
  // New multi-channel support
  selectedChannels:
    props.initialFilters.selectedChannels ||
    (props.initialFilters.channel ? [props.initialFilters.channel] : []),
  sortBy: props.initialFilters.sortBy || 'date',
  sortSpec: props.initialFilters.sortSpec || null,
  currency: (props.initialFilters.currency as 'eur' | 'usd') || 'eur',
  // Time-based filtering
  timeFilter: props.initialFilters.timeFilter || {
    type: null,
    preset: null,
    startDate: null,
    endDate: null,
    smartLogic: null,
  },
  priceFilter: props.initialFilters.priceFilter || {
    minPrice: 0,
    maxPrice: 70,
    includeFree: true,
  },
}

const localFilters = reactive<FilterConfig>({ ...initialLocalFilters })

// Watch for changes in initial filters (e.g., from URL loading)
watch(
  () => props.initialFilters,
  (newInitialFilters: Partial<FilterConfig> | undefined) => {
    if (newInitialFilters && Object.keys(newInitialFilters).length > 0) {
      Object.assign(localFilters, {
        releaseStatus: newInitialFilters.releaseStatus || 'all',
        platform: newInitialFilters.platform || 'all',
        rating: newInitialFilters.rating || '0',
        crossPlatform: newInitialFilters.crossPlatform || false,
        hiddenGems: newInitialFilters.hiddenGems || false,
        tag: newInitialFilters.tag || '',
        selectedTags:
          newInitialFilters.selectedTags ||
          (newInitialFilters.tag ? [newInitialFilters.tag] : []),
        tagLogic: (newInitialFilters.tagLogic as 'and' | 'or') || 'and',
        channel: newInitialFilters.channel || '',
        selectedChannels:
          newInitialFilters.selectedChannels ||
          (newInitialFilters.channel ? [newInitialFilters.channel] : []),
        sortBy: newInitialFilters.sortBy || 'date',
        sortSpec: newInitialFilters.sortSpec || null,
        currency: (newInitialFilters.currency as 'eur' | 'usd') || 'eur',
        timeFilter: newInitialFilters.timeFilter || {
          type: null,
          preset: null,
          startDate: null,
          endDate: null,
          smartLogic: null,
        },
        priceFilter: newInitialFilters.priceFilter || {
          minPrice: 0,
          maxPrice: 70,
          includeFree: true,
        },
      })
    }
  },
  { deep: true, immediate: false },
)

// Set up debounced filter updates
const { debouncedEmit, immediateEmit, cleanup } =
  useDebouncedFilters<FilterConfig>(
    initialLocalFilters,
    (newFilters: FilterConfig) => emit('filtersChanged', newFilters),
    TIMING.FILTER_DEBOUNCE_DELAY, // Configurable debounce delay
  )

const activeFilterCount = computed((): number => {
  let count = 0
  if (localFilters.releaseStatus !== 'all') {
    count++
  }
  if (localFilters.platform !== 'all') {
    count++
  }
  if (localFilters.rating !== '0') {
    count++
  }
  if (localFilters.crossPlatform) {
    count++
  }
  if (localFilters.hiddenGems) {
    count++
  }
  if (localFilters.selectedTags.length > 0) {
    count++
  }
  if (localFilters.selectedChannels.length > 0) {
    count++
  }
  if (localFilters.sortBy !== 'date' || localFilters.sortSpec) {
    count++
  }
  if (localFilters.currency !== 'eur') {
    count++
  }
  if (localFilters.timeFilter.type) {
    count++
  }
  if (
    localFilters.priceFilter &&
    (localFilters.priceFilter.minPrice > 0 ||
      localFilters.priceFilter.maxPrice < 70 ||
      !localFilters.priceFilter.includeFree)
  ) {
    count++
  }
  return count
})

// Section-specific active filter counts for badges
const basicFiltersCount = computed((): number => {
  let count = 0
  if (localFilters.releaseStatus !== 'all') {
    count++
  }
  if (localFilters.platform !== 'all') {
    count++
  }
  if (localFilters.crossPlatform) {
    count++
  }
  if (localFilters.hiddenGems) {
    count++
  }
  return count
})

const ratingFiltersCount = computed((): number =>
  localFilters.rating !== '0' ? 1 : 0,
)

const tagsCount = computed((): number =>
  localFilters.selectedTags.length > 0 ? localFilters.selectedTags.length : 0,
)

const channelsCount = computed((): number =>
  localFilters.selectedChannels.length > 0
    ? localFilters.selectedChannels.length
    : 0,
)

const sortingCount = computed((): number =>
  localFilters.sortBy !== 'date' || localFilters.sortSpec ? 1 : 0,
)

const timeFilterCount = computed((): number =>
  localFilters.timeFilter && localFilters.timeFilter.type ? 1 : 0,
)

const priceFilterCount = computed((): number =>
  localFilters.priceFilter &&
  (localFilters.priceFilter.minPrice > 0 ||
    localFilters.priceFilter.maxPrice < 70 ||
    !localFilters.priceFilter.includeFree)
    ? 1
    : 0,
)

const currencyCount = computed((): number =>
  localFilters.currency !== 'eur' ? 1 : 0,
)

const handleTagsChanged = (tagData: TagChangedData): void => {
  localFilters.selectedTags = tagData.selectedTags
  localFilters.tagLogic = tagData.tagLogic
  debouncedEmitFiltersChanged()
}

const handleChannelsChanged = (channelData: ChannelChangedData): void => {
  localFilters.selectedChannels = channelData.selectedChannels
  debouncedEmitFiltersChanged()
}

const handleTimeFilterChanged = (timeFilterData: TimeFilterData): void => {
  localFilters.timeFilter = { ...timeFilterData }
  debouncedEmitFiltersChanged()
}

const handlePriceFilterChanged = (priceFilterData: PriceFilterData): void => {
  localFilters.priceFilter = { ...priceFilterData }
  debouncedEmitFiltersChanged()
}

const handleSortChanged = (event: SortChangeEvent): void => {
  localFilters.sortBy = event.sortBy
  localFilters.sortSpec = event.sortSpec
  // Sort changes should be immediate for better UX
  immediateEmitFiltersChanged()
}

const handleFiltersChanged = (newFilters: Partial<FilterConfig>): void => {
  Object.assign(localFilters, newFilters)
  debouncedEmitFiltersChanged()
}

// Helper to preserve scroll position when filters change
const preserveScrollPosition = (callback: () => void): void => {
  // Find the sidebar scroll container
  const scrollContainer = document.querySelector('.sidebar-scroll')
  if (!scrollContainer) {
    callback()
    return
  }

  // Save current scroll position
  const { scrollTop } = scrollContainer

  // Execute the callback
  callback()

  // Restore scroll position after DOM update
  nextTick(() => {
    scrollContainer.scrollTop = scrollTop
  })
}

const handleRemoveFilter = (event: FilterRemoveEvent): void => {
  preserveScrollPosition(() => {
    switch (event.type) {
      case 'releaseStatus':
        localFilters.releaseStatus = event.value as string
        break
      case 'platform':
        localFilters.platform = event.value as string
        break
      case 'rating':
        localFilters.rating = event.value as string
        break
      case 'crossPlatform':
        localFilters.crossPlatform = event.value as boolean
        break
      case 'hiddenGems':
        localFilters.hiddenGems = event.value as boolean
        break
      case 'tags':
        localFilters.selectedTags = event.value as string[]
        break
      case 'channels':
        localFilters.selectedChannels = event.value as string[]
        break
      case 'sortBy':
        localFilters.sortBy = event.value as string
        localFilters.sortSpec = null
        break
      case 'currency':
        localFilters.currency = event.value as 'eur' | 'usd'
        break
      case 'timeFilter':
        localFilters.timeFilter = event.value as unknown as {
          type: string
          preset: string
          startDate: string
          endDate: string
          smartLogic: string
        }
        break
      case 'priceFilter':
        localFilters.priceFilter = event.value as unknown as {
          minPrice: number
          maxPrice: number
          includeFree: boolean
        }
        break
    }
    // Remove operations should be immediate
    immediateEmitFiltersChanged()
  })
}

const handleClearAllFilters = (): void => {
  preserveScrollPosition(() => {
    localFilters.releaseStatus = 'all'
    localFilters.platform = 'all'
    localFilters.rating = '0'
    localFilters.crossPlatform = false
    localFilters.hiddenGems = false
    localFilters.selectedTags = []
    localFilters.tagLogic = 'and'
    localFilters.selectedChannels = []
    localFilters.sortBy = 'date'
    localFilters.sortSpec = null
    localFilters.currency = 'eur'
    localFilters.timeFilter = {
      type: null,
      preset: null,
      startDate: null,
      endDate: null,
      smartLogic: null,
    }
    localFilters.priceFilter = {
      minPrice: 0,
      maxPrice: 70,
      includeFree: true,
    }
    // Clear all should be immediate
    immediateEmitFiltersChanged()
  })
}

const handleApplyPreset = (presetFilters: FilterConfig): void => {
  Object.assign(localFilters, presetFilters)
  // Preset changes should be immediate
  immediateEmitFiltersChanged()
}

// Debounced emit for gradual filter changes
const debouncedEmitFiltersChanged = (): void => {
  debouncedEmit({ ...localFilters })
}

// Immediate emit for important changes
const immediateEmitFiltersChanged = (): void => {
  immediateEmit({ ...localFilters })
}

// Cleanup on unmount
onUnmounted(() => {
  cleanup()
})
</script>

<template>
  <!-- Applied Filters Bar (Mobile only - desktop version is rendered below) -->
  <div class="md:hidden">
    <AppliedFiltersBar
      :filters="localFilters"
      @remove-filter="handleRemoveFilter"
      @clear-all-filters="handleClearAllFilters"
    />
  </div>

  <!-- Mobile Filter Interface -->
  <div class="md:hidden">
    <!-- Mobile Filter Button -->
    <div class="mb-4 flex items-center justify-between">
      <button
        @click="showMobileModal = true"
        class="flex items-center gap-2 rounded-lg bg-accent px-4 py-3 font-medium text-white transition-colors hover:bg-accent-hover active:bg-accent-active"
      >
        <svg
          class="size-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
          ></path>
        </svg>
        <span>Filters</span>
        <span
          v-if="activeFilterCount > 0"
          class="rounded-full bg-white/20 px-2 py-0.5 text-xs"
        >
          {{ activeFilterCount }}
        </span>
      </button>

      <!-- Game count for mobile -->
      <span class="text-sm text-text-secondary"> {{ gameCount }} games </span>
    </div>

    <!-- Mobile Filter Modal -->
    <MobileFilterModal
      :is-open="showMobileModal"
      :channels="channels"
      :channels-with-counts="channelsWithCounts"
      :tags="tags"
      :initial-filters="localFilters"
      :game-stats="gameStats"
      @close="showMobileModal = false"
      @filters-changed="handleFiltersChanged"
    />
  </div>

  <!-- Desktop Filter Interface -->
  <div class="hidden space-y-4 md:block">
    <!-- Applied Filters Summary -->
    <AppliedFiltersBar
      :filters="localFilters"
      :game-count="gameCount"
      @remove-filter="handleRemoveFilter"
      @clear-all-filters="handleClearAllFilters"
    />

    <!-- Basic Filters Section -->
    <CollapsibleSection
      title="Basic Filters"
      :active-count="basicFiltersCount"
      :default-expanded="true"
    >
      <div class="space-y-4">
        <!-- Release Status Filter -->
        <div>
          <label class="mb-1 block text-sm text-text-secondary"
            >Release Status:</label
          >
          <select
            v-model="localFilters.releaseStatus"
            class="w-full cursor-pointer rounded-sm border border-gray-600 bg-bg-primary px-3 py-2 text-text-primary hover:border-accent focus:border-accent focus:outline-none"
            @change="debouncedEmitFiltersChanged"
          >
            <option value="all">All Games</option>
            <option value="released">Released Only</option>
            <option value="early-access">Early Access</option>
            <option value="coming-soon">Coming Soon</option>
          </select>
        </div>

        <!-- Platform Filter -->
        <div>
          <label class="mb-1 block text-sm text-text-secondary"
            >Platform:</label
          >
          <select
            v-model="localFilters.platform"
            class="w-full cursor-pointer rounded-sm border border-gray-600 bg-bg-primary px-3 py-2 text-text-primary hover:border-accent focus:border-accent focus:outline-none"
            @change="debouncedEmitFiltersChanged"
          >
            <option value="all">All Platforms</option>
            <option value="steam">Steam</option>
            <option value="itch">Itch.io</option>
            <option value="crazygames">CrazyGames</option>
          </select>
        </div>

        <!-- Cross-Platform & Hidden Gems Checkboxes -->
        <div class="space-y-3">
          <div class="flex items-center gap-2">
            <input
              id="crossPlatform"
              v-model="localFilters.crossPlatform"
              type="checkbox"
              class="size-4 cursor-pointer rounded-sm border-gray-600 text-accent focus:ring-accent focus:ring-offset-0"
              @change="debouncedEmitFiltersChanged"
            />
            <label
              for="crossPlatform"
              class="cursor-pointer text-sm text-text-primary"
            >
              Multi-platform only
            </label>
          </div>

          <div class="flex items-center gap-2">
            <input
              id="hiddenGems"
              v-model="localFilters.hiddenGems"
              type="checkbox"
              class="size-4 cursor-pointer rounded-sm border-gray-600 text-accent focus:ring-accent focus:ring-offset-0"
              @change="debouncedEmitFiltersChanged"
            />
            <label
              for="hiddenGems"
              class="cursor-pointer text-sm text-text-primary"
              title="High quality games (80%+ rating) with limited video coverage (1-3 videos) and sufficient reviews (50+)"
            >
              Hidden Gems
            </label>
          </div>
        </div>
      </div>
    </CollapsibleSection>

    <!-- Rating Section -->
    <CollapsibleSection
      title="Rating"
      :active-count="ratingFiltersCount"
      :default-expanded="false"
    >
      <div>
        <label class="mb-1 block text-sm text-text-secondary"
          >Minimum Rating:</label
        >
        <select
          v-model="localFilters.rating"
          class="w-full cursor-pointer rounded-sm border border-gray-600 bg-bg-primary px-3 py-2 text-text-primary hover:border-accent focus:border-accent focus:outline-none"
          @change="debouncedEmitFiltersChanged"
        >
          <option value="0">All Ratings</option>
          <option value="70">70%+ Positive</option>
          <option value="80">80%+ Positive</option>
          <option value="90">90%+ Positive</option>
        </select>
      </div>
    </CollapsibleSection>

    <!-- Tag Filter Section -->
    <CollapsibleSection
      title="Tags"
      :active-count="tagsCount"
      :default-expanded="false"
    >
      <TagFilterMulti
        :tags-with-counts="tags"
        :initial-selected-tags="localFilters.selectedTags || []"
        :initial-tag-logic="localFilters.tagLogic || 'and'"
        @tags-changed="handleTagsChanged"
      />
    </CollapsibleSection>

    <!-- Channel Filter Section -->
    <CollapsibleSection
      title="Channels"
      :active-count="channelsCount"
      :default-expanded="false"
    >
      <ChannelFilterMulti
        :channels-with-counts="channelsWithCounts"
        :initial-selected-channels="localFilters.selectedChannels || []"
        @channels-changed="handleChannelsChanged"
      />
    </CollapsibleSection>

    <!-- Time Filter Section -->
    <CollapsibleSection
      title="Time Filter"
      :active-count="timeFilterCount"
      :default-expanded="false"
    >
      <TimeFilterSimple
        :initial-time-filter="
          localFilters.timeFilter ||
          ({
            type: null,
            preset: null,
            startDate: null,
            endDate: null,
            smartLogic: null,
          } as any)
        "
        @time-filter-changed="handleTimeFilterChanged"
      />
    </CollapsibleSection>

    <!-- Price Filter Section -->
    <CollapsibleSection
      title="Price Filter"
      :active-count="priceFilterCount"
      :default-expanded="false"
    >
      <PriceFilter
        :currency="localFilters.currency"
        :initial-price-filter="
          localFilters.priceFilter || {
            minPrice: 0,
            maxPrice: 1000,
            includeFree: true,
          }
        "
        :game-stats="gameStats"
        @price-filter-changed="handlePriceFilterChanged"
      />
    </CollapsibleSection>

    <!-- Sorting Section -->
    <CollapsibleSection
      title="Sort By"
      :active-count="sortingCount"
      :default-expanded="false"
    >
      <SortingOptions
        :initial-sort="localFilters.sortBy"
        :contextual-filters="localFilters"
        @sort-changed="handleSortChanged"
      />
    </CollapsibleSection>

    <!-- Settings Section -->
    <CollapsibleSection
      title="Settings"
      :active-count="currencyCount"
      :default-expanded="false"
    >
      <div>
        <label class="mb-1 block text-sm text-text-secondary">Currency:</label>
        <select
          v-model="localFilters.currency"
          class="w-full cursor-pointer rounded-sm border border-gray-600 bg-bg-primary px-3 py-2 text-text-primary hover:border-accent focus:border-accent focus:outline-none"
          @change="debouncedEmitFiltersChanged"
        >
          <option value="eur">EUR (€)</option>
          <option value="usd">USD ($)</option>
        </select>
      </div>
    </CollapsibleSection>

    <!-- Filter Presets Section -->
    <CollapsibleSection
      title="Filter Presets"
      :active-count="0"
      :default-expanded="false"
    >
      <FilterPresets
        :current-filters="localFilters"
        @apply-preset="handleApplyPreset"
      />
    </CollapsibleSection>

    <!-- Sidebar Footer -->
    <div class="border-t border-gray-600 pt-4">
      <div class="flex gap-2">
        <button
          @click="handleClearAllFilters"
          class="flex-1 rounded-sm border border-gray-500 py-2 text-sm font-medium text-text-secondary transition-colors hover:border-accent hover:text-accent"
          :disabled="activeFilterCount === 0"
        >
          Reset All
        </button>
        <button
          class="flex-1 rounded-sm bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hover"
          title="Export current filter results (feature coming soon)"
        >
          Export
        </button>
      </div>
    </div>
  </div>
</template>
