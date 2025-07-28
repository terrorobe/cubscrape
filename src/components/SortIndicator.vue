<template>
  <div class="flex items-center gap-2 text-sm">
    <!-- Sort Icon -->
    <div class="flex items-center gap-1">
      <svg
        class="size-4 text-accent"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          :d="sortIcon"
        />
      </svg>
      <span class="text-text-secondary">Sorted by:</span>
    </div>

    <!-- Sort Method -->
    <div class="relative flex items-center gap-2">
      <!-- Sort Dropdown -->
      <div class="relative">
        <button
          @click="showSortMenu = !showSortMenu"
          class="flex items-center gap-1 rounded-sm px-2 py-1 font-medium text-text-primary transition-colors hover:bg-bg-secondary"
          :title="'Click to change sort method'"
        >
          <span>{{ sortLabel }}</span>
          <svg
            class="size-3 transition-transform duration-200"
            :class="showSortMenu ? 'rotate-180' : ''"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M19 9l-7 7-7-7"
            ></path>
          </svg>
        </button>

        <!-- Sort Options Menu -->
        <div
          v-show="showSortMenu"
          class="absolute top-full left-0 z-20 mt-1 w-56 rounded-lg border border-gray-600 bg-bg-card shadow-lg"
          @click.stop
        >
          <div class="py-2">
            <div class="px-3 pb-2 text-xs font-medium text-text-secondary">
              Basic Sorting
            </div>
            <button
              v-for="option in basicSortOptions"
              :key="option.value"
              @click="handleSortChange(option.value)"
              class="flex w-full items-center justify-between px-3 py-2 text-left text-sm transition-colors hover:bg-bg-secondary"
              :class="
                sortBy === option.value
                  ? 'bg-accent/10 text-accent'
                  : 'text-text-primary'
              "
            >
              <span>{{ option.label }}</span>
              <svg
                v-if="sortBy === option.value"
                class="size-4 text-accent"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M5 13l4 4L19 7"
                ></path>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Advanced indicator -->
      <span
        v-if="isAdvanced"
        class="rounded-full bg-accent/20 px-2 py-0.5 text-xs font-medium text-accent"
        :title="advancedDetails"
      >
        Multi-criteria
      </span>

      <!-- Contextual indicator -->
      <span
        v-if="isContextual"
        class="rounded-full bg-blue-500/20 px-2 py-0.5 text-xs font-medium text-blue-400"
        title="This sort adapts to your active filters"
      >
        Contextual
      </span>

      <!-- Smart indicator -->
      <span
        v-if="isSmart"
        class="rounded-full bg-purple-500/20 px-2 py-0.5 text-xs font-medium text-purple-400"
        title="Intelligent game discovery algorithm"
      >
        Smart
      </span>
    </div>

    <!-- Explanation tooltip -->
    <div v-if="explanation" class="group relative">
      <svg
        class="size-4 cursor-help text-text-secondary/60 hover:text-text-secondary"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>

      <!-- Tooltip -->
      <div
        class="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 w-64 -translate-x-1/2 transform rounded-lg border border-gray-600 bg-bg-card px-3 py-2 opacity-0 shadow-lg transition-opacity duration-200 group-hover:opacity-100"
      >
        <p class="text-xs text-text-primary">{{ explanation }}</p>
        <div
          class="absolute top-full left-1/2 -translate-x-1/2 transform border-4 border-transparent border-t-gray-600"
        ></div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, ref, onMounted, onUnmounted } from 'vue'

export default {
  name: 'SortIndicator',
  props: {
    sortBy: {
      type: String,
      required: true,
    },
    sortSpec: {
      type: Object,
      default: null,
    },
    gameCount: {
      type: Number,
      default: 0,
    },
  },
  emits: ['sort-changed'],
  setup(props, { emit }) {
    const showSortMenu = ref(false)
    // Sort method labels
    const sortLabels = {
      date: 'Latest Videos',
      'rating-score': 'Highest Rated',
      'rating-category': 'Rating Tiers',
      name: 'Alphabetical',
      'release-new': 'Newest Releases',
      'release-old': 'Oldest Releases',
      'best-value': 'Best Value',
      'hidden-gems': 'Hidden Gems',
      'most-covered': 'Most Covered',
      trending: 'Trending Up',
      'creator-consensus': 'Creator Consensus',
      'recent-discoveries': 'Recent Discoveries',
      'video-recency': 'Within Time Range',
      'time-range-releases': 'Time Range Releases',
      'price-value': 'Price Range Value',
      'steam-optimized': 'Steam Highlights',
      'itch-discoveries': 'Itch Discoveries',
      'premium-quality': 'Premium Quality',
      'tag-match': 'Tag Relevance',
      'channel-picks': 'Channel Picks',
      advanced: 'Custom Multi-Criteria',
    }

    // Sort explanations
    const sortExplanations = {
      date: 'Games sorted by most recent video coverage, showing what content creators are playing now.',
      'rating-score':
        'Games with the highest Steam review percentages first, focusing on quality.',
      'rating-category':
        'Games grouped by Steam review categories (Overwhelmingly Positive, Very Positive, etc.), then by rating within each tier.',
      name: 'Games listed alphabetically by title, useful for finding specific games.',
      'release-new':
        'Most recently released games first, great for discovering new titles.',
      'release-old':
        'Oldest games first, perfect for finding classic or retro titles.',
      'best-value':
        'High-quality games at reasonable prices, prioritizing good value for money.',
      'hidden-gems':
        'Highly rated games with less video coverage - undiscovered treasures worth exploring.',
      'most-covered':
        'Games featured by many content creators, indicating strong community interest.',
      trending:
        'Games gaining recent attention with multiple new videos, showing current gaming trends.',
      'creator-consensus':
        'Games praised by multiple different channels, indicating broad appeal.',
      'recent-discoveries':
        'Recently featured games worth checking out, balanced by quality ratings.',
      'video-recency':
        'Games within your selected video time range, prioritizing newest coverage.',
      'time-range-releases':
        'Games released in your selected time range, sorted by rating quality.',
      'price-value': 'Best value games within your specified price range.',
      'steam-optimized':
        'Steam games sorted by review quality and community engagement metrics.',
      'itch-discoveries':
        'Creative indie games sorted by coverage and uniqueness.',
      'premium-quality':
        'Top-rated games with detailed reviews and recent attention.',
      'tag-match':
        'Games matching your selected tags, prioritized by rating and coverage.',
      'channel-picks':
        'Games featured by your selected channels, highest rated first.',
    }

    const sortLabel = computed(() => {
      return sortLabels[props.sortBy] || 'Custom Sort'
    })

    const explanation = computed(() => {
      let baseExplanation = sortExplanations[props.sortBy] || ''

      if (props.gameCount > 0) {
        baseExplanation += ` (${props.gameCount} games found)`
      }

      return baseExplanation
    })

    const isAdvanced = computed(() => {
      return props.sortBy === 'advanced' && props.sortSpec
    })

    const isContextual = computed(() => {
      return [
        'video-recency',
        'time-range-releases',
        'price-value',
        'steam-optimized',
        'itch-discoveries',
        'premium-quality',
        'tag-match',
        'channel-picks',
      ].includes(props.sortBy)
    })

    const isSmart = computed(() => {
      return [
        'best-value',
        'hidden-gems',
        'most-covered',
        'trending',
        'creator-consensus',
        'recent-discoveries',
      ].includes(props.sortBy)
    })

    const advancedDetails = computed(() => {
      if (!props.sortSpec) {
        return ''
      }

      const fieldNames = {
        rating: 'Rating',
        coverage: 'Coverage',
        recency: 'Recency',
        release: 'Release Date',
        price: 'Price',
        channels: 'Channels',
        reviews: 'Reviews',
      }

      let details = `Primary: ${fieldNames[props.sortSpec.primary?.field] || 'Unknown'}`
      if (props.sortSpec.secondary) {
        details += `, Secondary: ${fieldNames[props.sortSpec.secondary.field] || 'Unknown'}`
      }

      return details
    })

    const sortIcon = computed(() => {
      // Different icons based on sort type
      if (isAdvanced.value) {
        // Multi-level sort icon
        return 'M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12'
      } else if (isSmart.value) {
        // Brain/smart icon
        return 'M9.663 17h4.673M12 3a6 6 0 00-6 6c0 1.105.063 2.105.196 3M12 3a6 6 0 016 6c0 1.105-.063 2.105-.196 3m-11.608 0c-.135 1.028-.196 2.073-.196 3.073 0 2.485.199 4.925.582 7.262a4.657 4.657 0 01-.582 2.665m0 0a4.99 4.99 0 005.592 2.665m6.608 0c.135 1.028.196 2.073.196 3.073 0 2.485-.199 4.925-.582 7.262a4.657 4.657 0 00.582 2.665m0 0a4.99 4.99 0 01-5.592 2.665m0 0c.41-.258.826-.534 1.246-.826C9.663 17 12 17 12 17'
      } else if (isContextual.value) {
        // Filter/contextual icon
        return 'M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z'
      } else {
        // Standard sort icon
        return 'M3 4h13M3 8h9m-9 4h9m5-4v12m0 0l-4-4m4 4l4-4'
      }
    })

    // Basic sort options that are commonly used
    const basicSortOptions = [
      { value: 'date', label: 'Latest Videos' },
      { value: 'rating-score', label: 'Highest Rated' },
      { value: 'rating-category', label: 'Rating Tiers' },
      { value: 'name', label: 'Alphabetical' },
      { value: 'release-new', label: 'Newest Releases' },
      { value: 'release-old', label: 'Oldest Releases' },
    ]

    const handleSortChange = (newSortBy) => {
      showSortMenu.value = false
      emit('sort-changed', {
        sortBy: newSortBy,
        sortSpec: null, // Clear advanced sort spec when using basic sorts
      })
    }

    // Close menu when clicking outside
    const handleClickOutside = (event) => {
      if (!event.target.closest('.relative')) {
        showSortMenu.value = false
      }
    }

    onMounted(() => {
      document.addEventListener('click', handleClickOutside)
    })

    onUnmounted(() => {
      document.removeEventListener('click', handleClickOutside)
    })

    return {
      sortLabel,
      explanation,
      isAdvanced,
      isContextual,
      isSmart,
      advancedDetails,
      sortIcon,
      showSortMenu,
      basicSortOptions,
      handleSortChange,
    }
  },
}
</script>
