<template>
  <div class="space-y-4">
    <!-- Search -->
    <div>
      <label class="mb-2 block text-sm font-medium text-text-secondary"
        >Search Channels</label
      >
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Type to search channels..."
        class="w-full rounded-lg border border-gray-600 bg-bg-card p-3 text-text-primary placeholder-text-secondary focus:border-accent focus:ring-2 focus:ring-accent/50 focus:outline-none"
      />
    </div>

    <!-- Selected Channels -->
    <div v-if="selectedChannels.length > 0">
      <label class="mb-2 block text-sm font-medium text-text-secondary">
        Selected Channels ({{ selectedChannels.length }})
      </label>
      <div class="space-y-2">
        <div
          v-for="channel in selectedChannels"
          :key="`selected-${channel}`"
          class="flex items-center justify-between rounded-lg bg-accent p-3"
        >
          <span class="font-medium text-white">{{
            formatChannelName(channel)
          }}</span>
          <button
            @click="toggleChannel(channel)"
            class="rounded-full p-1 text-white transition-colors hover:bg-white/20 active:bg-white/30"
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
                d="M6 18L18 6M6 6l12 12"
              ></path>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Available Channels -->
    <div>
      <label class="mb-2 block text-sm font-medium text-text-secondary">
        Available Channels ({{ filteredAvailableChannels.length }})
      </label>

      <!-- Clear button for search -->
      <div v-if="searchQuery" class="mb-2">
        <button
          @click="searchQuery = ''"
          class="text-sm text-accent hover:text-accent-hover"
        >
          Clear search
        </button>
      </div>

      <!-- No results message -->
      <div
        v-if="filteredAvailableChannels.length === 0"
        class="py-4 text-center text-text-secondary"
      >
        <p v-if="searchQuery">No channels found matching "{{ searchQuery }}"</p>
        <p v-else>All channels are selected</p>
      </div>

      <!-- Channel list -->
      <div v-else class="max-h-64 space-y-1 overflow-y-auto">
        <button
          v-for="channel in filteredAvailableChannels"
          :key="`available-${channel.name}`"
          @click="toggleChannel(channel.name)"
          class="flex w-full items-center justify-between rounded-lg bg-bg-card p-3 text-left text-text-primary transition-colors hover:bg-bg-primary active:bg-bg-primary"
        >
          <span class="font-medium">{{ formatChannelName(channel.name) }}</span>
          <span class="text-sm text-text-secondary"
            >{{ channel.count }} game{{ channel.count !== 1 ? 's' : '' }}</span
          >
        </button>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="space-y-2 border-t border-gray-600 pt-4">
      <!-- Select Popular Channels -->
      <button
        v-if="selectedChannels.length === 0 && popularChannels.length > 0"
        @click="selectPopularChannels"
        class="w-full rounded-lg border border-accent px-4 py-3 text-accent transition-colors hover:bg-accent hover:text-white"
      >
        Select Top {{ Math.min(5, popularChannels.length) }} Channels
      </button>

      <!-- Clear All -->
      <button
        v-if="selectedChannels.length > 0"
        @click="clearAllChannels"
        class="w-full rounded-lg border border-gray-600 px-4 py-3 text-text-secondary transition-colors hover:border-accent hover:text-accent"
      >
        Clear All Channels
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, type Ref } from 'vue'
import { UI_LIMITS } from '../config/index'
import type { ChannelWithCount } from '../types/database'

// Component props interface
interface Props {
  channelsWithCounts?: ChannelWithCount[]
  initialSelectedChannels?: string[]
}

// Component events interface
interface Emits {
  'channels-changed': [data: { selectedChannels: string[] }]
}

// Define props with defaults
const props = withDefaults(defineProps<Props>(), {
  channelsWithCounts: () => [],
  initialSelectedChannels: () => [],
})

// Define emits
const emit = defineEmits<Emits>()

// Reactive state with proper typing
const selectedChannels: Ref<string[]> = ref([...props.initialSelectedChannels])
const searchQuery: Ref<string> = ref('')

// Computed properties with proper typing
const popularChannels = computed((): ChannelWithCount[] => {
  return props.channelsWithCounts
    .filter((channel) => !selectedChannels.value.includes(channel.name))
    .slice(0, UI_LIMITS.MOBILE_CHANNELS_COUNT)
})

const filteredAvailableChannels = computed((): ChannelWithCount[] => {
  const available = props.channelsWithCounts.filter(
    (channel) => !selectedChannels.value.includes(channel.name),
  )

  if (!searchQuery.value) {
    return available
  }

  const query = searchQuery.value.toLowerCase()
  return available.filter((channel) => {
    const formattedName = formatChannelName(channel.name).toLowerCase()
    return (
      formattedName.includes(query) ||
      channel.name.toLowerCase().includes(query)
    )
  })
})

// Helper functions with proper typing
const formatChannelName = (channel: string | undefined): string => {
  if (!channel || typeof channel !== 'string') {
    return 'Unknown Channel'
  }
  return channel
    .replace(/^videos-/, '')
    .replace(/-/g, ' ')
    .replace(/\b\w/g, (l) => l.toUpperCase())
}

const toggleChannel = (channelName: string): void => {
  const index = selectedChannels.value.indexOf(channelName)
  if (index > -1) {
    selectedChannels.value.splice(index, 1)
  } else {
    selectedChannels.value.push(channelName)
  }
  emitChange()
}

const selectPopularChannels = (): void => {
  const channelsToAdd = popularChannels.value
    .slice(0, UI_LIMITS.MOBILE_CHANNELS_COUNT)
    .map((c) => c.name)
  selectedChannels.value = [...selectedChannels.value, ...channelsToAdd]
  emitChange()
}

const clearAllChannels = (): void => {
  selectedChannels.value = []
  emitChange()
}

const emitChange = (): void => {
  emit('channels-changed', {
    selectedChannels: [...selectedChannels.value],
  })
}

// Watch for prop changes
watch(
  () => props.initialSelectedChannels,
  (newChannels: string[]) => {
    selectedChannels.value = [...newChannels]
  },
  { deep: true },
)
</script>

<style scoped>
/* Custom scrollbar for channel list */
.overflow-y-auto::-webkit-scrollbar {
  width: 4px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: theme('colors.bg.primary');
  border-radius: 2px;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: theme('colors.text.secondary');
  border-radius: 2px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: theme('colors.text.primary');
}

/* Active states for better touch feedback */
.active\:bg-bg-primary:active {
  background-color: theme('colors.bg.primary');
}

.active\:bg-white:active {
  background-color: white;
}
</style>
