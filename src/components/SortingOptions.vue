<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type {
  SortField,
  SortDirection,
  SortCriteria,
  AdvancedSortSpec,
  SortSpec,
  SortChangeEvent,
} from '../types/sorting'

/**
 * Quick preset configuration for advanced mode
 */
export interface QuickPreset {
  key: string
  name: string
  description: string
  primary: SortCriteria
  secondary: SortCriteria
}

/**
 * Contextual sort option
 */
export interface ContextualSortOption {
  value: string
  label: string
  description: string
}

// SortChangeEvent is now imported from types/sorting

/**
 * Props interface for SortingOptions component
 */
/**
 * Contextual filters interface for sorting suggestions
 */
export interface ContextualFilters {
  timeFilter?: {
    type?: string | null
    preset?: string | null
  }
  selectedChannels?: string[]
  selectedTags?: string[]
  platform?: string
  releaseStatus?: string
  rating?: string
  priceFilter?: {
    minPrice: number
    maxPrice: number
  }
}

export interface SortingOptionsProps {
  initialSort?: string
  contextualFilters?: ContextualFilters
  hideSmartPresets?: boolean
  showAdvancedToggle?: boolean
}

const props = withDefaults(defineProps<SortingOptionsProps>(), {
  initialSort: 'date',
  contextualFilters: () => ({}),
  hideSmartPresets: false,
  showAdvancedToggle: true,
})

const emit = defineEmits<{
  sortChanged: [event: SortChangeEvent]
}>()
const isAdvancedMode = ref<boolean>(false)
const currentSort = ref<string>(props.initialSort)

// Advanced sorting criteria
const primaryCriteria = ref<SortCriteria>({
  field: 'rating',
  direction: 'desc',
})

const secondaryCriteria = ref<SortCriteria>({
  field: 'coverage',
  direction: 'desc',
})

const hasSecondaryCriteria = ref<boolean>(false)

// Sort descriptions for user guidance
const sortDescriptions: Record<string, string> = {
  date: 'Games sorted by most recent video coverage',
  'rating-score': 'Games with highest Steam ratings first',
  'rating-category':
    'Games grouped by rating tiers (Overwhelmingly Positive, Very Positive, etc.)',
  name: 'Games sorted alphabetically by title',
  'release-new': 'Most recently released games first',
  'release-old': 'Oldest games first, good for discovering classics',
  'best-value':
    'High-rated games at reasonable prices - great bang for your buck',
  'hidden-gems':
    'Highly rated games with less video coverage - undiscovered treasures',
  'most-covered': 'Games covered by many channels - popular community picks',
  trending: 'Games gaining recent attention with multiple new videos',
  'creator-consensus': 'Games praised by multiple different channels',
  'recent-discoveries': 'Recently featured games that are worth checking out',
  // Contextual sorting descriptions
  'video-recency':
    'Games within your video time range, prioritizing newest coverage',
  'time-range-releases':
    'Games released in your time range, sorted by rating quality',
  'price-value': 'Best value games within your price range',
  'steam-optimized':
    'Steam games sorted by review quality and community engagement',
  'itch-discoveries': 'Indie discoveries sorted by creativity and coverage',
  'premium-quality':
    'Top-rated games with detailed reviews and recent attention',
  'tag-match':
    'Games matching your selected tags, prioritized by rating and coverage',
  'channel-picks':
    'Games featured by your selected channels, highest rated first',
}

// Quick preset combinations for advanced mode
const quickPresets: QuickPreset[] = [
  {
    key: 'value',
    name: 'Best Value',
    description: 'High rating + reasonable price',
    primary: { field: 'rating', direction: 'desc' },
    secondary: { field: 'price', direction: 'asc' },
  },
  {
    key: 'gems',
    name: 'Hidden Gems',
    description: 'High rating + low coverage',
    primary: { field: 'rating', direction: 'desc' },
    secondary: { field: 'coverage', direction: 'asc' },
  },
  {
    key: 'popular',
    name: 'Most Popular',
    description: 'High coverage + high rating',
    primary: { field: 'coverage', direction: 'desc' },
    secondary: { field: 'rating', direction: 'desc' },
  },
  {
    key: 'fresh',
    name: 'Fresh Releases',
    description: 'Recent release + recent coverage',
    primary: { field: 'release', direction: 'desc' },
    secondary: { field: 'recency', direction: 'desc' },
  },
]

const currentSortInfo = computed(
  (): string => sortDescriptions[currentSort.value] || '',
)

// Contextual sorting options based on active filters
const contextualSortOptions = computed((): ContextualSortOption[] => {
  const options: ContextualSortOption[] = []
  const filters = props.contextualFilters

  // If time filters are active, suggest time-relevant sorts
  if (filters.timeFilter && filters.timeFilter.type) {
    if (filters.timeFilter.type === 'video') {
      options.push({
        value: 'video-recency',
        label: 'Within Time Range',
        description:
          'Games within your selected video time range, newest first',
      })
    } else if (filters.timeFilter.type === 'release') {
      options.push({
        value: 'time-range-releases',
        label: 'Time Range Releases',
        description: 'Release date within your range, with rating priority',
      })
    }
  }

  // If price filters are active, suggest value-focused sorts
  if (
    filters.priceFilter &&
    (filters.priceFilter.minPrice > 0 || filters.priceFilter.maxPrice < 70)
  ) {
    options.push({
      value: 'price-value',
      label: 'Price Range Value',
      description: 'Best rated games within your price range',
    })
  }

  // If platform is specific, suggest platform-optimized sorts
  if (filters.platform && filters.platform !== 'all') {
    if (filters.platform === 'steam') {
      options.push({
        value: 'steam-optimized',
        label: 'Steam Highlights',
        description: 'Steam-specific sorting by review quality and recency',
      })
    } else if (filters.platform === 'itch') {
      options.push({
        value: 'itch-discoveries',
        label: 'Itch Discoveries',
        description: 'Creative indie games by coverage and uniqueness',
      })
    }
  }

  // If high rating filter is active, suggest rating-focused sorts
  if (filters.rating && parseInt(filters.rating) >= 80) {
    options.push({
      value: 'premium-quality',
      label: 'Premium Quality',
      description: 'Top-rated games sorted by review depth and recency',
    })
  }

  // If multiple tags are selected, suggest tag-relevance sorting
  if (filters.selectedTags && filters.selectedTags.length > 1) {
    options.push({
      value: 'tag-match',
      label: 'Tag Relevance',
      description: 'Games matching your tags, sorted by rating and coverage',
    })
  }

  // If specific channels are selected, suggest channel-focused sorting
  if (filters.selectedChannels && filters.selectedChannels.length > 0) {
    options.push({
      value: 'channel-picks',
      label: 'Channel Picks',
      description: 'Highlighted by your selected channels, best rated first',
    })
  }

  return options
})

const advancedSortInfo = computed((): string => {
  const primary = getFieldDescription(
    primaryCriteria.value.field,
    primaryCriteria.value.direction,
  )
  if (!hasSecondaryCriteria.value) {
    return `Sorting by ${primary}`
  }

  const secondary = getFieldDescription(
    secondaryCriteria.value.field,
    secondaryCriteria.value.direction,
  )
  return `Sorting by ${primary}, then by ${secondary}`
})

const getFieldDescription = (
  field: SortField,
  direction: SortDirection,
): string => {
  const fieldNames: Record<SortField, string> = {
    rating: 'rating score',
    coverage: 'video coverage',
    recency: 'video recency',
    release: 'release date',
    price: 'price',
    channels: 'channel count',
    reviews: 'review count',
  }

  const directionText = direction === 'desc' ? 'highest first' : 'lowest first'
  return `${fieldNames[field]} (${directionText})`
}

const toggleAdvancedMode = (): void => {
  isAdvancedMode.value = !isAdvancedMode.value

  if (!isAdvancedMode.value) {
    // Switching back to simple mode
    emitSortChange()
  } else {
    // Switching to advanced mode
    handleAdvancedSortChange()
  }
}

const addSecondaryCriteria = (): void => {
  hasSecondaryCriteria.value = true
  handleAdvancedSortChange()
}

const removeSecondaryCriteria = (): void => {
  hasSecondaryCriteria.value = false
  handleAdvancedSortChange()
}

const applyPreset = (preset: QuickPreset): void => {
  primaryCriteria.value = { ...preset.primary }
  secondaryCriteria.value = { ...preset.secondary }
  hasSecondaryCriteria.value = true
  handleAdvancedSortChange()
}

const handleSortChange = (): void => {
  emitSortChange()
}

const handleAdvancedSortChange = (): void => {
  // Convert advanced criteria to sort specification
  const sortSpec: AdvancedSortSpec = {
    mode: 'advanced',
    primary: primaryCriteria.value,
    secondary: hasSecondaryCriteria.value ? secondaryCriteria.value : null,
  }

  emit('sortChanged', {
    sortBy: 'advanced',
    sortSpec: sortSpec as SortSpec,
  })
}

const emitSortChange = (): void => {
  if (isAdvancedMode.value) {
    handleAdvancedSortChange()
  } else {
    emit('sortChanged', {
      sortBy: currentSort.value,
      sortSpec: null as SortSpec,
    })
  }
}

// Initialize based on incoming sort
const initializeFromSort = (sortValue: string): void => {
  if (sortValue === 'advanced') {
    isAdvancedMode.value = true
  } else {
    currentSort.value = sortValue
    isAdvancedMode.value = false
  }
}

// Watch for external sort changes
watch(
  () => props.initialSort,
  (newSort: string) => {
    initializeFromSort(newSort)
  },
)

// Initialize on mount
initializeFromSort(props.initialSort)
</script>

<template>
  <div class="space-y-3">
    <div class="flex items-center gap-2">
      <h3 class="text-sm font-semibold text-text-primary">Sort By</h3>
      <button
        v-if="showAdvancedToggle"
        @click="toggleAdvancedMode"
        class="rounded-sm bg-accent/20 px-2 py-0.5 text-xs text-accent transition-colors hover:bg-accent/30"
        :title="
          isAdvancedMode
            ? 'Switch to simple sorting'
            : 'Enable advanced multi-criteria sorting'
        "
      >
        {{ isAdvancedMode ? 'Simple' : 'Advanced' }}
      </button>
    </div>

    <!-- Simple Mode: Traditional single-criteria sorting -->
    <div v-if="!isAdvancedMode" class="flex flex-col gap-2">
      <select
        v-model="currentSort"
        class="cursor-pointer rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary hover:border-accent"
        @change="handleSortChange"
      >
        <optgroup label="Basic Sorting">
          <option value="date">Latest Videos</option>
          <option value="rating-score">Highest Rated</option>
          <option value="rating-category">Rating Tiers</option>
          <option value="name">Alphabetical</option>
          <option value="release-new">Newest Releases</option>
          <option value="release-old">Oldest Releases</option>
        </optgroup>

        <optgroup label="Discovery Sorting" v-if="!hideSmartPresets">
          <option value="best-value">Best Value</option>
          <option value="hidden-gems">Hidden Gems</option>
          <option value="most-covered">Most Covered</option>
          <option value="trending">Trending Up</option>
          <option value="creator-consensus">Creator Consensus</option>
          <option value="recent-discoveries">Recent Discoveries</option>
        </optgroup>

        <!-- Contextual sorting options based on active filters -->
        <optgroup label="Contextual" v-if="contextualSortOptions.length > 0">
          <option
            v-for="option in contextualSortOptions"
            :key="option.value"
            :value="option.value"
          >
            {{ option.label }}
          </option>
        </optgroup>
      </select>

      <!-- Sort explanation -->
      <div v-if="currentSortInfo" class="text-xs text-text-secondary/80 italic">
        {{ currentSortInfo }}
      </div>
    </div>

    <!-- Advanced Mode: Multi-criteria custom sorting -->
    <div v-else class="flex flex-col gap-3">
      <!-- Primary Sort Criteria -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between">
          <span class="text-xs font-medium text-text-secondary"
            >Primary Sort</span
          >
          <button
            @click="addSecondaryCriteria"
            v-if="!hasSecondaryCriteria"
            class="rounded-sm bg-accent/20 px-2 py-0.5 text-xs text-accent transition-colors hover:bg-accent/30"
          >
            Add Secondary
          </button>
        </div>
        <div class="flex gap-2">
          <select
            v-model="primaryCriteria.field"
            class="flex-1 cursor-pointer rounded-sm border border-gray-600 bg-bg-card px-2 py-1.5 text-sm text-text-primary hover:border-accent"
            @change="handleAdvancedSortChange"
          >
            <option value="rating">Rating Score</option>
            <option value="coverage">Video Coverage</option>
            <option value="recency">Video Recency</option>
            <option value="release">Release Date</option>
            <option value="price">Price Value</option>
            <option value="channels">Channel Count</option>
            <option value="reviews">Review Count</option>
          </select>
          <select
            v-model="primaryCriteria.direction"
            class="cursor-pointer rounded-sm border border-gray-600 bg-bg-card px-2 py-1.5 text-sm text-text-primary hover:border-accent"
            @change="handleAdvancedSortChange"
          >
            <option value="desc">High to Low</option>
            <option value="asc">Low to High</option>
          </select>
        </div>
      </div>

      <!-- Secondary Sort Criteria -->
      <div v-if="hasSecondaryCriteria" class="flex flex-col gap-2">
        <div class="flex items-center justify-between">
          <span class="text-xs font-medium text-text-secondary"
            >Secondary Sort</span
          >
          <button
            @click="removeSecondaryCriteria"
            class="rounded-sm bg-red-500/20 px-2 py-0.5 text-xs text-red-400 transition-colors hover:bg-red-500/30"
          >
            Remove
          </button>
        </div>
        <div class="flex gap-2">
          <select
            v-model="secondaryCriteria.field"
            class="flex-1 cursor-pointer rounded-sm border border-gray-600 bg-bg-card px-2 py-1.5 text-sm text-text-primary hover:border-accent"
            @change="handleAdvancedSortChange"
          >
            <option value="rating">Rating Score</option>
            <option value="coverage">Video Coverage</option>
            <option value="recency">Video Recency</option>
            <option value="release">Release Date</option>
            <option value="price">Price Value</option>
            <option value="channels">Channel Count</option>
            <option value="reviews">Review Count</option>
          </select>
          <select
            v-model="secondaryCriteria.direction"
            class="cursor-pointer rounded-sm border border-gray-600 bg-bg-card px-2 py-1.5 text-sm text-text-primary hover:border-accent"
            @change="handleAdvancedSortChange"
          >
            <option value="desc">High to Low</option>
            <option value="asc">Low to High</option>
          </select>
        </div>
      </div>

      <!-- Preset Quick Actions -->
      <div class="flex flex-wrap gap-2">
        <button
          v-for="preset in quickPresets"
          :key="preset.key"
          @click="applyPreset(preset)"
          class="rounded-sm border border-gray-600 bg-bg-card px-2 py-1 text-xs text-text-secondary transition-colors hover:border-accent hover:text-text-primary"
          :title="preset.description"
        >
          {{ preset.name }}
        </button>
      </div>

      <!-- Advanced Sort Explanation -->
      <div
        v-if="advancedSortInfo"
        class="border-t border-gray-600 pt-2 text-xs text-text-secondary/80 italic"
      >
        {{ advancedSortInfo }}
      </div>
    </div>
  </div>
</template>
