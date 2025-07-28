<script>
import { ref, watch } from 'vue'

export default {
  name: 'MobileTimeFilterSimple',
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
  emits: ['timeFilterChanged'],
  setup(props, { emit }) {
    const selectedType = ref(props.initialTimeFilter.type || '')
    const selectedPreset = ref(props.initialTimeFilter.preset || '')

    const handleChange = () => {
      const timeFilter = {
        type: selectedType.value || null,
        preset: selectedPreset.value || null,
        startDate: null,
        endDate: null,
        smartLogic: null,
      }

      // Generate date range for preset
      if (selectedType.value && selectedPreset.value) {
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

      emit('timeFilterChanged', timeFilter)
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
      },
      { deep: true },
    )

    return {
      selectedType,
      selectedPreset,
      handleChange,
    }
  },
}
</script>

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
      </select>
    </div>
  </div>
</template>
