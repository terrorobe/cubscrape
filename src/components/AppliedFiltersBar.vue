<template>
  <div v-if="appliedFilters.length > 0" class="mb-4">
    <!-- Mobile: Horizontal scrollable bar -->
    <div class="flex items-center gap-3 md:hidden">
      <span class="shrink-0 text-sm font-medium text-text-secondary">
        Filters:
      </span>
      <div class="scrollbar-thin flex gap-2 overflow-x-auto pb-2">
        <button
          v-for="filter in appliedFilters"
          :key="filter.key"
          @click="removeFilter(filter)"
          class="flex shrink-0 items-center gap-2 rounded-full bg-accent px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-accent-hover active:bg-accent-active"
        >
          <span>{{ filter.label }}</span>
          <svg
            class="size-3"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            ></path>
          </svg>
        </button>

        <!-- Clear all button -->
        <button
          v-if="appliedFilters.length > 1"
          @click="clearAllFilters"
          class="shrink-0 rounded-full border border-gray-500 px-3 py-1.5 text-sm font-medium text-text-secondary transition-colors hover:border-accent hover:text-accent"
        >
          Clear All
        </button>
      </div>
    </div>

    <!-- Desktop: Card-style sidebar display -->
    <div class="hidden md:block">
      <div
        class="rounded-lg border border-gray-600 bg-bg-card p-4 transition-all duration-300 ease-in-out"
      >
        <div class="mb-3 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-text-primary">
            Active Filters
          </h3>
          <span
            class="flex size-6 items-center justify-center rounded-full bg-accent text-xs font-medium text-white"
          >
            {{ appliedFilters.length }}
          </span>
        </div>

        <!-- Results Count Preview -->
        <div
          v-if="gameCount !== undefined"
          class="mb-3 text-sm text-text-secondary"
        >
          {{ gameCount }} games found
        </div>

        <div
          v-if="appliedFilters.length > 0"
          class="space-y-2 transition-all duration-300"
        >
          <button
            v-for="filter in appliedFilters"
            :key="filter.key"
            @click="removeFilter(filter)"
            class="flex w-full items-center justify-between rounded-sm bg-accent/10 px-3 py-2 text-sm transition-colors hover:bg-accent/20"
          >
            <span class="truncate text-text-primary">{{ filter.label }}</span>
            <svg
              class="size-4 shrink-0 text-text-secondary hover:text-accent"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              ></path>
            </svg>
          </button>

          <!-- Clear all button -->
          <button
            @click="clearAllFilters"
            class="mt-2 w-full rounded-sm border border-gray-500 py-2 text-sm font-medium text-text-secondary transition-colors hover:border-accent hover:text-accent"
          >
            Clear All Filters
          </button>
        </div>

        <div v-else class="text-sm text-text-secondary">No active filters</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { FilterConfig } from '../utils/presetManager'

/**
 * Applied filter item interface
 */
export interface AppliedFilter {
  key: string
  type: string
  label: string
  value: any
}

/**
 * Filter remove event payload
 */
export interface FilterRemoveEvent {
  type: string
  value: any
}

/**
 * Props interface for AppliedFiltersBar component
 */
export interface AppliedFiltersBarProps {
  filters: FilterConfig
  gameCount?: number
}

const props = withDefaults(defineProps<AppliedFiltersBarProps>(), {
  gameCount: undefined,
})

const emit = defineEmits<{
  'remove-filter': [event: FilterRemoveEvent]
  'clear-all-filters': []
}>()
const appliedFilters = computed((): AppliedFilter[] => {
  const filters: AppliedFilter[] = []

  // Release Status
  if (props.filters.releaseStatus && props.filters.releaseStatus !== 'all') {
    const statusLabels: Record<string, string> = {
      released: 'Released Only',
      'early-access': 'Early Access',
      'coming-soon': 'Coming Soon',
    }
    filters.push({
      key: 'releaseStatus',
      type: 'releaseStatus',
      label:
        statusLabels[props.filters.releaseStatus] ||
        props.filters.releaseStatus,
      value: 'all',
    })
  }

  // Platform
  if (props.filters.platform && props.filters.platform !== 'all') {
    const platformLabels: Record<string, string> = {
      steam: 'Steam',
      itch: 'Itch.io',
      crazygames: 'CrazyGames',
    }
    filters.push({
      key: 'platform',
      type: 'platform',
      label: platformLabels[props.filters.platform] || props.filters.platform,
      value: 'all',
    })
  }

  // Rating
  if (props.filters.rating && props.filters.rating !== '0') {
    filters.push({
      key: 'rating',
      type: 'rating',
      label: `${props.filters.rating}%+ Rating`,
      value: '0',
    })
  }

  // Cross-Platform
  if (props.filters.crossPlatform) {
    filters.push({
      key: 'crossPlatform',
      type: 'crossPlatform',
      label: 'Multi-platform only',
      value: false,
    })
  }

  // Hidden Gems
  if (props.filters.hiddenGems) {
    filters.push({
      key: 'hiddenGems',
      type: 'hiddenGems',
      label: 'Hidden Gems',
      value: false,
    })
  }

  // Tags
  if (props.filters.selectedTags && props.filters.selectedTags.length > 0) {
    if (props.filters.selectedTags.length === 1) {
      filters.push({
        key: 'tags',
        type: 'tags',
        label: props.filters.selectedTags[0],
        value: [],
      })
    } else {
      const logic = props.filters.tagLogic === 'or' ? 'any' : 'all'
      filters.push({
        key: 'tags',
        type: 'tags',
        label: `${props.filters.selectedTags.length} tags (${logic})`,
        value: [],
      })
    }
  }

  // Channels
  if (
    props.filters.selectedChannels &&
    props.filters.selectedChannels.length > 0
  ) {
    if (props.filters.selectedChannels.length === 1) {
      const channelName = formatChannelName(props.filters.selectedChannels[0])
      filters.push({
        key: 'channels',
        type: 'channels',
        label: channelName,
        value: [],
      })
    } else {
      filters.push({
        key: 'channels',
        type: 'channels',
        label: `${props.filters.selectedChannels.length} channels`,
        value: [],
      })
    }
  }

  // Sort
  if (props.filters.sortBy && props.filters.sortBy !== 'date') {
    const sortLabels = {
      'rating-score': 'Rating Score',
      'rating-category': 'Rating Category',
      name: 'Game Name',
      'release-new': 'Release: Newest',
      'release-old': 'Release: Oldest',
    }
    filters.push({
      key: 'sortBy',
      type: 'sortBy',
      label: `Sort: ${sortLabels[props.filters.sortBy] || props.filters.sortBy}`,
      value: 'date',
    })
  }

  // Currency
  if (props.filters.currency && props.filters.currency !== 'eur') {
    const currencyLabels = {
      usd: 'USD ($)',
    }
    filters.push({
      key: 'currency',
      type: 'currency',
      label: currencyLabels[props.filters.currency] || props.filters.currency,
      value: 'eur',
    })
  }

  // Time Filter
  if (props.filters.timeFilter && props.filters.timeFilter.type) {
    let label = 'Time Filter'

    if (props.filters.timeFilter.type === 'smart') {
      const smartLabels = {
        'release-and-video-recent': 'Recently Released',
        'first-video-recent': 'Newly Discovered',
        'multiple-videos-recent': 'Trending',
        'old-game-new-attention': 'Rediscovered',
      }
      label = smartLabels[props.filters.timeFilter.smartLogic] || 'Smart Filter'
    } else if (props.filters.timeFilter.type === 'video') {
      label = 'Video Date Filter'
    } else if (props.filters.timeFilter.type === 'release') {
      label = 'Release Date Filter'
    }

    filters.push({
      key: 'timeFilter',
      type: 'timeFilter',
      label: label,
      value: {
        type: null,
        preset: null,
        startDate: null,
        endDate: null,
        smartLogic: null,
      },
    })
  }

  // Price Filter
  if (
    props.filters.priceFilter &&
    (props.filters.priceFilter.minPrice > 0 ||
      props.filters.priceFilter.maxPrice < 70 ||
      !props.filters.priceFilter.includeFree)
  ) {
    let label = 'Price Filter'
    const currency = props.filters.currency === 'usd' ? '$' : '€'

    // Create a descriptive label based on the filter settings
    if (!props.filters.priceFilter.includeFree) {
      if (
        props.filters.priceFilter.minPrice > 0 ||
        props.filters.priceFilter.maxPrice < 70
      ) {
        label = `${currency}${props.filters.priceFilter.minPrice}-${props.filters.priceFilter.maxPrice} (no free)`
      } else {
        label = 'Paid games only'
      }
    } else if (
      props.filters.priceFilter.minPrice === 0 &&
      props.filters.priceFilter.maxPrice === 0
    ) {
      label = 'Free games only'
    } else if (
      props.filters.priceFilter.minPrice > 0 ||
      props.filters.priceFilter.maxPrice < 70
    ) {
      label = `${currency}${props.filters.priceFilter.minPrice}-${props.filters.priceFilter.maxPrice}`
    }

    filters.push({
      key: 'priceFilter',
      type: 'priceFilter',
      label: label,
      value: { minPrice: 0, maxPrice: 70, includeFree: true },
    })
  }

  return filters
})

const formatChannelName = (channel: string): string => {
  if (!channel || typeof channel !== 'string') {
    return 'Unknown Channel'
  }
  return channel
    .replace(/^videos-/, '')
    .replace(/-/g, ' ')
    .replace(/\b\w/g, (l) => l.toUpperCase())
}

const removeFilter = (filter: AppliedFilter): void => {
  emit('remove-filter', {
    type: filter.type,
    value: filter.value,
  })
}

const clearAllFilters = (): void => {
  emit('clear-all-filters')
}
</script>

<style scoped>
/* Custom scrollbar for mobile horizontal scroll */
.scrollbar-thin {
  scrollbar-width: thin;
  scrollbar-color: theme('colors.text.secondary') transparent;
}

.scrollbar-thin::-webkit-scrollbar {
  height: 4px;
}

.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}

.scrollbar-thin::-webkit-scrollbar-thumb {
  background-color: theme('colors.text.secondary');
  border-radius: 2px;
}

.scrollbar-thin::-webkit-scrollbar-thumb:hover {
  background-color: theme('colors.text.primary');
}

/* Ensure horizontal scroll works properly */
.overflow-x-auto {
  -webkit-overflow-scrolling: touch;
}

/* Active states for better touch feedback */
.active\:bg-accent-active:active {
  background-color: theme('colors.accent') / 0.8;
}
</style>
