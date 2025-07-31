<script setup lang="ts">
import { ref, computed, watch, type Ref, type ComputedRef } from 'vue'
import type {
  SortSpec,
  SortField,
  SortDirection,
  SortCriteria,
  AdvancedSortSpec,
  SortChangeEvent,
} from '../types/sorting'
import { isAdvancedSortSpec, normalizeSortSpec } from '../types/sorting'
import { debug } from '../utils/debug'

// Component props interface
interface Props {
  initialSort?: string
  initialSortSpec?: SortSpec
}

// Component events interface
interface Emits {
  sortChanged: [event: SortChangeEvent]
}

// Define props with defaults
const props = withDefaults(defineProps<Props>(), {
  initialSort: 'date',
  initialSortSpec: null,
})

// Define emits
const emit = defineEmits<Emits>()

// Sort option interfaces
interface SortOption {
  value: string
  label: string
  description?: string
}

// Quick preset interface
interface QuickPreset {
  key: string
  name: string
  primary: SortCriteria
  secondary: SortCriteria
}
// Reactive state with proper typing
const isAdvancedMode: Ref<boolean> = ref(false)
const currentSort: Ref<string> = ref(props.initialSort)

// Advanced sorting criteria with proper typing
const primaryCriteria: Ref<SortCriteria> = ref({
  field: 'rating',
  direction: 'desc',
})

const secondaryCriteria: Ref<SortCriteria> = ref({
  field: 'coverage',
  direction: 'desc',
})

const hasSecondaryCriteria: Ref<boolean> = ref(false)

// Sort options for mobile interface with proper typing
const basicSortOptions: SortOption[] = [
  {
    value: 'date',
    label: 'Latest Videos',
    description: 'Most recent video coverage',
  },
  {
    value: 'rating-score',
    label: 'Highest Rated',
    description: 'Best Steam ratings first',
  },
  {
    value: 'rating-category',
    label: 'Rating Tiers',
    description: 'Grouped by rating categories',
  },
  {
    value: 'name',
    label: 'Alphabetical',
    description: 'A to Z by game title',
  },
  {
    value: 'release-new',
    label: 'Newest Releases',
    description: 'Most recently released games',
  },
  {
    value: 'release-old',
    label: 'Oldest Releases',
    description: 'Classic games first',
  },
]

const smartSortOptions: SortOption[] = [
  {
    value: 'best-value',
    label: 'Best Value',
    description: 'High quality at great prices',
  },
  {
    value: 'hidden-gems',
    label: 'Hidden Gems',
    description: 'Great games with less coverage',
  },
  {
    value: 'most-covered',
    label: 'Most Covered',
    description: 'Community favorites',
  },
  {
    value: 'trending',
    label: 'Trending Up',
    description: 'Games gaining attention',
  },
  {
    value: 'creator-consensus',
    label: 'Creator Consensus',
    description: 'Praised by multiple channels',
  },
  {
    value: 'recent-discoveries',
    label: 'Recent Discoveries',
    description: 'Worth checking out',
  },
]

// Quick preset combinations for advanced mode with proper typing
const quickPresets: QuickPreset[] = [
  {
    key: 'value',
    name: 'Best Value',
    primary: { field: 'rating', direction: 'desc' },
    secondary: { field: 'price', direction: 'asc' },
  },
  {
    key: 'gems',
    name: 'Hidden Gems',
    primary: { field: 'rating', direction: 'desc' },
    secondary: { field: 'coverage', direction: 'asc' },
  },
  {
    key: 'popular',
    name: 'Most Popular',
    primary: { field: 'coverage', direction: 'desc' },
    secondary: { field: 'rating', direction: 'desc' },
  },
  {
    key: 'fresh',
    name: 'Fresh Releases',
    primary: { field: 'release', direction: 'desc' },
    secondary: { field: 'recency', direction: 'desc' },
  },
]

const advancedSortInfo: ComputedRef<string> = computed(() => {
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

const toggleSecondaryCriteria = (): void => {
  hasSecondaryCriteria.value = !hasSecondaryCriteria.value
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
    mode: 'advanced' as const,
    primary: primaryCriteria.value,
    secondary: hasSecondaryCriteria.value ? secondaryCriteria.value : null,
  }

  const changeEvent: SortChangeEvent = {
    sortBy: 'advanced',
    sortSpec,
  }

  emit('sortChanged', changeEvent)
}

const emitSortChange = (): void => {
  if (isAdvancedMode.value) {
    handleAdvancedSortChange()
  } else {
    const changeEvent: SortChangeEvent = {
      sortBy: currentSort.value,
      sortSpec: null,
    }
    emit('sortChanged', changeEvent)
  }
}

// Initialize from props with proper type handling and validation
const initializeFromProps = (): void => {
  // Normalize the sort spec to handle any legacy formats
  const normalizedSortSpec = normalizeSortSpec(props.initialSortSpec)

  if (
    props.initialSort === 'advanced' &&
    isAdvancedSortSpec(normalizedSortSpec)
  ) {
    isAdvancedMode.value = true

    // Validate and set primary criteria
    if (
      normalizedSortSpec.primary &&
      isValidSortCriteria(normalizedSortSpec.primary)
    ) {
      primaryCriteria.value = { ...normalizedSortSpec.primary }
    } else {
      // Fallback to default primary criteria if invalid
      debug.warn('Invalid primary sort criteria, using defaults')
      primaryCriteria.value = { field: 'rating', direction: 'desc' }
    }

    // Validate and set secondary criteria
    if (
      normalizedSortSpec.secondary &&
      isValidSortCriteria(normalizedSortSpec.secondary)
    ) {
      secondaryCriteria.value = { ...normalizedSortSpec.secondary }
      hasSecondaryCriteria.value = true
    } else {
      hasSecondaryCriteria.value = false
      secondaryCriteria.value = { field: 'coverage', direction: 'desc' }
    }
  } else {
    // Validate simple sort value
    const validSortValue = isValidSimpleSort(props.initialSort)
      ? props.initialSort
      : 'date'
    currentSort.value = validSortValue
    isAdvancedMode.value = false
    hasSecondaryCriteria.value = false
  }
}

// Type guard for valid sort criteria
const isValidSortCriteria = (criteria: unknown): criteria is SortCriteria => {
  if (!criteria || typeof criteria !== 'object') {
    return false
  }

  const c = criteria as Record<string, unknown>
  const validFields: SortField[] = [
    'rating',
    'coverage',
    'recency',
    'release',
    'price',
    'channels',
    'reviews',
  ]
  const validDirections: SortDirection[] = ['asc', 'desc']

  return (
    typeof c.field === 'string' &&
    validFields.includes(c.field as SortField) &&
    typeof c.direction === 'string' &&
    validDirections.includes(c.direction as SortDirection)
  )
}

// Type guard for valid simple sort values
const isValidSimpleSort = (sort: string): boolean => {
  const validSorts = [
    'date',
    'rating-score',
    'rating-category',
    'name',
    'release-new',
    'release-old',
    'best-value',
    'hidden-gems',
    'most-covered',
    'trending',
    'creator-consensus',
    'recent-discoveries',
    'itch-discoveries',
  ]
  return validSorts.includes(sort)
}

// Watch for external prop changes
watch(
  [() => props.initialSort, () => props.initialSortSpec],
  () => {
    initializeFromProps()
  },
  { deep: true },
)

// Initialize on mount
initializeFromProps()
</script>

<template>
  <div class="space-y-4">
    <!-- Mode Toggle -->
    <div class="flex items-center justify-between">
      <label class="text-sm font-medium text-text-secondary">Sort Mode</label>
      <button
        @click="toggleAdvancedMode"
        class="flex items-center gap-2 rounded-lg bg-accent/20 px-3 py-1.5 text-sm text-accent transition-colors hover:bg-accent/30"
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
            :d="
              isAdvancedMode
                ? 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
                : 'M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4'
            "
          />
        </svg>
        {{ isAdvancedMode ? 'Simple Mode' : 'Advanced Mode' }}
      </button>
    </div>

    <!-- Simple Mode: Radio buttons for quick selection -->
    <div v-if="!isAdvancedMode" class="space-y-3">
      <div class="space-y-2">
        <p class="text-xs text-text-secondary">Basic Sorting</p>
        <div class="space-y-2">
          <label
            v-for="option in basicSortOptions"
            :key="option.value"
            class="flex items-start"
          >
            <input
              v-model="currentSort"
              :value="option.value"
              type="radio"
              name="mobileSort"
              class="mt-0.5 mr-3 size-4 text-accent focus:ring-2 focus:ring-accent"
              @change="handleSortChange"
            />
            <div class="flex-1">
              <span class="text-text-primary">{{ option.label }}</span>
              <p
                v-if="option.description"
                class="mt-0.5 text-xs text-text-secondary/80"
              >
                {{ option.description }}
              </p>
            </div>
          </label>
        </div>
      </div>

      <div class="space-y-2">
        <p class="text-xs text-text-secondary">Smart Discovery</p>
        <div class="space-y-2">
          <label
            v-for="option in smartSortOptions"
            :key="option.value"
            class="flex items-start"
          >
            <input
              v-model="currentSort"
              :value="option.value"
              type="radio"
              name="mobileSort"
              class="mt-0.5 mr-3 size-4 text-accent focus:ring-2 focus:ring-accent"
              @change="handleSortChange"
            />
            <div class="flex-1">
              <span class="text-text-primary">{{ option.label }}</span>
              <p
                v-if="option.description"
                class="mt-0.5 text-xs text-text-secondary/80"
              >
                {{ option.description }}
              </p>
            </div>
          </label>
        </div>
      </div>
    </div>

    <!-- Advanced Mode: Multi-criteria builder -->
    <div v-else class="space-y-4">
      <!-- Primary Sort -->
      <div class="space-y-2">
        <label class="text-sm font-medium text-text-secondary"
          >Primary Sort</label
        >
        <div class="flex gap-2">
          <select
            v-model="primaryCriteria.field"
            class="flex-1 rounded-lg border border-gray-600 bg-bg-card px-3 py-2 text-sm text-text-primary"
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
            class="rounded-lg border border-gray-600 bg-bg-card px-3 py-2 text-sm text-text-primary"
            @change="handleAdvancedSortChange"
          >
            <option value="desc">High → Low</option>
            <option value="asc">Low → High</option>
          </select>
        </div>
      </div>

      <!-- Secondary Sort Toggle -->
      <div class="flex items-center justify-between">
        <label class="text-sm font-medium text-text-secondary"
          >Secondary Sort</label
        >
        <button
          @click="toggleSecondaryCriteria"
          class="rounded-sm px-2 py-1 text-xs transition-colors"
          :class="
            hasSecondaryCriteria
              ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
              : 'bg-accent/20 text-accent hover:bg-accent/30'
          "
        >
          {{ hasSecondaryCriteria ? 'Remove' : 'Add' }}
        </button>
      </div>

      <!-- Secondary Sort -->
      <div v-if="hasSecondaryCriteria" class="flex gap-2">
        <select
          v-model="secondaryCriteria.field"
          class="flex-1 rounded-lg border border-gray-600 bg-bg-card px-3 py-2 text-sm text-text-primary"
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
          class="rounded-lg border border-gray-600 bg-bg-card px-3 py-2 text-sm text-text-primary"
          @change="handleAdvancedSortChange"
        >
          <option value="desc">High → Low</option>
          <option value="asc">Low → High</option>
        </select>
      </div>

      <!-- Quick Presets -->
      <div class="space-y-2">
        <p class="text-xs text-text-secondary">Quick Presets</p>
        <div class="grid grid-cols-2 gap-2">
          <button
            v-for="preset in quickPresets"
            :key="preset.key"
            @click="applyPreset(preset)"
            class="rounded-lg border border-gray-600 bg-bg-card px-3 py-2 text-sm text-text-secondary transition-colors hover:border-accent hover:text-text-primary"
          >
            {{ preset.name }}
          </button>
        </div>
      </div>

      <!-- Advanced Sort Explanation -->
      <div
        v-if="advancedSortInfo"
        class="rounded-lg border border-gray-600 bg-bg-primary p-3"
      >
        <p class="text-xs text-text-secondary/80">{{ advancedSortInfo }}</p>
      </div>
    </div>
  </div>
</template>
