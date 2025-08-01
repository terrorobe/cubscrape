<script setup lang="ts">
import { computed } from 'vue'
import type { VersionMismatchInfo } from '../utils/databaseManager'

// Props interface
interface DatabaseStatusProps {
  connected: boolean
  games: number
  lastGenerated: Date | null
  lastChecked: Date | null
  showVersionMismatch: boolean
  versionMismatchInfo: VersionMismatchInfo | null
  isDevelopment: boolean
  currentTime: Date
  productionCheckInterval: number // in milliseconds
}

// Events interface
interface DatabaseStatusEmits {
  (e: 'testVersionMismatch'): void
  (e: 'reloadApp'): void
  (e: 'dismissVersionMismatch'): void
}

// Component props
const props = defineProps<DatabaseStatusProps>()

// Component emits
const emit = defineEmits<DatabaseStatusEmits>()

// Computed properties for timestamp formatting
const formatTimestamp = (
  timestamp: Date | string | null,
  useOld = false,
): string => {
  if (!timestamp) {
    return 'Unknown'
  }
  const date = new Date(timestamp)
  const now = props.currentTime
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000) // 60 * 1000
  const diffHours = Math.floor(diffMs / 3600000) // 60 * 60 * 1000

  const suffix = useOld ? ' old' : ' ago'

  if (diffMins < 1) {
    return 'just now'
  }
  if (diffMins < 60) {
    return `${diffMins}m${suffix}`
  }
  if (diffHours < 24) {
    return `${diffHours}h${suffix}`
  }
  return date.toLocaleDateString()
}

const formatExactTimestamp = (timestamp: Date | string | null): string => {
  if (!timestamp) {
    return 'Unknown'
  }
  const date = new Date(timestamp)
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// Computed properties for tooltips and display text
const databaseTooltip = computed(() => {
  if (!props.lastGenerated) {
    return ''
  }

  if (props.isDevelopment) {
    return 'Click to test version mismatch'
  }

  return `Database generation time: ${formatExactTimestamp(props.lastGenerated)}. Database should roughly update every 6 hours.`
})

const lastCheckTooltip = computed(() => {
  if (!props.lastChecked) {
    return ''
  }

  const checkIntervalMinutes = Math.round(props.productionCheckInterval / 60000)
  return `Last database update check: ${formatExactTimestamp(props.lastChecked)}. Checks happen every ${checkIntervalMinutes} minutes.`
})

const connectionStatusClass = computed(() =>
  props.connected ? 'bg-green-500' : 'bg-red-500',
)

// Event handlers
const handleDatabaseClick = () => {
  if (props.isDevelopment) {
    emit('testVersionMismatch')
  }
}

const handleReloadApp = () => {
  emit('reloadApp')
}

const handleDismissVersionMismatch = () => {
  emit('dismissVersionMismatch')
}
</script>

<template>
  <div class="database-status">
    <!-- Version Mismatch Notification -->
    <div
      v-if="showVersionMismatch"
      class="mb-6 rounded-lg border border-amber-500/50 bg-amber-50 p-4 dark:bg-amber-900/20"
    >
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <span class="text-2xl">🔄</span>
          <div>
            <h3 class="font-semibold text-amber-800 dark:text-amber-200">
              New Version Available
            </h3>
            <p class="text-sm text-amber-700 dark:text-amber-300">
              The app has been updated. Please reload to get the latest features
              and fixes.
            </p>
          </div>
        </div>
        <div class="flex gap-2">
          <button
            @click="handleDismissVersionMismatch"
            class="rounded-sm px-3 py-1 text-sm text-amber-700 hover:bg-amber-100 dark:text-amber-300 dark:hover:bg-amber-800/50"
          >
            Dismiss
          </button>
          <button
            @click="handleReloadApp"
            class="rounded-sm bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700"
          >
            Reload Now
          </button>
        </div>
      </div>
    </div>

    <!-- Desktop Database Status -->
    <div class="hidden items-center gap-4 text-sm md:flex">
      <div class="flex items-center gap-2">
        <span class="size-2 rounded-full" :class="connectionStatusClass"></span>
        <span>{{ games }} total</span>
      </div>
      <div class="text-xs text-text-secondary/70">
        <span
          v-if="lastGenerated"
          :title="databaseTooltip"
          :class="isDevelopment ? 'cursor-pointer hover:text-text-primary' : ''"
          @click="handleDatabaseClick"
        >
          Database:
          {{ formatTimestamp(lastGenerated, true) }}
        </span>
        <span v-if="lastChecked && !isDevelopment" :title="lastCheckTooltip">
          • Last check:
          {{ formatTimestamp(lastChecked) }}
        </span>
      </div>
    </div>

    <!-- Mobile Database Status -->
    <div class="flex items-center gap-2 text-sm md:hidden">
      <span class="size-2 rounded-full" :class="connectionStatusClass"></span>
      <span>{{ games }} total</span>
    </div>
  </div>
</template>

<style scoped>
.database-status {
  /* Component wrapper styles if needed */
}
</style>
