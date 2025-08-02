<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

/**
 * Channel item interface with name and count
 */
export interface ChannelWithCount {
  name: string
  count: number
}

/**
 * Channel filter change event payload
 */
export interface ChannelFilterChangeEvent {
  selectedChannels: string[]
}

/**
 * Props interface for ChannelFilterMulti component
 */
export interface ChannelFilterMultiProps {
  channelsWithCounts?: ChannelWithCount[]
  initialSelectedChannels?: string[]
}

const props = withDefaults(defineProps<ChannelFilterMultiProps>(), {
  channelsWithCounts: () => [],
  initialSelectedChannels: () => [],
})

const emit = defineEmits<{
  channelsChanged: [event: ChannelFilterChangeEvent]
}>()
const searchInput = ref<HTMLInputElement | null>(null)
const searchQuery = ref<string>('')
const showDropdown = ref<boolean>(false)
const selectedChannels = ref<string[]>([...props.initialSelectedChannels])

// Filtered channels based on search query
const filteredChannels = computed((): ChannelWithCount[] => {
  if (!searchQuery.value.trim()) {
    // Sort by popularity (game count) when not searching
    return props.channelsWithCounts.slice().sort((a, b) => b.count - a.count)
  }

  const query = searchQuery.value.toLowerCase()
  return props.channelsWithCounts
    .filter((channel) => {
      const formattedName = formatChannelName(channel.name).toLowerCase()
      return (
        formattedName.includes(query) ||
        channel.name.toLowerCase().includes(query)
      )
    })
    .sort((a, b) => b.count - a.count)
})

// Visible channels - always show all filtered channels
const visibleChannels = computed(
  (): ChannelWithCount[] => filteredChannels.value,
)

const toggleChannel = (channelName: string): void => {
  const index = selectedChannels.value.indexOf(channelName)
  if (index > -1) {
    selectedChannels.value.splice(index, 1)
  } else {
    selectedChannels.value.push(channelName)
  }
  emitFiltersChanged()
}

const removeChannel = (channelName: string): void => {
  const index = selectedChannels.value.indexOf(channelName)
  if (index > -1) {
    selectedChannels.value.splice(index, 1)
    emitFiltersChanged()
  }
}

const clearAllChannels = (): void => {
  selectedChannels.value = []
  emitFiltersChanged()
}

const clearSearch = (): void => {
  searchQuery.value = ''
  if (searchInput.value) {
    searchInput.value.focus()
  }
}

const formatChannelName = (channel: string): string => {
  if (!channel || typeof channel !== 'string') {
    return 'Unknown Channel'
  }
  return channel
    .replace(/^videos-/, '')
    .replace(/-/g, ' ')
    .replace(/\b\w/g, (l) => l.toUpperCase())
}

const emitFiltersChanged = (): void => {
  emit('channelsChanged', {
    selectedChannels: [...selectedChannels.value],
  })
}

// Handle clicking outside to close dropdown
const handleClickOutside = (event: Event): void => {
  const input = searchInput.value
  if (input && event.target && !input.contains(event.target as Node)) {
    showDropdown.value = false
  }
}

// Watch for changes in initial props
watch(
  () => props.initialSelectedChannels,
  (newChannels: string[]) => {
    selectedChannels.value = [...newChannels]
  },
  { deep: true },
)

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div class="space-y-3">
    <h3 class="text-sm font-semibold text-text-primary">Channels</h3>

    <!-- Selected Channels Display -->
    <div v-if="selectedChannels.length > 0" class="mb-3">
      <div class="mb-2 flex items-center justify-between">
        <span class="text-sm font-medium text-text-primary">
          Selected ({{ selectedChannels.length }})
        </span>
        <button
          @click="clearAllChannels"
          class="text-sm text-accent hover:underline"
        >
          Clear All
        </button>
      </div>
      <div class="flex flex-wrap gap-1">
        <span
          v-for="channel in selectedChannels"
          :key="channel"
          class="flex items-center gap-1 rounded-full bg-accent/20 px-2 py-1 text-xs text-accent"
        >
          {{ formatChannelName(channel) }}
          <button
            @click="removeChannel(channel)"
            class="flex size-3 items-center justify-center rounded-full text-accent/70 hover:bg-accent/30 hover:text-accent"
          >
            ×
          </button>
        </span>
      </div>
    </div>

    <!-- Search Input -->
    <div class="relative">
      <input
        ref="searchInput"
        type="text"
        v-model="searchQuery"
        placeholder="Search channels..."
        class="w-full rounded-sm border border-gray-600 bg-bg-primary px-3 py-2 pl-9 text-sm text-text-primary placeholder-text-secondary hover:border-accent focus:border-accent focus:outline-none"
        @focus="showDropdown = true"
      />
      <svg
        class="pointer-events-none absolute top-2.5 left-3 size-4 text-text-secondary"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
        />
      </svg>
      <button
        v-if="searchQuery"
        @click="clearSearch"
        class="absolute top-2.5 right-3 size-4 text-text-secondary hover:text-text-primary"
      >
        ×
      </button>
    </div>

    <!-- Channel List (Simplified for Sidebar) -->
    <div class="space-y-1">
      <label
        v-for="channel in visibleChannels"
        :key="channel.name"
        class="flex cursor-pointer items-center gap-2 rounded-sm border border-transparent p-2 text-sm transition-colors hover:border-accent/30 hover:bg-accent/5"
        :class="{
          'border-accent/50 bg-accent/10': selectedChannels.includes(
            channel.name,
          ),
        }"
        @click="toggleChannel(channel.name)"
      >
        <input
          type="checkbox"
          :checked="selectedChannels.includes(channel.name)"
          @click.stop
          @change="toggleChannel(channel.name)"
          class="size-4 rounded-sm border-gray-600 text-accent focus:ring-accent focus:ring-offset-0"
        />
        <div class="min-w-0 flex-1">
          <div class="truncate text-text-primary">
            {{ formatChannelName(channel.name) }}
          </div>
          <div class="text-xs text-text-secondary">
            {{ channel.count }} games
          </div>
        </div>
      </label>
    </div>

    <!-- Empty State -->
    <div
      v-if="filteredChannels.length === 0 && searchQuery"
      class="py-4 text-center text-sm text-text-secondary"
    >
      No channels found for "{{ searchQuery }}"
    </div>

    <!-- Overall Empty State -->
    <div
      v-if="channelsWithCounts.length === 0"
      class="py-6 text-center text-sm text-text-secondary"
    >
      No channels available
    </div>
  </div>
</template>
