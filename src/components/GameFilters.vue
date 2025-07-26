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
      @height-change="handleActiveFiltersHeightChange"
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
        :initial-time-filter="localFilters.timeFilter || {}"
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
        :initial-price-filter="localFilters.priceFilter || {}"
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

<script>
import { reactive, computed, ref, onUnmounted, nextTick } from 'vue'
import { useDebouncedFilters } from '../composables/useDebouncedFilters.js'
import CollapsibleSection from './CollapsibleSection.vue'
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
    CollapsibleSection,
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

    // Section-specific active filter counts for badges
    const basicFiltersCount = computed(() => {
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

    const ratingFiltersCount = computed(() => {
      return localFilters.rating !== '0' ? 1 : 0
    })

    const tagsCount = computed(() => {
      return localFilters.selectedTags.length > 0
        ? localFilters.selectedTags.length
        : 0
    })

    const channelsCount = computed(() => {
      return localFilters.selectedChannels.length > 0
        ? localFilters.selectedChannels.length
        : 0
    })

    const sortingCount = computed(() => {
      return localFilters.sortBy !== 'date' || localFilters.sortSpec ? 1 : 0
    })

    const timeFilterCount = computed(() => {
      return localFilters.timeFilter && localFilters.timeFilter.type ? 1 : 0
    })

    const priceFilterCount = computed(() => {
      return localFilters.priceFilter &&
        (localFilters.priceFilter.minPrice > 0 ||
          localFilters.priceFilter.maxPrice < 70 ||
          !localFilters.priceFilter.includeFree)
        ? 1
        : 0
    })

    const currencyCount = computed(() => {
      return localFilters.currency !== 'eur' ? 1 : 0
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

    // Helper to preserve scroll position when filters change
    const preserveScrollPosition = (callback) => {
      // Find the sidebar scroll container
      const scrollContainer = document.querySelector('.sidebar-scroll')
      if (!scrollContainer) {
        callback()
        return
      }

      // Save current scroll position
      const scrollTop = scrollContainer.scrollTop

      // Execute the callback
      callback()

      // Restore scroll position after DOM update
      nextTick(() => {
        scrollContainer.scrollTop = scrollTop
      })
    }

    const handleRemoveFilter = (filterInfo) => {
      preserveScrollPosition(() => {
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
      })
    }

    const handleClearAllFilters = () => {
      preserveScrollPosition(() => {
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
      })
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
      basicFiltersCount,
      ratingFiltersCount,
      tagsCount,
      channelsCount,
      sortingCount,
      timeFilterCount,
      priceFilterCount,
      currencyCount,
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
