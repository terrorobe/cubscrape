<script setup lang="ts">
import { ref, computed, watch } from 'vue'

/**
 * Channel item interface with name and count
 */
export interface ChannelWithCount {
  name: string
  count: number
  videoCount?: number
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
const selectedChannels = ref<string[]>([...props.initialSelectedChannels])

// Channels sorted alphabetically
const sortedChannels = computed((): ChannelWithCount[] =>
  props.channelsWithCounts.slice().sort((a, b) => {
    const nameA = formatChannelName(a.name)
    const nameB = formatChannelName(b.name)
    return nameA.localeCompare(nameB)
  }),
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

// Watch for changes in initial props
watch(
  () => props.initialSelectedChannels,
  (newChannels: string[]) => {
    selectedChannels.value = [...newChannels]
  },
  { deep: true },
)
</script>

<template>
  <div class="space-y-3">
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

    <!-- Channel List (Simplified for Sidebar) -->
    <div v-if="channelsWithCounts.length > 0" class="space-y-1">
      <label
        v-for="channel in sortedChannels"
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
            <span
              >{{ channel.count }}
              {{ channel.count === 1 ? 'game' : 'games' }}</span
            >
            <span
              v-if="channel.videoCount"
              class="mx-1.5 text-text-secondary/50"
              >•</span
            >
            <span v-if="channel.videoCount"
              >{{ channel.videoCount }}
              {{ channel.videoCount === 1 ? 'video' : 'videos' }}</span
            >
          </div>
        </div>
      </label>
    </div>

    <!-- Loading State -->
    <div
      v-else
      class="flex items-center justify-center py-6 text-sm text-text-secondary"
    >
      <div class="flex items-center gap-2">
        <div
          class="size-4 animate-spin rounded-full border-2 border-accent border-t-transparent"
        ></div>
        <span>Loading channels...</span>
      </div>
    </div>
  </div>
</template>
