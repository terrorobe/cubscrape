<template>
  <div class="space-y-4">
    <div class="mb-2 text-sm font-medium text-text-secondary">Time Filter</div>

    <!-- Filter Type Selection -->
    <div class="space-y-3">
      <label class="flex items-center">
        <input
          v-model="selectedType"
          value=""
          type="radio"
          class="mr-3 size-4 text-accent"
          @change="handleChange"
        />
        <span class="text-text-primary">No Time Filter</span>
      </label>

      <label class="flex items-center">
        <input
          v-model="selectedType"
          value="video"
          type="radio"
          class="mr-3 size-4 text-accent"
          @change="handleChange"
        />
        <span class="text-text-primary">Filter by Video Date</span>
      </label>

      <label class="flex items-center">
        <input
          v-model="selectedType"
          value="release"
          type="radio"
          class="mr-3 size-4 text-accent"
          @change="handleChange"
        />
        <span class="text-text-primary">Filter by Release Date</span>
      </label>
    </div>

    <!-- Preset Selection -->
    <div v-if="selectedType" class="space-y-2">
      <label class="text-sm text-text-secondary">Time Range:</label>
      <select
        v-model="selectedPreset"
        class="min-h-12 w-full rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary"
        @change="handleChange"
      >
        <option value="">Select a time range...</option>
        <option value="last-week">Last Week</option>
        <option value="last-month">Last Month</option>
        <option value="last-3-months">Last 3 Months</option>
        <option value="last-6-months">Last 6 Months</option>
        <option value="last-year">Last Year</option>
        <option value="custom">Custom Range</option>
      </select>
    </div>

    <!-- Custom Date Range for Mobile -->
    <div v-if="selectedType && selectedPreset === 'custom'" class="space-y-3">
      <label class="text-sm text-text-secondary">Custom Date Range:</label>
      <div class="space-y-2">
        <div>
          <label class="mb-1 block text-xs text-text-secondary">From:</label>
          <input
            v-model="customStartDate"
            type="date"
            class="min-h-12 w-full rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary"
            @change="handleChange"
          />
        </div>
        <div>
          <label class="mb-1 block text-xs text-text-secondary">To:</label>
          <input
            v-model="customEndDate"
            type="date"
            class="min-h-12 w-full rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary"
            @change="handleChange"
          />
        </div>
      </div>
    </div>

    <!-- Smart Filters for Mobile -->
    <div v-if="selectedType === 'smart'" class="space-y-2">
      <label class="text-sm text-text-secondary">Smart Discovery:</label>
      <select
        v-model="selectedSmartFilter"
        class="min-h-12 w-full rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary"
        @change="handleChange"
      >
        <option value="">Select discovery type...</option>
        <option value="recently-released">Recently Released</option>
        <option value="new-discoveries">New Discoveries</option>
        <option value="trending">Trending Now</option>
        <option value="hidden-gems-time">Hidden Gems</option>
      </select>
    </div>

    <!-- Current Selection Display -->
    <div v-if="selectedType" class="rounded-sm border border-gray-600 bg-bg-card p-3">
      <div class="text-xs text-text-secondary">Current Filter:</div>
      <div class="text-sm text-text-primary">
        {{ getFilterDescription() }}
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch } from 'vue'

export default {
  name: 'MobileTimeFilter',
  props: {
    initialTimeFilter: {
      type: Object,
      default: () => ({
        type: null,
        preset: null,
        startDate: null,
        endDate: null,
        smartLogic: null,
      }),
    },
  },
  emits: ['time-filter-changed'],
  setup(props, { emit }) {
    const selectedType = ref(props.initialTimeFilter.type || '')
    const selectedPreset = ref(props.initialTimeFilter.preset || '')
    const selectedSmartFilter = ref(props.initialTimeFilter.smartLogic || '')
    const customStartDate = ref(props.initialTimeFilter.startDate || '')
    const customEndDate = ref(props.initialTimeFilter.endDate || '')

    const getFilterDescription = () => {
      if (!selectedType.value) return 'No filter applied'
      
      const typeLabel = selectedType.value === 'video' ? 'Video Date' : 'Release Date'
      
      if (selectedPreset.value === 'custom') {
        const start = customStartDate.value || 'Not set'
        const end = customEndDate.value || 'Not set'
        return `${typeLabel}: ${start} to ${end}`
      }
      
      if (selectedPreset.value) {
        const presetLabels = {
          'last-week': 'Last Week',
          'last-month': 'Last Month',
          'last-3-months': 'Last 3 Months',
          'last-6-months': 'Last 6 Months',
          'last-year': 'Last Year',
        }
        return `${typeLabel}: ${presetLabels[selectedPreset.value] || selectedPreset.value}`
      }
      
      if (selectedSmartFilter.value) {
        const smartLabels = {
          'recently-released': 'Recently Released Games',
          'new-discoveries': 'New Game Discoveries',
          'trending': 'Trending Games',
          'hidden-gems-time': 'Time-based Hidden Gems',
        }
        return smartLabels[selectedSmartFilter.value] || selectedSmartFilter.value
      }
      
      return `${typeLabel} filter selected`
    }

    const handleChange = () => {
      const timeFilter = {
        type: selectedType.value || null,
        preset: selectedPreset.value || null,
        startDate: null,
        endDate: null,
        smartLogic: selectedSmartFilter.value || null,
      }

      // Generate date range for preset
      if (selectedType.value && selectedPreset.value && selectedPreset.value !== 'custom') {
        const ranges = {
          'last-week': 7,
          'last-month': 30,
          'last-3-months': 90,
          'last-6-months': 180,
          'last-year': 365,
        }

        const days = ranges[selectedPreset.value]
        if (days) {
          const endDate = new Date()
          const startDate = new Date(
            endDate.getTime() - days * 24 * 60 * 60 * 1000,
          )
          timeFilter.startDate = startDate.toISOString().split('T')[0]
          timeFilter.endDate = endDate.toISOString().split('T')[0]
        }
      }

      // Handle custom date range
      if (selectedPreset.value === 'custom') {
        timeFilter.startDate = customStartDate.value || null
        timeFilter.endDate = customEndDate.value || null
      }

      emit('time-filter-changed', timeFilter)
    }

    // Watch for prop changes
    watch(
      () => props.initialTimeFilter,
      (newFilter) => {
        if (newFilter.type !== selectedType.value) {
          selectedType.value = newFilter.type || ''
        }
        if (newFilter.preset !== selectedPreset.value) {
          selectedPreset.value = newFilter.preset || ''
        }
        if (newFilter.smartLogic !== selectedSmartFilter.value) {
          selectedSmartFilter.value = newFilter.smartLogic || ''
        }
        if (newFilter.startDate !== customStartDate.value) {
          customStartDate.value = newFilter.startDate || ''
        }
        if (newFilter.endDate !== customEndDate.value) {
          customEndDate.value = newFilter.endDate || ''
        }
      },
      { deep: true },
    )

    return {
      selectedType,
      selectedPreset,
      selectedSmartFilter,
      customStartDate,
      customEndDate,
      handleChange,
      getFilterDescription,
    }
  },
}
</script>