<template>
  <!-- Applied Filters Bar (Mobile & Desktop) -->
  <AppliedFiltersBar
    :filters="localFilters"
    @remove-filter="handleRemoveFilter"
    @clear-all-filters="handleClearAllFilters"
  />

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
  <div class="mb-8 hidden rounded-lg bg-bg-secondary p-5 md:block">
    <div class="flex flex-wrap items-center gap-5">
      <!-- Release Status Filter -->
      <div class="flex flex-col gap-1">
        <label class="text-sm text-text-secondary">Release Status:</label>
        <select
          v-model="localFilters.releaseStatus"
          class="cursor-pointer rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary hover:border-accent"
          @change="debouncedEmitFiltersChanged"
        >
          <option value="all">All Games</option>
          <option value="released">Released Only</option>
          <option value="early-access">Early Access</option>
          <option value="coming-soon">Coming Soon</option>
        </select>
      </div>

      <!-- Platform Filter -->
      <div class="flex flex-col gap-1">
        <label class="text-sm text-text-secondary">Platform:</label>
        <select
          v-model="localFilters.platform"
          class="cursor-pointer rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary hover:border-accent"
          @change="debouncedEmitFiltersChanged"
        >
          <option value="all">All Platforms</option>
          <option value="steam">Steam</option>
          <option value="itch">Itch.io</option>
          <option value="crazygames">CrazyGames</option>
        </select>
      </div>

      <!-- Cross-Platform Filter -->
      <div class="flex flex-col gap-1">
        <label class="text-sm text-text-secondary">Cross-Platform:</label>
        <div class="flex items-center gap-2">
          <input
            id="crossPlatform"
            v-model="localFilters.crossPlatform"
            type="checkbox"
            class="size-4 cursor-pointer rounded-sm border-gray-600 bg-bg-card text-accent focus:ring-accent focus:ring-offset-0"
            @change="debouncedEmitFiltersChanged"
          />
          <label
            for="crossPlatform"
            class="cursor-pointer text-sm text-text-primary"
          >
            Multi-platform only
          </label>
        </div>
      </div>

      <!-- Hidden Gems Filter -->
      <div class="flex flex-col gap-1">
        <label class="text-sm text-text-secondary">Hidden Gems:</label>
        <div class="flex items-center gap-2">
          <input
            id="hiddenGems"
            v-model="localFilters.hiddenGems"
            type="checkbox"
            class="size-4 cursor-pointer rounded-sm border-gray-600 bg-bg-card text-accent focus:ring-accent focus:ring-offset-0"
            @change="debouncedEmitFiltersChanged"
          />
          <label
            for="hiddenGems"
            class="cursor-pointer text-sm text-text-primary"
            title="High quality games (80%+ rating) with limited video coverage (1-3 videos) and sufficient reviews (50+)"
          >
            Quality, low coverage
          </label>
        </div>
      </div>

      <!-- Rating Filter -->
      <div class="flex flex-col gap-1">
        <label class="text-sm text-text-secondary">Minimum Rating:</label>
        <select
          v-model="localFilters.rating"
          class="cursor-pointer rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary hover:border-accent"
          @change="debouncedEmitFiltersChanged"
        >
          <option value="0">All Ratings</option>
          <option value="70">70%+ Positive</option>
          <option value="80">80%+ Positive</option>
          <option value="90">90%+ Positive</option>
        </select>
      </div>

      <!-- Tag Filter (Multi-Select) -->
      <div class="flex flex-col gap-1">
        <TagFilterMulti
          :tags-with-counts="tags"
          :initial-selected-tags="localFilters.selectedTags || []"
          :initial-tag-logic="localFilters.tagLogic || 'and'"
          @tags-changed="handleTagsChanged"
        />
      </div>

      <!-- Channel Filter (Multi-Select) -->
      <div class="flex flex-col gap-1">
        <ChannelFilterMulti
          :channels-with-counts="channelsWithCounts"
          :initial-selected-channels="localFilters.selectedChannels || []"
          @channels-changed="handleChannelsChanged"
        />
      </div>

      <!-- Advanced Sort Filter -->
      <div class="flex flex-col gap-1">
        <SortingOptions
          :initial-sort="localFilters.sortBy"
          :contextual-filters="localFilters"
          @sort-changed="handleSortChanged"
        />
      </div>

      <!-- Currency Filter -->
      <div class="flex flex-col gap-1">
        <label class="text-sm text-text-secondary">Currency:</label>
        <select
          v-model="localFilters.currency"
          class="cursor-pointer rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary hover:border-accent"
          @change="debouncedEmitFiltersChanged"
        >
          <option value="eur">EUR (€)</option>
          <option value="usd">USD ($)</option>
        </select>
      </div>

      <!-- Time Filter -->
      <div class="flex flex-col gap-1">
        <TimeFilterSimple
          :initial-time-filter="localFilters.timeFilter || {}"
          @time-filter-changed="handleTimeFilterChanged"
        />
      </div>

      <!-- Price Filter -->
      <div class="flex flex-col gap-1">
        <PriceFilter
          :currency="localFilters.currency"
          :initial-price-filter="localFilters.priceFilter || {}"
          :game-stats="gameStats"
          @price-filter-changed="handlePriceFilterChanged"
        />
      </div>

      <!-- Filter Presets -->
      <div class="flex flex-col gap-1">
        <FilterPresets
          :current-filters="localFilters"
          @apply-preset="handleApplyPreset"
        />
      </div>
    </div>
  </div>
</template>

<script>
import { reactive, computed, ref, onUnmounted } from 'vue'
import { useDebouncedFilters } from '../composables/useDebouncedFilters.js'
import TagFilterMulti from './TagFilterMulti.vue'
import ChannelFilterMulti from './ChannelFilterMulti.vue'
import TimeFilterSimple from './TimeFilterSimple.vue'
import PriceFilter from './PriceFilter.vue'
import SortingOptions from './SortingOptions.vue'
import MobileFilterModal from './MobileFilterModal.vue'
import AppliedFiltersBar from './AppliedFiltersBar.vue'
import FilterPresets from './FilterPresets.vue'

export default {
  name: 'GameFilters',
  components: {
    TagFilterMulti,
    ChannelFilterMulti,
    TimeFilterSimple,
    PriceFilter,
    SortingOptions,
    MobileFilterModal,
    AppliedFiltersBar,
    FilterPresets,
  },
  props: {
    channels: {
      type: Array,
      default: () => [],
    },
    channelsWithCounts: {
      type: Array,
      default: () => [],
    },
    tags: {
      type: Array,
      default: () => [],
    },
    initialFilters: {
      type: Object,
      default: () => ({}),
    },
    gameCount: {
      type: Number,
      default: 0,
    },
    gameStats: {
      type: Object,
      default: () => ({
        totalGames: 0,
        freeGames: 0,
        maxPrice: 70,
      }),
    },
  },
  emits: ['filters-changed'],
  setup(props, { emit }) {
    const showMobileModal = ref(false)
    const initialLocalFilters = {
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
      tagLogic: props.initialFilters.tagLogic || 'and',
      // Legacy single channel support for backward compatibility
      channel: props.initialFilters.channel || '',
      // New multi-channel support
      selectedChannels:
        props.initialFilters.selectedChannels ||
        (props.initialFilters.channel ? [props.initialFilters.channel] : []),
      sortBy: props.initialFilters.sortBy || 'date',
      sortSpec: props.initialFilters.sortSpec || null,
      currency: props.initialFilters.currency || 'eur',
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

    const localFilters = reactive({ ...initialLocalFilters })

    // Set up debounced filter updates
    const { debouncedEmit, immediateEmit, cleanup } = useDebouncedFilters(
      initialLocalFilters,
      (newFilters) => emit('filters-changed', newFilters),
      400, // 400ms debounce delay
    )

    const activeFilterCount = computed(() => {
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

    const handleTagsChanged = (tagData) => {
      localFilters.selectedTags = tagData.selectedTags
      localFilters.tagLogic = tagData.tagLogic
      // Update legacy tag field for backward compatibility
      localFilters.tag =
        tagData.selectedTags.length === 1 ? tagData.selectedTags[0] : ''
      debouncedEmitFiltersChanged()
    }

    const handleChannelsChanged = (channelData) => {
      localFilters.selectedChannels = channelData.selectedChannels
      // Update legacy channel field for backward compatibility
      localFilters.channel =
        channelData.selectedChannels.length === 1
          ? channelData.selectedChannels[0]
          : ''
      debouncedEmitFiltersChanged()
    }

    const handleTimeFilterChanged = (timeFilterData) => {
      localFilters.timeFilter = { ...timeFilterData }
      debouncedEmitFiltersChanged()
    }

    const handlePriceFilterChanged = (priceFilterData) => {
      localFilters.priceFilter = { ...priceFilterData }
      debouncedEmitFiltersChanged()
    }

    const handleSortChanged = (sortData) => {
      localFilters.sortBy = sortData.sortBy
      localFilters.sortSpec = sortData.sortSpec
      // Sort changes should be immediate for better UX
      immediateEmitFiltersChanged()
    }

    const handleFiltersChanged = (newFilters) => {
      Object.assign(localFilters, newFilters)
      debouncedEmitFiltersChanged()
    }

    const handleRemoveFilter = (filterInfo) => {
      switch (filterInfo.type) {
        case 'releaseStatus':
          localFilters.releaseStatus = filterInfo.value
          break
        case 'platform':
          localFilters.platform = filterInfo.value
          break
        case 'rating':
          localFilters.rating = filterInfo.value
          break
        case 'crossPlatform':
          localFilters.crossPlatform = filterInfo.value
          break
        case 'hiddenGems':
          localFilters.hiddenGems = filterInfo.value
          break
        case 'tags':
          localFilters.selectedTags = filterInfo.value
          localFilters.tag = ''
          break
        case 'channels':
          localFilters.selectedChannels = filterInfo.value
          localFilters.channel = ''
          break
        case 'sortBy':
          localFilters.sortBy = filterInfo.value
          localFilters.sortSpec = null
          break
        case 'currency':
          localFilters.currency = filterInfo.value
          break
        case 'timeFilter':
          localFilters.timeFilter = filterInfo.value
          break
        case 'priceFilter':
          localFilters.priceFilter = filterInfo.value
          break
      }
      // Remove operations should be immediate
      immediateEmitFiltersChanged()
    }

    const handleClearAllFilters = () => {
      localFilters.releaseStatus = 'all'
      localFilters.platform = 'all'
      localFilters.rating = '0'
      localFilters.crossPlatform = false
      localFilters.hiddenGems = false
      localFilters.tag = ''
      localFilters.selectedTags = []
      localFilters.tagLogic = 'and'
      localFilters.channel = ''
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
    }

    const handleApplyPreset = (presetFilters) => {
      Object.assign(localFilters, presetFilters)
      // Preset changes should be immediate
      immediateEmitFiltersChanged()
    }

    // Debounced emit for gradual filter changes
    const debouncedEmitFiltersChanged = () => {
      debouncedEmit({ ...localFilters })
    }

    // Immediate emit for important changes
    const immediateEmitFiltersChanged = () => {
      immediateEmit({ ...localFilters })
    }

    // Legacy emit function for backward compatibility
    const emitFiltersChanged = () => {
      debouncedEmitFiltersChanged()
    }

    const formatChannelName = (channel) => {
      if (!channel || typeof channel !== 'string') {
        return 'Unknown Channel'
      }
      return channel
        .replace(/^videos-/, '')
        .replace(/-/g, ' ')
        .replace(/\b\w/g, (l) => l.toUpperCase())
    }

    // Cleanup on unmount
    onUnmounted(() => {
      cleanup()
    })

    return {
      showMobileModal,
      localFilters,
      activeFilterCount,
      handleTagsChanged,
      handleChannelsChanged,
      handleTimeFilterChanged,
      handlePriceFilterChanged,
      handleSortChanged,
      handleFiltersChanged,
      handleRemoveFilter,
      handleClearAllFilters,
      handleApplyPreset,
      emitFiltersChanged,
      debouncedEmitFiltersChanged,
      immediateEmitFiltersChanged,
      formatChannelName,
    }
  },
}
</script>
