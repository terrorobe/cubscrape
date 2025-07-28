<template>
  <div class="space-y-3">
    <h3 class="text-sm font-semibold text-text-primary">Time Filter</h3>

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
    <div
      class="space-y-2"
      :class="{ 'pointer-events-none opacity-0': !selectedType }"
    >
      <label class="text-sm text-text-secondary">Time Range:</label>
      <select
        v-model="selectedPreset"
        class="w-full rounded-sm border border-gray-600 bg-bg-card px-3 py-2 text-text-primary"
        @change="handleChange"
        :disabled="!selectedType"
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

<script setup lang="ts">
import { ref, watch } from 'vue'

/**
 * Time filter type options
 */
export type TimeFilterType = 'video' | 'release' | null

/**
 * Time filter preset options
 */
export type TimeFilterPreset =
  | 'last-week'
  | 'last-month'
  | 'last-3-months'
  | 'last-6-months'
  | 'last-year'
  | null

/**
 * Time filter configuration
 */
export interface TimeFilterConfig {
  type: TimeFilterType
  preset: TimeFilterPreset
  startDate: string | null
  endDate: string | null
  smartLogic: string | null
}

/**
 * Props interface for TimeFilterSimple component
 */
export interface TimeFilterSimpleProps {
  initialTimeFilter?: TimeFilterConfig
}

const props = withDefaults(defineProps<TimeFilterSimpleProps>(), {
  initialTimeFilter: () => ({
    type: null,
    preset: null,
    startDate: null,
    endDate: null,
    smartLogic: null,
  }),
})

const emit = defineEmits<{
  'time-filter-changed': [filter: TimeFilterConfig]
}>()
const selectedType = ref<string>(props.initialTimeFilter.type || '')
const selectedPreset = ref<string>(props.initialTimeFilter.preset || '')

const handleChange = (): void => {
  const timeFilter: TimeFilterConfig = {
    type: (selectedType.value || null) as TimeFilterType,
    preset: (selectedPreset.value || null) as TimeFilterPreset,
    startDate: null,
    endDate: null,
    smartLogic: null,
  }

  // Generate date range for preset
  if (selectedType.value && selectedPreset.value) {
    const ranges: Record<string, number> = {
      'last-week': 7,
      'last-month': 30,
      'last-3-months': 90,
      'last-6-months': 180,
      'last-year': 365,
    }

    const days = ranges[selectedPreset.value]
    if (days) {
      const endDate = new Date()
      const startDate = new Date(endDate.getTime() - days * 24 * 60 * 60 * 1000)
      timeFilter.startDate = startDate.toISOString().split('T')[0]
      timeFilter.endDate = endDate.toISOString().split('T')[0]
    }
  }

  emit('time-filter-changed', timeFilter)
}

// Watch for prop changes
watch(
  () => props.initialTimeFilter,
  (newFilter: TimeFilterConfig) => {
    if (newFilter.type !== selectedType.value) {
      selectedType.value = newFilter.type || ''
    }
    if (newFilter.preset !== selectedPreset.value) {
      selectedPreset.value = newFilter.preset || ''
    }
  },
  { deep: true },
)
</script>
