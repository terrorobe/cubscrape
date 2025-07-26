<template>
  <div class="space-y-4">
    <label class="text-sm text-text-secondary">Time Filter:</label>

    <!-- Filter Type Selection -->
    <div class="space-y-2">
      <label class="flex items-center">
        <input
          v-model="selectedType"
          value=""
          type="radio"
          class="mr-2 text-accent"
          @change="handleChange"
        />
        <span class="text-sm text-text-primary">No Time Filter</span>
      </label>

      <label class="flex items-center">
        <input
          v-model="selectedType"
          value="video"
          type="radio"
          class="mr-2 text-accent"
          @change="handleChange"
        />
        <span class="text-sm text-text-primary">Filter by Video Date</span>
      </label>

      <label class="flex items-center">
        <input
          v-model="selectedType"
          value="release"
          type="radio"
          class="mr-2 text-accent"
          @change="handleChange"
        />
        <span class="text-sm text-text-primary">Filter by Release Date</span>
      </label>
    </div>

    <!-- Preset Selection -->
    <div v-if="selectedType" class="space-y-2">
      <label class="text-sm text-text-secondary">Time Range:</label>
      <select
        v-model="selectedPreset"
        class="w-full rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary"
        @change="handleChange"
      >
        <option value="">Select a time range...</option>
        <option value="last-week">Last Week</option>
        <option value="last-month">Last Month</option>
        <option value="last-3-months">Last 3 Months</option>
        <option value="last-6-months">Last 6 Months</option>
        <option value="last-year">Last Year</option>
      </select>
    </div>

    <!-- Custom Date Range -->
    <div v-if="selectedType && selectedPreset === 'custom'" class="space-y-2">
      <label class="text-sm text-text-secondary">Custom Date Range:</label>
      <div class="grid grid-cols-2 gap-2">
        <input
          v-model="customStartDate"
          type="date"
          class="rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary"
          @change="handleChange"
        />
        <input
          v-model="customEndDate"
          type="date"
          class="rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary"
          @change="handleChange"
        />
      </div>
    </div>

    <!-- Smart Filters -->
    <div v-if="selectedType === 'smart'" class="space-y-2">
      <label class="text-sm text-text-secondary">Smart Filters:</label>
      <select
        v-model="selectedSmartFilter"
        class="w-full rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary"
        @change="handleChange"
      >
        <option value="">Select smart filter...</option>
        <option value="recently-released">Recently Released Games</option>
        <option value="new-discoveries">New Discoveries</option>
        <option value="trending">Trending Games</option>
        <option value="hidden-gems-time">Hidden Gems (Time-based)</option>
      </select>
    </div>
  </div>
</template>

<script>
import { ref, watch } from 'vue'

export default {
  name: 'TimeFilter',
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

    const handleChange = () => {
      const timeFilter = {
        type: selectedType.value || null,
        preset: selectedPreset.value || null,
        startDate: null,
        endDate: null,
        smartLogic: selectedSmartFilter.value || null,
      }

      // Generate date range for preset
      if (
        selectedType.value &&
        selectedPreset.value &&
        selectedPreset.value !== 'custom'
      ) {
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
    }
  },
}
</script>
