<script setup lang="ts">
import {
  ref,
  reactive,
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  watch,
  type Ref,
} from 'vue'
import type { FilterConfig } from '../utils/presetManager'
import type {
  ChannelWithCount,
  TagWithCount,
  DatabaseStats,
} from '../types/database'
import type { SortChangeEvent } from '../types/sorting'
import MobileTagFilter from './MobileTagFilter.vue'
import MobileChannelFilter from './MobileChannelFilter.vue'
import MobileTimeFilterSimple from './MobileTimeFilterSimple.vue'
import MobilePriceFilter from './MobilePriceFilter.vue'
import MobileSortingOptions from './MobileSortingOptions.vue'
import MobileFilterPresets from './MobileFilterPresets.vue'

// Component props interface
interface Props {
  isOpen?: boolean
  channels?: string[]
  channelsWithCounts?: ChannelWithCount[]
  tags?: TagWithCount[]
  initialFilters?: Partial<FilterConfig>
  gameStats?: DatabaseStats
}

// Component events interface
interface Emits {
  close: []
  filtersChanged: [filters: FilterConfig]
}

// Define props with defaults
const props = withDefaults(defineProps<Props>(), {
  isOpen: false,
  channels: () => [],
  channelsWithCounts: () => [],
  tags: () => [],
  initialFilters: () => ({}),
  gameStats: () => ({
    totalGames: 0,
    freeGames: 0,
    maxPrice: 70,
  }),
})

// Define emits
const emit = defineEmits<Emits>()

// Option interfaces
interface Option {
  value: string
  label: string
}

// Tab interface
interface Tab {
  id: string
  label: string
  count: number
}

// Filter data interfaces
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
}

// SortData interface is replaced by SortChangeEvent from types/sorting.ts

// Reactive state with proper typing
const isAnimating: Ref<boolean> = ref(false)
const activeTab: Ref<string> = ref('presets')

// Touch handling for swipe-to-close
const touchStartY: Ref<number> = ref(0)
const touchCurrentY: Ref<number> = ref(0)
const isDragging: Ref<boolean> = ref(false)

// Initialize local filters with proper defaults
const localFilters = reactive<FilterConfig>({
  releaseStatus: props.initialFilters.releaseStatus || 'all',
  platform: props.initialFilters.platform || 'all',
  rating: props.initialFilters.rating || '0',
  crossPlatform: props.initialFilters.crossPlatform || false,
  hiddenGems: props.initialFilters.hiddenGems || false,
  tag: props.initialFilters.tag || '',
  selectedTags: props.initialFilters.selectedTags || [],
  tagLogic: (props.initialFilters.tagLogic as 'and' | 'or') || 'and',
  channel: props.initialFilters.channel || '',
  selectedChannels: props.initialFilters.selectedChannels || [],
  sortBy: props.initialFilters.sortBy || 'date',
  sortSpec: props.initialFilters.sortSpec || null,
  currency: (props.initialFilters.currency as 'eur' | 'usd') || 'eur',
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
  },
})

// Filter options
const releaseStatusOptions: Option[] = [
  { value: 'all', label: 'All Games' },
  { value: 'released', label: 'Released Only' },
  { value: 'early-access', label: 'Early Access' },
  { value: 'coming-soon', label: 'Coming Soon' },
]

const platformOptions: Option[] = [
  { value: 'all', label: 'All Platforms' },
  { value: 'steam', label: 'Steam' },
  { value: 'itch', label: 'Itch.io' },
  { value: 'crazygames', label: 'CrazyGames' },
]

const ratingOptions: Option[] = [
  { value: '0', label: 'All Ratings' },
  { value: '70', label: '70%+ Positive' },
  { value: '80', label: '80%+ Positive' },
  { value: '90', label: '90%+ Positive' },
]

const currencyOptions: Option[] = [
  { value: 'eur', label: 'EUR (€)' },
  { value: 'usd', label: 'USD ($)' },
]

// Computed properties
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
      localFilters.priceFilter.maxPrice < 70)
  ) {
    count++
  }
  return count
})

const tabs = computed((): Tab[] => [
  {
    id: 'presets',
    label: 'Presets',
    count: 0,
  },
  {
    id: 'basic',
    label: 'Basic',
    count:
      (localFilters.releaseStatus !== 'all' ? 1 : 0) +
      (localFilters.platform !== 'all' ? 1 : 0) +
      (localFilters.rating !== '0' ? 1 : 0) +
      (localFilters.crossPlatform ? 1 : 0) +
      (localFilters.hiddenGems ? 1 : 0) +
      (localFilters.sortBy !== 'date' || localFilters.sortSpec ? 1 : 0) +
      (localFilters.currency !== 'eur' ? 1 : 0),
  },
  {
    id: 'tags',
    label: 'Tags',
    count: localFilters.selectedTags.length,
  },
  {
    id: 'channels',
    label: 'Channels',
    count: localFilters.selectedChannels.length,
  },
  {
    id: 'time',
    label: 'Time',
    count: localFilters.timeFilter.type ? 1 : 0,
  },
  {
    id: 'price',
    label: 'Price',
    count:
      localFilters.priceFilter.minPrice > 0 ||
      localFilters.priceFilter.maxPrice < 70
        ? 1
        : 0,
  },
])

// Animation handling
const startAnimation = async (): Promise<void> => {
  await nextTick()
  requestAnimationFrame(() => {
    isAnimating.value = true
  })
}

const stopAnimation = (): void => {
  isAnimating.value = false
  setTimeout(() => {
    emit('close')
  }, 300)
}

// Touch handling
const handleTouchStart = (e: TouchEvent): void => {
  touchStartY.value = e.touches[0].clientY
  isDragging.value = true
}

const handleTouchMove = (e: TouchEvent): void => {
  if (!isDragging.value) {
    return
  }

  touchCurrentY.value = e.touches[0].clientY
  const deltaY = touchCurrentY.value - touchStartY.value

  // Only allow downward swipes and only if we're at the top of scroll content
  if (deltaY > 0) {
    const scrollContainer = (e.currentTarget as HTMLElement).querySelector(
      '.overflow-y-auto',
    ) as HTMLElement | null
    if (!scrollContainer || scrollContainer.scrollTop === 0) {
      e.preventDefault()
      // Apply some resistance to the drag
      const resistance = Math.min(deltaY / 3, 100)
      ;(e.currentTarget as HTMLElement).style.transform =
        `translateY(${resistance}px)`
    }
  }
}

const handleTouchEnd = (e: TouchEvent): void => {
  if (!isDragging.value) {
    return
  }

  const deltaY = touchCurrentY.value - touchStartY.value

  // Reset transform
  ;(e.currentTarget as HTMLElement).style.transform = ''

  // Close if dragged down far enough
  if (deltaY > 150) {
    closeModal()
  }

  isDragging.value = false
}

// Event handlers
const closeModal = (): void => {
  stopAnimation()
}

const clearAllFilters = (): void => {
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
  }
  emitFiltersChanged()
}

const handleTagsChanged = (tagData: TagChangedData): void => {
  localFilters.selectedTags = tagData.selectedTags
  localFilters.tagLogic = tagData.tagLogic
  emitFiltersChanged()
}

const handleChannelsChanged = (channelData: ChannelChangedData): void => {
  localFilters.selectedChannels = channelData.selectedChannels
  emitFiltersChanged()
}

const handleTimeFilterChanged = (timeFilterData: TimeFilterData): void => {
  localFilters.timeFilter = { ...timeFilterData }
  emitFiltersChanged()
}

const handlePriceFilterChanged = (priceFilterData: PriceFilterData): void => {
  localFilters.priceFilter = { ...priceFilterData }
  emitFiltersChanged()
}

const handleSortChanged = (sortEvent: SortChangeEvent): void => {
  localFilters.sortBy = sortEvent.sortBy
  localFilters.sortSpec = sortEvent.sortSpec
  emitFiltersChanged()
}

const emitFiltersChanged = (): void => {
  emit('filtersChanged', { ...localFilters })
}

const handleApplyPreset = (presetFilters: FilterConfig): void => {
  Object.assign(localFilters, presetFilters)
  emitFiltersChanged()
}

// Handle keyboard events
const handleKeydown = (e: KeyboardEvent): void => {
  if (e.key === 'Escape' && props.isOpen) {
    closeModal()
  }
}

// Watch for prop changes
const updateLocalFilters = (): void => {
  Object.assign(localFilters, props.initialFilters)
}

// Watch for isOpen changes
const handleOpenChange = (newValue: boolean): void => {
  if (newValue) {
    startAnimation()
    updateLocalFilters()
    document.body.classList.add('modal-open')
  } else {
    document.body.classList.remove('modal-open')
  }
}

// Lifecycle hooks
onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
  if (props.isOpen) {
    startAnimation()
    document.body.classList.add('modal-open')
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  document.body.classList.remove('modal-open')
})

// Watch for isOpen changes
watch(
  () => props.isOpen,
  (newValue: boolean) => {
    handleOpenChange(newValue)
  },
)

// Watch for initialFilters changes
watch(
  () => props.initialFilters,
  () => {
    updateLocalFilters()
  },
  { deep: true },
)
</script>

<template>
  <!-- Backdrop -->
  <div
    v-if="isOpen"
    class="fixed inset-0 z-40 bg-black/50 transition-opacity duration-300"
    :class="{ 'opacity-100': isAnimating, 'opacity-0': !isAnimating }"
    @click="closeModal"
  ></div>

  <!-- Modal -->
  <div
    v-if="isOpen"
    class="fixed inset-x-0 bottom-0 z-50 transform transition-transform duration-300 ease-out"
    :class="{ 'translate-y-0': isAnimating, 'translate-y-full': !isAnimating }"
    @touchstart="handleTouchStart"
    @touchmove="handleTouchMove"
    @touchend="handleTouchEnd"
  >
    <!-- Handle/Grip -->
    <div class="flex justify-center pt-2 pb-1">
      <div class="h-1 w-10 rounded-full bg-gray-400"></div>
    </div>

    <!-- Modal Content -->
    <div class="rounded-t-xl bg-bg-secondary shadow-xl">
      <!-- Header -->
      <div
        class="flex items-center justify-between border-b border-gray-600 px-4 py-3"
      >
        <h2 class="text-lg font-semibold text-text-primary">Filters</h2>
        <div class="flex items-center gap-3">
          <span
            v-if="activeFilterCount > 0"
            class="text-sm text-text-secondary"
          >
            {{ activeFilterCount }} active
          </span>
          <button
            @click="clearAllFilters"
            class="text-sm text-accent hover:text-accent-hover disabled:opacity-50"
            :disabled="activeFilterCount === 0"
          >
            Clear All
          </button>
          <button
            @click="closeModal"
            class="rounded-full p-1 text-text-secondary hover:bg-bg-primary hover:text-text-primary"
          >
            <svg
              class="size-6"
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
        </div>
      </div>

      <!-- Tabs -->
      <div class="border-b border-gray-600 bg-bg-primary">
        <div class="scrollbar-none flex overflow-x-auto">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            class="shrink-0 px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors"
            :class="
              activeTab === tab.id
                ? 'border-b-2 border-accent text-accent'
                : 'text-text-secondary hover:text-text-primary'
            "
          >
            {{ tab.label }}
            <span v-if="tab.count > 0" class="ml-1 text-xs opacity-75"
              >({{ tab.count }})</span
            >
          </button>
        </div>
      </div>

      <!-- Tab Content -->
      <div class="overflow-y-auto p-4" style="max-height: 70vh">
        <!-- Presets Tab -->
        <div v-if="activeTab === 'presets'">
          <MobileFilterPresets
            :current-filters="localFilters"
            @apply-preset="handleApplyPreset"
          />
        </div>

        <!-- Basic Filters Tab -->
        <div v-else-if="activeTab === 'basic'" class="space-y-6">
          <!-- Release Status -->
          <div>
            <label class="mb-2 block text-sm font-medium text-text-secondary"
              >Release Status</label
            >
            <div class="space-y-2">
              <label
                v-for="option in releaseStatusOptions"
                :key="option.value"
                class="flex items-center"
              >
                <input
                  v-model="localFilters.releaseStatus"
                  :value="option.value"
                  type="radio"
                  name="releaseStatus"
                  class="mr-3 size-4 text-accent focus:ring-2 focus:ring-accent"
                  @change="emitFiltersChanged"
                />
                <span class="text-text-primary">{{ option.label }}</span>
              </label>
            </div>
          </div>

          <!-- Platform -->
          <div>
            <label class="mb-2 block text-sm font-medium text-text-secondary"
              >Platform</label
            >
            <div class="space-y-2">
              <label
                v-for="option in platformOptions"
                :key="option.value"
                class="flex items-center"
              >
                <input
                  v-model="localFilters.platform"
                  :value="option.value"
                  type="radio"
                  name="platform"
                  class="mr-3 size-4 text-accent focus:ring-2 focus:ring-accent"
                  @change="emitFiltersChanged"
                />
                <span class="text-text-primary">{{ option.label }}</span>
              </label>
            </div>
          </div>

          <!-- Cross-Platform -->
          <div>
            <label class="mb-2 block text-sm font-medium text-text-secondary"
              >Cross-Platform</label
            >
            <div class="flex items-center">
              <input
                id="crossPlatformMobile"
                v-model="localFilters.crossPlatform"
                type="checkbox"
                class="mr-3 size-4 rounded-sm text-accent focus:ring-2 focus:ring-accent"
                @change="emitFiltersChanged"
              />
              <label for="crossPlatformMobile" class="text-text-primary">
                Show only multi-platform games
              </label>
            </div>
          </div>

          <!-- Hidden Gems -->
          <div>
            <label class="mb-2 block text-sm font-medium text-text-secondary"
              >Hidden Gems</label
            >
            <div class="flex items-center">
              <input
                id="hiddenGemsMobile"
                v-model="localFilters.hiddenGems"
                type="checkbox"
                class="mr-3 size-4 rounded-sm text-accent focus:ring-2 focus:ring-accent"
                @change="emitFiltersChanged"
              />
              <label for="hiddenGemsMobile" class="text-text-primary">
                High quality, low coverage games
              </label>
            </div>
            <p class="mt-1 text-xs text-text-secondary">
              80%+ rating, 1-3 videos, 50+ reviews
            </p>
          </div>

          <!-- Rating -->
          <div>
            <label class="mb-2 block text-sm font-medium text-text-secondary"
              >Minimum Rating</label
            >
            <div class="space-y-2">
              <label
                v-for="option in ratingOptions"
                :key="option.value"
                class="flex items-center"
              >
                <input
                  v-model="localFilters.rating"
                  :value="option.value"
                  type="radio"
                  name="rating"
                  class="mr-3 size-4 text-accent focus:ring-2 focus:ring-accent"
                  @change="emitFiltersChanged"
                />
                <span class="text-text-primary">{{ option.label }}</span>
              </label>
            </div>
          </div>

          <!-- Advanced Sort -->
          <div>
            <MobileSortingOptions
              :initial-sort="localFilters.sortBy"
              :initial-sort-spec="localFilters.sortSpec"
              @sort-changed="handleSortChanged"
            />
          </div>

          <!-- Currency -->
          <div>
            <label class="mb-2 block text-sm font-medium text-text-secondary"
              >Currency</label
            >
            <div class="space-y-2">
              <label
                v-for="option in currencyOptions"
                :key="option.value"
                class="flex items-center"
              >
                <input
                  v-model="localFilters.currency"
                  :value="option.value"
                  type="radio"
                  name="currency"
                  class="mr-3 size-4 text-accent focus:ring-2 focus:ring-accent"
                  @change="emitFiltersChanged"
                />
                <span class="text-text-primary">{{ option.label }}</span>
              </label>
            </div>
          </div>
        </div>

        <!-- Tags Tab -->
        <div v-else-if="activeTab === 'tags'">
          <MobileTagFilter
            :tags-with-counts="tags"
            :initial-selected-tags="localFilters.selectedTags || []"
            :initial-tag-logic="localFilters.tagLogic || 'and'"
            @tags-changed="handleTagsChanged"
          />
        </div>

        <!-- Channels Tab -->
        <div v-else-if="activeTab === 'channels'">
          <MobileChannelFilter
            :channels-with-counts="channelsWithCounts"
            :initial-selected-channels="localFilters.selectedChannels || []"
            @channels-changed="handleChannelsChanged"
          />
        </div>

        <!-- Time Tab -->
        <div v-else-if="activeTab === 'time'">
          <MobileTimeFilterSimple
            :initial-time-filter="localFilters.timeFilter || {}"
            @time-filter-changed="handleTimeFilterChanged"
          />
        </div>

        <!-- Price Tab -->
        <div v-else-if="activeTab === 'price'">
          <MobilePriceFilter
            :currency="localFilters.currency"
            :initial-price-filter="localFilters.priceFilter || {}"
            :game-stats="gameStats"
            @price-filter-changed="handlePriceFilterChanged"
          />
        </div>
      </div>

      <!-- Footer -->
      <div class="border-t border-gray-600 px-4 py-3">
        <div class="flex gap-3">
          <button
            @click="closeModal"
            class="flex-1 rounded-lg bg-accent px-4 py-3 font-medium text-white transition-colors hover:bg-accent-hover active:bg-accent-active"
          >
            Apply Filters
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Hide scrollbar while keeping functionality */
.scrollbar-none {
  -ms-overflow-style: none; /* Internet Explorer 10+ */
  scrollbar-width: none; /* Firefox */
}

.scrollbar-none::-webkit-scrollbar {
  display: none; /* Safari and Chrome */
}

/* Ensure modal appears above everything */
.z-40 {
  z-index: 40;
}

.z-50 {
  z-index: 50;
}

/* Custom radio button styling for better touch targets */
input[type='radio'] {
  min-width: 1rem;
  min-height: 1rem;
}

/* Active states for better touch feedback */
.active\:bg-accent-active:active {
  background-color: theme('colors.accent') / 0.8;
}
</style>
